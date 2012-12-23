# -*- coding: utf-8 -*-
"""
This module implements the access to KeePass 1.x-databases.
"""
import binascii

__authors__ = ["Karsten-Kai König <kkoenig@posteo.de>", "Hans Lellelid <hans@xmpl.org>", "Brett Viren <brett.viren@gmail.com>"]
__copyright__ = "Copyright (C) 2012 Karsten-Kai König <kkoenig@posteo.de>"
__license__ = """
keepassdb is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or at your option) any later version.

keepassdb is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
keepassdb.  If not, see <http://www.gnu.org/licenses/>.
"""
import logging
import os
import os.path
import hashlib

from Crypto.Random import get_random_bytes

from keepassdb import exc, util, const
from keepassdb.model import Group, Entry, RootGroup
from keepassdb.structures import HeaderStruct, GroupStruct, EntryStruct

class Database(object):
    """
    Database represents the KeePass 1.x database.
    
    Attributes:
    - groups holds all groups of the database. (list of StdGroups)
    - readonly declares if the file should be read-only or not (bool)
    - filepath holds the path of the database (string)
    - password is the passphrase to encrypt and decrypt the database (string)
    - keyfile is the path to a keyfile (string)
    
    Usage:
    
    You can load a KeePass database by the filename and the passphrase or
    create an empty database. It's also possible to open the database read-only
    and to create a new one.
    
    Example:
    
    from keepassdb import Database
    
    try:
        db = Database.load(filepath, passphrase)
    except Exception as e:
        print(e)
    
    try:
        db = Database.create()
    except Exception as e:
        print(e)
    """
    readonly = False
    header = None
    password = None
    keyfile = None
    _filepath = None
    
    def __init__(self, filepath=None, password=None, keyfile=None, readonly=False, new=False):
        """
        Initialize a new or an existing database.
        
        The default constructor should only be called internally; you should use the
        Database::load() or Database::create() methods to load or create a new
        database, respectively. 
        """
        self.log = logging.getLogger('{0.__module__}.{0.__name__}'.format(self.__class__))
        self.groups = []
        self.password = None
        self.keyfile = None
        
        self._entries = []
        self._root_group = RootGroup()
        
        if new:
            self.filepath = filepath
            self.password = password
            self.keyfile = keyfile
            self.initialize_empty()
        elif filepath:
            self.load(filepath, password=password, keyfile=keyfile, readonly=readonly)
    
    @property
    def filepath(self):
        """ Property for retrieving current filepath (or None if db not loaded from file) """
        return self._filepath
    
    @filepath.setter
    def filepath(self, value):
        """ Proerty for setting current filepath. """
        self._filepath = value
        
    def initialize_empty(self):
        """
        Initialize the database with a defaut 'Internet' group.
        """
        assert len(self.groups) == 0, "initialize_empty() should only be used with a new database."
        self.create_group('Internet', icon=1)
                
    def load(self, filepath, password=None, keyfile=None, readonly=False):
        self.filepath = filepath
        buf = None
        if hasattr(filepath, 'read'):
            buf = filepath.read()
        else:
            # Assume it is a filepath and attempt to open it.
            if not os.path.exists(filepath):
                raise ValueError("File does not exist: {}".format(filepath))
        
            with open(filepath, 'rb') as fp:
                buf = fp.read()
                
        self.load_from_buffer(buf, password=password, keyfile=keyfile, readonly=readonly)
    
    def load_from_buffer(self, buf, password=None, keyfile=None, readonly=False):
        """
        This method opens an existing database.

        :param buf: A string (bytes) of the database contents.
        :param password:
        :param keyfile:
        :param readonly: Whether to open the database read-only.
        """
        if password is None and keyfile is None:
            raise ValueError("Password and/or keyfile is required.")
        
        # Save these to use as defaults when saving the database
        self.password = password
        self.keyfile = keyfile
        
        # The header is 124 bytes long, the rest is content
        hdr_len = HeaderStruct.length
        header_bytes = buf[:hdr_len]
        crypted_content = buf[hdr_len:]
        
        self.header = HeaderStruct(header_bytes)
        
        self.log.debug("Extracted header: {0}".format(self.header))
        # Check if the database is supported
        if self.header.version & const.DB_SUPPORTED_VERSION_MASK != const.DB_SUPPORTED_VERSION & const.DB_SUPPORTED_VERSION_MASK:
            raise exc.UnsupportedDatabaseVersion('Unsupported file version: {0}'.format(hex(self.header.version)))
            
        #Actually, only AES is supported.
        if not self.header.flags & HeaderStruct.AES:
            raise exc.UnsupportedDatabaseEncryption('Only AES encryption is supported.')
        
        final_key = util.derive_key(seed_key=self.header.seed_key,
                                    seed_rand=self.header.seed_rand,
                                    rounds=self.header.key_enc_rounds,
                                    password=password, keyfile=keyfile)
        
        decrypted_content = util.decrypt_aes_cbc(crypted_content, key=final_key, iv=self.header.encryption_iv)
        
        # Check if decryption failed
        if ((len(decrypted_content) > const.DB_MAX_CONTENT_LEN) or
            (len(decrypted_content) == 0 and self.header.ngroups > 0)):
            raise exc.IncorrectKey("Decryption failed! The key is wrong or the file is damaged.")

        if not self.header.contents_hash == hashlib.sha256(decrypted_content).digest():
            raise exc.AuthenticationError("Hash test failed. The key is wrong or the file is damaged.")
            
        # First thing (after header) are the group definitions.
        for _i in range(self.header.ngroups):
            gstruct = GroupStruct(decrypted_content)
            self.groups.append(Group.from_struct(gstruct))
            length = len(gstruct)
            decrypted_content = decrypted_content[length:]
        
        # Next come the entry definitions.
        for _i in range(self.header.nentries):
            estruct = EntryStruct(decrypted_content)
            self._entries.append(Entry.from_struct(estruct))
            length = len(estruct)
            decrypted_content = decrypted_content[length:]
            
        # Sets up the hierarchy, relates the group/entry model objects.
        self._bind_model()
        
    def save(self, filepath=None, password=None, keyfile=None):
        """
        Save the database.
        
        Password or keyfile (or both) required.  If database was loaded 
         
        :param filepath: The path to the file we wish to save.
        :param password: The password to use for the database.
        :param keyfile: The keyfile to use for the database.
        
        :raise keepassdb.exc.ReadOnlyDatabase: If database was opened with readonly flag.
        """
        if self.readonly:
            raise exc.ReadOnlyDatabase()
        
        if filepath is not None:
            self.filepath = filepath
        if password is not None or self.keyfile is not None:
            # Do these together so we don't end up with some hybrid of old & new key material
            self.password = password
            self.keyfile = keyfile  
        else: 
            raise ValueError("Password and/or keyfile is required.")
        
        if self.filepath is None:
            raise ValueError("Unable to save file without filepath.")
        
        buf = bytearray()
        
        # First, serialize the groups
        for group in self.groups:
            # Get the packed bytes
            group_struct = group.to_struct()
            self.log.debug("Group struct: {0!r}".format(group_struct))
            buf += group_struct.encode()
            
        # Then the entries.
        for entry in self._entries:
            entry_struct = entry.to_struct()
            buf += entry_struct.encode()

        # Hmmmm ... these defaults should probably be set elsewhere....?
        header = HeaderStruct()
        header.signature1 = const.DB_SIGNATURE1
        header.signature2 = const.DB_SIGNATURE2
        header.flags = header.AES
        header.version = 0x00030002
        header.key_enc_rounds = 50000
        header.seed_key = get_random_bytes(32)
        
        # Generate new seed & vector; update content hash        
        header.encryption_iv = get_random_bytes(16)
        header.seed_rand = get_random_bytes(16)
        header.contents_hash = hashlib.sha256(buf).digest()
        
        # Update num groups/entries to match curr state
        header.nentries = len(self._entries)
        header.ngroups = len(self.groups)
        
        final_key = util.derive_key(seed_key=header.seed_key,
                                    seed_rand=header.seed_rand,
                                    rounds=header.key_enc_rounds,
                                    password=password, keyfile=keyfile)
        
        
        print "Serialized payload: {0!r}".format(buf)
        
        encrypted_content = util.encrypt_aes_cbc(buf, key=final_key, iv=header.encryption_iv)
        
        with open(self.filepath, "wb") as fp:
            fp.write(header.encode() + encrypted_content)
                    
    def create_group(self, title, parent=None, icon=1, expires=None):
        """
        This method creates a new group.

        A group title is needed or no group will be created.

        If a parent is given, the group will be created as a sub-group.

        title must be a string, image an unsigned int >0 and parent a Group.
        
        :return: The newly created group.
        :rtype: :class:`keepassdb.model.Group`
        """
        if parent and not isinstance(parent, Group):
            raise TypeError("Parent must be of type Group")
        
        if expires is None:
            expires = const.NEVER
        
        if self.groups:
            group_id = max([g.id for g in self.groups]) + 1
        else:
            group_id = 1
        
        group = Group(id=group_id, title=title, icon=icon, db=self, 
                      created=util.now(), modified=util.now(), accessed=util.now(),
                      expires=expires)
        
        # If no parent is given, just append the new group at the end
        if parent is None:
            group.parent = self._root_group
            self._root_group.children.append(group)
            group.level = 0
            self.groups.append(group)
            
        # Else insert the group behind the parent
        else:
            if parent in self.groups:
                parent.children.append(group)
                group.parent = parent
                group.level = parent.level + 1
                self.groups.insert(self.groups.index(parent) + 1, group)
            else:
                raise exc.KPError("Given parent doesn't exist")
                
        return group

    def remove_group(self, group):
        """
        This method removes a group.
        """
        if not isinstance(group, Group):
            raise TypeError("group must be Group")
        if not group in self.groups:
            raise ValueError("Group does not exist (or is not bound to this db instance).")
        
        # Recurse down to remove sub-groups
        for child in group.children: # We may need to copy this to avoid CME (see below)
            self.remove_group(child)
        
        for entry in group.entries:
            self.remove_entry(entry)
        
        # Finally remove group from the parent's list.
        group.parent.children.remove(group) # Concurrent modification exception? Parent in recursive stack is iterating ...
        self.groups.remove(group)
        
            
    def move_group(self, group=None, parent=None):
        """Append group to a new parent.

        group and parent must be Group-instances.

        """

        if group is None or type(group) is not Group:
            raise exc.KPError("A valid group must be given.")
            
        elif parent is not None and type(parent) is not Group:
            raise exc.KPError("parent must be a Group.")
            
        elif group is parent:
            raise exc.KPError("group and parent must not be the same group")
            
        if parent is None: parent = self._root_group;
        if group in self.groups:
            self.groups.remove(group)
            group.parent.children.remove(group)
            group.parent = parent
            if parent.children:
                if parent.children[-1] is self.groups[-1]:
                    self.groups.append(group)
                else:
                    new_index = self.groups.index(parent.children[-1]) + 1
                    self.groups.insert(new_index, group)
            else:
                new_index = self.groups.index(parent) + 1
                self.groups.insert(new_index, group)
            parent.children.append(group)
            if parent is self._root_group:
                group.level = 0
            else:
                group.level = parent.level + 1
            if group.children:
                self._move_group_helper();
            group.last_mod = util.now()
            return True
        else:
            raise exc.KPError("Didn't find given group.")
            

    def move_group_in_parent(self, group=None, index=None):
        """Move group to another position in group's parent.
        
        index must be a valid index of group.parent.groups

        """
        
        if group is None or index is None:
            raise exc.KPError("group and index must be set")
            
        elif type(group) is not Group or type(index) is not int:
            raise exc.KPError("group must be a Group-instance and index "
                          "must be an integer.")
            
        elif group not in self.groups:
            raise exc.KPError("Given group doesn't exist")
            
        elif index < 0 or index >= len(group.parent.children):
            raise exc.KPError("index must be a valid index if group.parent.groups")
            
        else:
            group_at_index = group.parent.children[index]
            pos_in_parent = group.parent.children.index(group) 
            pos_in_groups = self.groups.index(group)
            pos_in_groups2 = self.groups.index(group_at_index)

            group.parent.children[index] = group
            group.parent.children[pos_in_parent] = group_at_index
            self.groups[pos_in_groups2] = group
            self.groups[pos_in_groups] = group_at_index
            if group.children: self._move_group_helper(group);
            if group_at_index.children: self._move_group_helper(group_at_index);
            group.last_mod = util.now()
            return True

    def _move_group_helper(self, group):
        """
        A helper to recursively move the chidren of a group.
        """
        for i in group.children:
            self.groups.remove(i)
            i.level = group.level + 1
            self.group.insert(self.groups.index(group) + 1, i)
            if i.children:
                self._move_group_helper(i);

    def create_entry(self, group, **kwargs):
        """
        Create a new Entry object.
        
        The group which should hold the entry is needed.

        image must be an unsigned int >0, group a Group.
        
        :param group: The associated group.
        :keyword title: 
        :keyword icon:
        :keyword url:
        :keyword username:
        :keyword password:
        :keyword notes:
        :keyword expires: Expiration date (if None, entry will never expire). 
        :type expires: datetime
         
        :return: The new entry.
        :rtype: :class:`keepassdb.model.Entry`
        """
        if group not in self.groups:
            raise ValueError("Group doesn't exist / is not bound to this database.")
                 
        uuid = binascii.hexlify(get_random_bytes(16))
        
        entry = Entry(uuid=uuid,
                      group_id=group.id,
                      created=util.now(),
                      modified=util.now(),
                      accessed=util.now(),
                      **kwargs)
        
        self._entries.append(entry)
        group.entries.append(entry)
        
        return entry

    def remove_entry(self, entry):
        """This method can remove entries.
        
        :param entry: The Entry object to remove.
        :type entry: pwmanager.model.Entry
        """
        
        if entry is None or type(entry) is not Entry:
            raise exc.KPError("Need an entry.")
            
        elif entry in self._entries:
            entry.group.entries.remove(entry)
            self._entries.remove(entry)
            self._num_entries -= 1
            return True
        else:
            raise exc.KPError("Given entry doesn't exist.")
            

    def move_entry(self, entry=None, group=None):
        """Move an entry to another group.

        A Group group and a StdEntrytry are needed.

        """

        if entry is None or group is None or type(entry) is not Entry or \
            type(group) is not Group:
            raise exc.KPError("Need an entry and a group.")
            
        elif entry not in self._entries:
            raise exc.KPError("No entry found.")
            
        elif group in self.groups:
            entry.group.entries.remove(entry)
            group.entries.append(entry)
            entry.group_id = group.id
            return True
        else:
            raise exc.KPError("No group found.")
            
                
    def move_entry_in_group(self, entry, index):
        """
        Move entry to specified position in specified group.

        :param entry: The Entry object to move.
        :type entry: :class:`keepassdb.model.Entry`
        :param index: The 0-based index for the new position within group.
        :type index: int
        """
        if not isinstance(entry, Entry):
            raise TypeError("Invalid type for entry: {0!r}".format(entry))
        
        if index < 0 or index >= len(entry.group.entries):
            raise IndexError("Index is not within allowable range.")
            
        if entry not in self._entries:
            raise ValueError("Entry does not exist (or not bound to this db instance).")
        
        pos_in_group = entry.group.entries.index(entry)
        pos_in_entries = self._entries.index(entry)
        entry_at_index = entry.group.entries[index]
        pos_in_entries2 = self._entries.index(entry_at_index)

        entry.group.entries[index] = entry
        entry.group.entries[pos_in_group] = entry_at_index
        self._entries[pos_in_entries2] = entry
        self._entries[pos_in_entries] = entry_at_index

    def _bind_model(self):
        """This method creates a group tree"""

        if self.groups[0].level != 0:
            self.log.info("Got invalid first group: {0}".format(self.groups[0]))
            raise ValueError("Invalid group tree: first group must have level of 0 (got {0})".format(self.groups[0].level))
        
        # The KeePassX source code maintains that first group to have incremented 
        # level is a child of the previous group with a lower level
        #
        # [R]
        #  | A (1)
        #  +-| B (2)
        #  | | C (2)
        #  | D (1)
        #  +-| E (2)
        #    | F (2)
        #    +-| G (3)
        #      | H (3)
        #      | I (3)
        #       
        
        class Stack(list):
            """ A class to make parsing code slightly more semantic. """
            def push(self, el):
                self.append(el)

        # Consider replacing the below code (which is from KeePassX) with this version:  (Test it out ...)               
        # 
        parent_stack = Stack([self._root_group])        
        current_parent = self._root_group
        prev_group = None
        for g in self.groups:
            if prev_group is not None: # first iteration is exceptional
                if g.level > prev_group.level: # Always true for iteration 1 since _root_group has level of -1
                    # Dropping down a level; the previous group is the parent
                    current_parent = prev_group
                    parent_stack.push(current_parent)
                elif g.level < prev_group.level:
                    # Pop off parents until we have a parent with a level that is less than current
                    while g.level <= current_parent.level:
                        current_parent = parent_stack.pop()
                    parent_stack.push(current_parent) # We want to make sure that the top of the stack always matches current parent
                
            # bi-directional child-parent binding
            g.parent = current_parent
            current_parent.children.append(g)
            
            prev_group = g
           
        for entry in self._entries:
            for group in self.groups:
                if entry.group_id == group.id:
                    group.entries.append(entry)
                    entry.group = group

    def close(self):
        """
        Closes the database.
        """

    def to_dict(self, hierarchy=True, show_passwords=False):
        if hierarchy:
            d = dict(groups=[g.to_dict(hierarchy=hierarchy, show_passwords=show_passwords) for g in self._root_group.children])
        else:
            d = dict(groups=[g.to_dict(show_passwords=show_passwords) for g in self.groups])
        return d
     
