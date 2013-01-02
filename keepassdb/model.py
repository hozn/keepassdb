# -*- coding: utf-8 -*-
"""
The model consists of the Group and Entity classes that together make up the contents
of the database.  These classes are directly related to their :mod:`keepassdb.structs`
counterparts; however, they also track the hierarchy of the database, track modification
times, and provide convenience methods to perform create and move operations.
""" 

__authors__ = ["Brett Viren <brett.viren@gmail.com>","Hans Lellelid <hans@xmpl.org>"]
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

import abc
import logging
import base64

from keepassdb import const, util
from keepassdb.structs import GroupStruct, EntryStruct

__authors__ = ["Karsten-Kai König <kkoenig@posteo.de>", "Hans Lellelid <hans@xmpl.org>"]
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

class BaseModel(object):
    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        self.log = logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))
        
    @abc.abstractproperty
    def struct_type(self):
        pass
    
    @classmethod
    def from_struct(cls, structobj):
        """
        Initialize properties of this model object from specified struct object.
        
        :param structobj: The sturct object instance to use for initialization.
        """
        kwargs = structobj.attributes()
        return cls(**kwargs)
    
    def to_struct(self):
        """
        Initialize properties of the appropriate struct class from this model class.
        """
        structobj = self.struct_type()
        for k in structobj.attributes():
            self.log.info("Setting attribute %s to %r" % (k, getattr(self, k)))
            setattr(structobj, k, getattr(self, k))
        return structobj
        
class RootGroup(object):
    """
    A group-like object that serves as the root node of the tree.
    
    This is the `root` attribute of the :class:`keepassdb.db.Database` instance.
    
    This object is not written to the database; it simply exists to provide
    a virtual node from which to make the top-level groups children.
    
    :ivar title: The title for the group ('Root Group')
    :ivar level: The hierarchy level / depth in tree; This is -1 for root group. 
    :ivar children: List of children groups (:class:`keepassdb.model.Group`)
    """
    parent = None
    level = -1
    children = None
    entries = None
    title = 'Root Group'
    
    def __init__(self):
        self.children = []
        self.entries = []
    
    def __repr__(self):
        return '<RootGroup>'
    
