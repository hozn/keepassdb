# -*- coding: utf-8 -*-
"""
The database classes provide the primary API for loading and saving KeePass 1.x databases,
in addition to creating new groups and entries.
"""
import binascii
import logging
import os
import os.path
import hashlib

from Crypto.Random import get_random_bytes

from keepassdb import exc, util, const
from keepassdb.model import Group, Entry, RootGroup
from keepassdb.structs import HeaderStruct, GroupStruct, EntryStruct

__authors__ = ["Karsten-Kai König <kkoenig@posteo.de>", "Hans Lellelid <hans@xmpl.org>", "Brett Viren <brett.viren@gmail.com>"]
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

class Database(object):
    """
    This class represents the KeePass 1.x database.
    
    :ivar root: The group-like virtual root object (not actually part of database).
    :ivar groups: The flat list of groups (:class:`keepassdb.model.Group`) in this database.
    :ivar entries: The flat list of entries (:class:`keepassdb.model.Entry`) in this database.
    :ivar readonly: Whether database was opened read-only.
    :ivar filepath: The path to the database that is opened or will be written (if specified).
    :ivar password: The passphrase to use to encrypt the database.
    :ivar keyfile: A path to a keyfile that can be used instead or in combination with passphrase.
    :ivar header: The database header struct (:class:`keepassdb.structs.HeaderStruct`).
    """
    root = None
    groups = None # The flat list of :class:`keepassdb.model.Group` groups in this database.
    entries = None
    
    readonly = False
    header = None
    password = None
    keyfile = None
    _filepath = None
    
    def __init__(self, dbfile=None, password=None, keyfile=None, readonly=False, new=False):
        """
        Initialize a new or an existing database.
        
        :param dbfile: The path to the database file or a file-like object from which to read the database.
        :type dbfile: str or file
        :param password: Passphrase from which to derive key for file.
        :param password: str
        :param keyfile: The keyfile to use instead of or in conjunction with passphrase.
        :param keyfile: str or file
        :param readonly: Whether to open the database read-only (e.g. if already open in another process)
        :type readonly: bool
        :param new: Whether this is a new database (only necessary when specifying filepath so that file 
                   will not attempt to be loaded).
        :type new: bool
        """
        self.log = logging.getLogger('{0.__module__}.{0.__name__}'.format(self.__class__))
        
        
        self.password = password
        self.keyfile = keyfile
        
        self.root = RootGroup()
        self.groups = []
        self.entries = []
        
        if new:
            if hasattr(dbfile, 'read'):
                raise TypeError("Cannot specify file object for new database")
            self.filepath = dbfile # XXX: Consider if we should be invoking the setter here or not.
        elif dbfile:
            self.load(dbfile, password=password, keyfile=keyfile, readonly=readonly)
    
    def _clear(self):
        """
        Resets/clears out internal object state.
        """
        self.root = RootGroup()
        self.groups = []
        self.entries = []
        self.readonly = False
        self.header = None
        self.password = None
        self.keyfile = None
        self.filepath = None
    
    @property
    def filepath(self):
        """ Property for retrieving current filepath (or None if db not loaded from file) """
        return self._filepath
    
    @filepath.setter
    def filepath(self, value):
        """ Proerty for setting current filepath. """
        self._filepath = value
        
    def create_default_group(self):
        """
        Create a default 'Internet' group on an empty database.
        
        :returns: The new 'Internet' group.
        :rtype: :class:`keepassdb.model.Group`
        """
        assert len(self.groups) == 0, "initialize_empty() should only be used with a new database."
        return self.create_group(u'Internet', icon=1)
                
    def load(self, dbfile, password=None, keyfile=None, readonly=False):
        """
        Load the database from file/stream.
        
        :param dbfile: The database file path/stream.
        :type dbfile: str or file-like object
        :param password: The password for the database.
        :type password: str
        :param keyfile: Path to a keyfile (or a stream) that can be used instead of or in conjunction with password for database.
        :type keyfile: str or file-like object
        :param readonly: Whether to open the database read-only.
        :type readonly: bool
        """
        
        self._clear()
        buf = None
        is_stream = hasattr(dbfile, 'read') 
        if is_stream:
            buf = dbfile.read()
        else:
            if not os.path.exists(dbfile):
                raise IOError("File does not exist: {0}".format(dbfile))
            
            with open(dbfile, 'rb') as fp:
                buf = fp.read()
                
        self.load_from_buffer(buf, password=password, keyfile=keyfile, readonly=readonly)
        
        # One we have successfully loaded the file, go ahead and set the internal attribute
        # (in the LockingDatabase subclass, this will effectivley take out the lock on the file)
        if not is_stream:
            self.filepath = dbfile
             
    
    def load_from_buffer(self, buf, password=None, keyfile=None, readonly=False):
        """
        Load a database from passed-in buffer (bytes).

        :param buf: A string (bytes) of the database contents.
        :type buf: str
        :param password: The password for the database.
        :type password: str
        :param keyfile: Path to a keyfile (or a stream) that can be used instead of or in conjunction with password for database.
        :type keyfile: str or file-like object
        :param readonly: Whether to open the database read-only.
        :type readonly: bool
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
        
        # FIXME: Remove this once we've tracked down issues.
        self.log.debug("(load) Final key: {0!r}, pass={1}".format(final_key, password))
        
        decrypted_content = util.decrypt_aes_cbc(crypted_content, key=final_key, iv=self.header.encryption_iv)
        
        # Check if decryption failed
        if ((len(decrypted_content) > const.DB_MAX_CONTENT_LEN) or
            (len(decrypted_content) == 0 and self.header.ngroups > 0)):
            raise exc.IncorrectKey("Decryption failed! The key is wrong or the file is damaged.")
        
        if not self.header.contents_hash == hashlib.sha256(decrypted_content).digest():
            self.log.debug("Decrypted content: {0!r}".format(decrypted_content))
            self.log.error("Hash mismatch. Header hash = {0!r}, hash of contents = {1!r}".format(self.header.contents_hash,                                                                                                 hashlib.sha256(decrypted_content).digest()))
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
            self.entries.append(Entry.from_struct(estruct))
            length = len(estruct)
            decrypted_content = decrypted_content[length:]
            
        # Sets up the hierarchy, relates the group/entry model objects.
        self._bind_model()
        
    def save(self, dbfile=None, password=None, keyfile=None):
        """
        Save the database to specified file/stream with password and/or keyfile.
         
        :param dbfile: The path to the file we wish to save.
        :type dbfile: The path to the database file or a file-like object.
        
        :param password: The password to use for the database encryption key.
        :type password: str
        :param keyfile: The path to keyfile (or a stream) to use instead of or in conjunction with password for encryption key.
        :type keyfile: str or file-like object
        :raise keepassdb.exc.ReadOnlyDatabase: If database was opened with readonly flag.
        """
        if self.readonly:
            # We might wish to make this more sophisticated.  E.g. if a new path is specified
            # as a parameter, then it's probably ok to ignore a readonly flag?  In general
            # this flag doens't make a ton of sense for a library ...
            raise exc.ReadOnlyDatabase()
        
        if dbfile is not None and not hasattr(dbfile, 'write'):
            self.filepath = dbfile
            
        if password is not None or self.keyfile is not None:
            # Do these together so we don't end up with some hybrid of old & new key material
            self.password = password
            self.keyfile = keyfile  
        else: 
            raise ValueError("Password and/or keyfile is required.")
        
        if self.filepath is None and dbfile is None:
            raise ValueError("Unable to save without target file.")
        
        buf = bytearray()
        
        # First, serialize the groups
        for group in self.groups:
            # Get the packed bytes
            group_struct = group.to_struct()
            self.log.debug("Group struct: {0!r}".format(group_struct))
            buf += group_struct.encode()
            
        # Then the entries.
        for entry in self.entries:
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
        
        # Convert buffer to bytes for API simplicity
        buf = bytes(buf)
        
        # Generate new seed & vector; update content hash        
        header.encryption_iv = get_random_bytes(16)
        header.seed_rand = get_random_bytes(16)
        header.contents_hash = hashlib.sha256(buf).digest()
        
        self.log.debug("(Unencrypted) content: {0!r}".format(buf))
        self.log.debug("Generating hash for {0}-byte content: {1}".format(len(buf), hashlib.sha256(buf).digest()))
        # Update num groups/entries to match curr state
        header.nentries = len(self.entries)
        header.ngroups = len(self.groups)
        
        final_key = util.derive_key(seed_key=header.seed_key,
                                    seed_rand=header.seed_rand,
                                    rounds=header.key_enc_rounds,
                                    password=password, keyfile=keyfile)
        
        # FIXME: Remove this once we've tracked down issues.
        self.log.debug("(save) Final key: {0!r}, pass={1}".format(final_key, password))
        
        encrypted_content = util.encrypt_aes_cbc(buf, key=final_key, iv=header.encryption_iv)
        
        if hasattr(dbfile, 'write'):
            dbfile.write(header.encode() + encrypted_content)
        else:
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
            group.parent = self.root
            self.root.children.append(group)
            group.level = 0
            self.groups.append(group)
            
        # Else insert the group behind the parent
        else:
            if parent not in self.groups:
                raise ValueError("Group doesn't exist / is not bound to this database.")
            parent.children.append(group)
            group.parent = parent
            group.level = parent.level + 1
            self.groups.insert(self.groups.index(parent) + 1, group)
                
        return group

    def remove_group(self, group):
        """
        Remove the specified group.
        """
        if not isinstance(group, Group):
            raise TypeError("group must be Group")
        if group not in self.groups:
            raise ValueError("Group doesn't exist / is not bound to this database.")
        
        # Recurse down to remove sub-groups
        for child in group.children: # We may need to copy this to avoid CME (see below)
            self.remove_group(child)
        
        for entry in group.entries:
            self.remove_entry(entry)
        
        # Finally remove group from the parent's list.
        group.parent.children.remove(group) # Concurrent modification exception? Parent in recursive stack is iterating ...
        self.groups.remove(group)
        
            
    def move_group(self, group, parent, index=None):
        """
        Move group to be a child of new parent.
        
        :param group: The group to move.
        :type group: :class:`keepassdb.model.Group`
        :param parent: The new parent for the group.
        :type parent: :class:`keepassdb.model.Group`
        :param index: The 0-based index within the parent (defaults to appending
                      group to end of parent's children).
        :type index: int
        """
        if not isinstance(group, Group):
            raise TypeError("group param must be of type Group")
        
        if parent is not None and not isinstance(parent, Group):
            raise TypeError("parent param must be of type Group")
            
        if group is parent:
            raise ValueError("group and parent are the same")
            
        if parent is None:
            parent = self.root
            
        if group not in self.groups:
            raise exc.UnboundModelError("Group doesn't exist / is not bound to this database.")
        
        if parent not in self.groups:
            raise exc.UnboundModelError("Parent group doesn't exist / is not bound to this database.")
        
        curr_parent = group.parent
        curr_parent.children.remove(group)
        
        if index is None:
            parent.children.append(group)
            self.log.debug("Moving {0!r} to child of {1!r}, (appending)".format(group, parent))
        else:
            parent.children.insert(index, group)
            self.log.debug("Moving {0!r} to child of {1!r}, (at position {2!r})".format(group, parent, index))
        
        group.parent = parent
        group.modified = util.now()
        
        self._rebuild_groups()
                    
        
    def _rebuild_groups(self):
        """
        Recreates the groups master list based on the groups hierarchy (order matters here,
        since the parser uses order to determine lineage).
        """
        self.groups = []
        
        def collapse_group(group):
            for subgroup in group.children:
                self.groups.append(subgroup)
                collapse_group(subgroup)
                
        collapse_group(self.root)

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
        
        self.entries.append(entry)
        group.entries.append(entry)
        
        return entry

    def remove_entry(self, entry):
        """
        Remove specified entry.
        
        :param entry: The Entry object to remove.
        :type entry: :class:`keepassdb.model.Entry`
        """
        if not isinstance(entry, Entry):
            raise TypeError("entry param must be of type Entry.")
        if not entry in self.entries:
            raise ValueError("Entry doesn't exist / not bound to this datbase.")
        
        entry.group.entries.remove(entry)
        self.entries.remove(entry)

    def move_entry(self, entry, group, index=None):
        """
        Move an entry to another group.
        
        :param entry: The Entry object to move.
        :type entry: :class:`keepassdb.model.Entry`
        
        :param group: The new parent Group object for the entry.
        :type group: :class:`keepassdb.model.Group`
        
        :param index: The 0-based index within the parent (defaults to appending
                      group to end of parent's children).
        :type index: int
        """
        if not isinstance(entry, Entry):
            raise TypeError("entry param must be of type Entry")
        if not isinstance(group, Group):
            raise TypeError("group param must be of type Group")
        
        if entry not in self.entries:
            raise exc.UnboundModelError("Invalid entry (or not bound to this database): {0!r}".format(entry))
        if group not in self.groups:
            raise exc.UnboundModelError("Invalid group (or not bound to this database): {0!r}".format(group))
        
        curr_group = entry.group
        
        curr_group.entries.remove(entry)
        if index is None:
            group.entries.append(entry)
            self.log.debug("Moving {0!r} to child of {1!r}, (appending)".format(entry, group))
        else:
            group.entries.insert(index, entry)
            self.log.debug("Moving {0!r} to child of {1!r}, (at position {2})".format(entry, group, index))
            
        entry.group = group
        
        entry.modified = util.now()
        
        self._rebuild_entries()
        
    def _rebuild_entries(self):
        """
        Recreates the entries master list based on the groups hierarchy (order matters here,
        since the parser uses order to determine lineage).
        """
        self.entries = []
        def collapse_entries(group):
            for entry in group.entries:
                self.entries.append(entry)
            for subgroup in group.children:
                collapse_entries(subgroup)
                
        collapse_entries(self.root)
        
    def _bind_model(self):
        """
        This method binds the various model objects together in the correct hierarchy
        and adds referneces to this database object in the groups.
        """

        if self.groups[0].level != 0:
            self.log.info("Got invalid first group: {0}".format(self.groups[0]))
            raise ValueError("Invalid group tree: first group must have level of 0 (got {0})".format(self.groups[0].level))
        
        # The KeePassX source code maintains that first group to have incremented 
        # level is a child of the previous group with a lower level.
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

        # This is a different parsing approach than taken by KeePassX (or other python               
        # libs), but seems a little more intuitive.  It could be further simplified
        # by noting that current_parent is always parent_stack[-1], but this is a bit
        # more readable.
        parent_stack = Stack([self.root])        
        current_parent = self.root
        prev_group = None
        for g in self.groups:
            g.db = self # Bind database to group objects
            if prev_group is not None: # first iteration is exceptional
                if g.level > prev_group.level: # Always true for iteration 1 since root has level of -1
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
            
        # Bind group objects to entries
        for entry in self.entries:
            for group in self.groups:
                if entry.group_id == group.id:
                    group.entries.append(entry)
                    entry.group = group
                    break
            else:
                # KeePassX adds these to the first group (i.e. root.children[0])
                raise NotImplementedError("Orphaned entries not (yet) supported.")

    def close(self):
        """
        Closes the database, performs any necessary cleanup functions.
        """

    def to_dict(self, hierarchy=True, hide_passwords=False):
        if hierarchy:
            d = dict(groups=[g.to_dict(hierarchy=hierarchy, hide_passwords=hide_passwords) for g in self.root.children])
        else:
            d = dict(groups=[g.to_dict(hide_passwords=hide_passwords) for g in self.groups])
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
        :type force: bool
        :raises: :class:`keepassdb.exc.DatabaseAlreadyLocked` - If the database is already locked (and force not set to True).
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
        :type force: bool
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