class LockingDatabase(Database):
    """
    A convenience subclass that adds automatic file locking (if db not opened read-only).
    
    The lock is only acquired when the filepath is specified to a load() or save() operation. 
    The close() method will also release the lock.
    """
    
    _locked = False

    @property
    def lockfile(self):
        return self.filepath + '.lock'
    
    @property
    def filepath(self):
        """ Property for retrieving current filepath (or None if db not loaded from file) """
        return self._filepath
    
    @filepath.setter
    def filepath(self, value):
        """ Property for setting current filepath, automatically takes out lock on new file if not readonly db. """
        if not self.readonly and self._filepath != value:
            if self._locked:
                self.log.debug("Releasing previously-held lock file: {0}".format(self.lockfile))
                # Release the lock on previous filepath.
                self.release_lock()
            self._filepath = value
            if self._filepath is not None:
                self.acquire_lock()
        else:
            self._filepath = value
    
    def __enter__(self):
        """
        Take out a lock on the database file, supporting using as context manager.
        
        Note that the lock has probably already been taken out, but this won't hurt.
        """
        self.acquire_lock()
        return self
    
    def __exit__(self, exc_type, exc_value, exc_tb):
        """
        Release the lock on the database file, supporting using as context manager.
        """
        self.release_lock()
        
        return False # Do not suppress.
        
    def acquire_lock(self, force=False):
        """
        Takes out a lock (creates a <dbname>.lock file) for the database.
        :param force: Whether to force taking "ownership" of the lock file.
        :raise keepassdb.exc.DatabaseAlreadyLocked: If the database is already locked (and force not set to True)
        """
        if self.readonly:
            raise exc.ReadOnlyDatabase()
        if not self._locked:
            self.log.debug("Acquiring lock file: {0}".format(self.lockfile))
            if os.path.exists(self.lockfile) and not force:
                raise exc.DatabaseAlreadyLocked('Lock file already exists: {0}'.format(self.lockfile)) 
            open(self.lockfile, 'w').close()
            self._locked = True
            
    def release_lock(self, force=False):
        """
        Releases the lock  (deletes the <dbname>.lock file) if it was acquired by this class or force is set to True.
        
        :param force: Whether to force releasing the lock (e.g. if it was not acquired during this session).
        """
        if self.readonly:
            raise exc.ReadOnlyDatabase()
        if self._locked or force:
            self.log.debug("Removing lock file: {0}".format(self.lockfile))
            if os.path.exists(self.lockfile):
                os.remove(self.lockfile)
                self._locked = False
        else:
            self.log.debug("Database not locked (not removing)")
                  
    def close(self):
        """
        Closes the database, releasing lock.
        """
        super(LockingDatabase, self).close()
        if not self.readonly:
            self.release_lock()