class Group(BaseModel):
    """
    Represents a single group of a KeePass 1.x database.
    
    :ivar db: The parent database (:class:`keepassdb.db.Database`)
    :ivar id: The group numeric id (unsigned int)
    :ivar title: The group title (string)
    :ivar level: The hierarchy level / depth in tree (unsigned int)
    :ivar icon: The group icon identifier used in KeePassX (unsigned int)
    :ivar parent: The parent group (:class:`keepassdb.model.Group`)
    :ivar children: List of children groups (:class:`keepassdb.model.Group`)
    :ivar entries: List of member entries (:class:`keepassdb.model.Entry`)
    """
    
    # These are the shadow attribs for our getters and setters
    _title = None
    _icon = None
    _expires = None

    struct_type = GroupStruct
    
    def __init__(self, id=None, title=None, icon=None, level=None, created=None, modified=None,
                 accessed=None, expires=None, flags=None, parent=None, db=None):
        """
        Initialize a new Group object with optional attributes.
        
        Use the :method:`Group.parse` class method if you would like to initialize a group
        from the data structure.
        """
        super(Group, self).__init__()
        if icon is None:
            icon = 1            
        if created is None:
            created = util.now()
        if modified is None:
            modified = util.now()
        if accessed is None:
            accessed = util.now()
        if expires is None:
            expires = const.NEVER
        if flags is None:
            flags = 0  # XXX: Need to figure out what this is, but 0 seems to be the correct default
        
        self.id = id
        self._title = title
        self._icon = icon
        self.level = level
        self.created = created
        self.modified = modified
        self.accessed = accessed
        self._expires = expires
        self.flags = flags
        
        # TODO: Determine how we want to handle these other attributes.
        self.parent = parent
        self.db = db
        self.children = []
        self.entries = []
    
    def __repr__(self):
        return '<Group title={0} id={1} level={2}>'.format(self.title,
                                                           self.id,
                                                           self.level)
            
    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        self._title = value
        self.modified = util.now()
    
    @property
    def icon(self):
        return self._icon
    
    @icon.setter
    def icon(self, value):
        self._icon = value
        self.modified = util.now()
        
    @property
    def expires(self):
        return self._expires
    
    @expires.setter
    def expires(self, value):
        self._expires = value
        self.modified = util.now()
        
    def move(self, parent, index=None):
        """
        Move this group to a new parent.
        
        :param parent: The new parent group; if None will be root group.
        :type parent: :class:`keepassdb.model.Group`
        :param index: The 0-based index within the parent (defaults to appending
                      group to end of parent's children).
        :type index: int
        """
        return self.db.move_group(self, parent, index=index)

    def change_index(self, index):
        """
        Move the group to the new 0-based index within the same parent.
        
        :param index: The 0-based index for the new position within parent group.  Note that this
                    index will be evaluated *after* the group has been removed from the list.
        :type index: int
        """
        return self.db.change_group_index(self, index)

    def remove(self):
        """This method calls remove_group of the holding db"""
        return self.db.remove_group(self)

    def create_entry(self, **kwargs):
        """
        This method creates an entry in this group.

        :keyword title: 
        :keyword icon:
        :keyword url:
        :keyword username:
        :keyword password:
        :keyword notes:
        :keyword expires: Expiration date (if None, entry will never expire). 
        :type expires: datetime
        """
        return self.db.create_entry(group=self, **kwargs)

    def to_dict(self, hierarchy=True, hide_passwords=False):
        d = dict(id=self.id,
                 title=self.title,
                 icon=self.icon,
                 level=self.level,
                 created=self.created if self.created != const.NEVER else None,
                 modified=self.modified if self.modified != const.NEVER else None,
                 accessed=self.accessed if self.accessed !=  const.NEVER else None,
                 expires=self.expires if self.expires != const.NEVER else None,
                 flags=self.flags
                 )
        d['entries'] = [e.to_dict(hide_passwords=hide_passwords) for e in self.entries]
        if hierarchy:
            d['children'] = [g.to_dict(hierarchy=hierarchy, hide_passwords=hide_passwords) for g in self.children]
            
        return d
    
        
class Entry(BaseModel):
    """Entry represents a simple entry of a KeePass 1.x database.
    
    :ivar uuid: The ID for the entry.
    :ivar group_id: The numeric ID for the group.
    :ivar group: The group object that this entity is related to.
    :ivar icon: The icon identifier.
    :ivar title: The title for the entry.
    :ivar username: The username.        
    :ivar password: The password
    :ivar url: The entry URL.
    :ivar notes: Notes/comment for the entry.
    :ivar created: When entry was created (default: now)
    :ivar modified: When entry was last modified (default: now)
    :ivar accessed: When the entry was last accessed (default: now)
    :ivar expires: When the entry (password) expires.  Default will be :ref:`keepassdb.const.NEVER`.
    :ivar binary_desc: Description/metadata for the binary column.
    :ivar binary: Binary contents.
    """ 
    
    struct_type = EntryStruct
    _group = None

    def __init__(self, uuid = None, group_id = None, group = None,
                 icon = None, title = None, url = None, username = None,
                 password = None, notes = None, 
                 created = None, modified = None, accessed = None, 
                 expires = None, binary_desc = None, binary = None):
        """
        Initialize a Entry-instance with provided attributes.
        
        Typically Entry objects should be created using the :meth:`Group.create_entry` method 
        which will additionally bind the entry to the group.
        
        :keyword uuid: The ID for the entry.
        :type uuid: str (16 bytes)
        
        :keyword group_id: The numeric ID for the group.
        :type group_id: int
        
        :keyword group: The group object that this entity is related to.
        :type group: :class:`Group`
        
        :keyword icon: The icon identifier.
        :type icon: int

        :keyword title: The title for the entry.
        :type username: unicode

        :keyword username: The username.
        :type username: unicode
        
        :keyword password: The password
        :type password: unicode
        
        :keyword url: The entry URL.
        :type url: unicode
        
        :keyword notes: Notes/comment for the entry.
        :type notes: unicode
        
        :keyword created: When entry was created (default: now)
        :type created: :class:`datetime.datetime`
        
        :keyword modified: When entry was last modified (default: now)
        :type modified: :class:`datetime.datetime`
        
        :keyword accessed: When the entry was last accessed (default: now)
        :type accessed: :class:`datetime.datetime`
        
        :keyword expires: When the entry (password) expires.  Default will be :ref:`keepassdb.const.NEVER`.
        :type expires :class:`datetime.datetime`
        
        :keyword binary_desc: Description/metadata for the binary column.
        :type binary_desc: unicode
        
        :keyword binary: Binary contents.
        :type binary: str
        """
        super(Entry, self).__init__()
        if icon is None:
            icon = 1    
        if created is None:
            created = util.now()
        if modified is None:
            modified = util.now()
        if accessed is None:
            accessed = util.now()
        if expires is None:
            expires = const.NEVER
        
        # Some casting to strings here, since this is what we'll get when we read
        # these entries from the database.  (Probably needs to be more comprehensive.)
        if title is None: title = u''
        if notes is None: notes = u''
        if url is None: url = u''
        if binary is None: binary = b''
        if binary_desc is None: binary_desc = u''
        
        self.uuid = uuid
        self.group_id = group_id
        self.group = group
        
        # Property attributes
        self._icon = icon
        self._title = title
        self._url = url
        self._username = username
        self._password = password
        self._notes = notes
        
        self.created = created
        self.modified = modified
        self.accessed = accessed
        self._expires = expires
        self.binary_desc = binary_desc
        self.binary = binary

    def __repr__(self):
        return '<Entry title={0} username={1}>'.format(self.title,
                                                       self.username)

    @property
    def group(self):
        return self._group
    
    @group.setter
    def group(self, value):
        self._group = value
        if value is not None:
            self.group_id = value.id
        
    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, value):
        self._title = value
        self.modified = util.now()
    
    
    @property
    def icon(self):
        return self._icon
    
    @icon.setter
    def icon(self, value):
        self._icon = value
        self.modified = util.now()
    
    @property
    def url(self):
        return self._url
    
    @url.setter
    def url(self, value):
        self._url = value
        self.modified = util.now()
    
    @property
    def username(self):
        return self._username
    
    @username.setter
    def username(self, value):
        self._username = value
        self.modified = util.now()
    
    @property
    def password(self):
        return self._password
    
    @password.setter
    def password(self, value):
        self._password = value
        self.modified = util.now()
        
    @property
    def notes(self):
        return self._notes
    
    @notes.setter
    def notes(self, value):
        self._notes = value
        self.modified = util.now()
        
    @property
    def expires(self):
        return self._expires
    
    @expires.setter
    def expires(self, value):
        self._expires = value
        self.modified = util.now()
        
    def move(self, group, index=None):
        """
        This method moves the entry to another group.
        """
        return self.group.db.move_entry(self, group, index=index)

    def change_index(self, index):
        """
        This method moves the entry to another position in the group.
        """
        return self.group.db.move_entry_in_group(self, index)

    def remove(self):
        """
        This method removes this entry.
        """
        return self.group.db.remove_entry(self)
    
    def to_dict(self, hide_passwords=False):
        d = dict(uuid=self.uuid,
                 group_id=self.group_id,
                 icon=self.icon,
                 title=self.title,
                 url=self.url,
                 username=self.username,
                 password=self.password if not hide_passwords else '********',
                 notes=self.notes,
                 created=self.created if self.created != const.NEVER else None,  
                 modified=self.modified if self.modified != const.NEVER else None,
                 expires=self.expires if self.expires != const.NEVER else None,
                 binary_desc=self.binary_desc,
                 binary=base64.b64encode(self.binary) if self.binary is not None else ''
                 )
        return d