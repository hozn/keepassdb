"""
Support for reading and writing the structures that comprise the keepass database.

This module is derived from the elegant parsing improvements Brett Viren <brett.viren@gmail.com>
introduced in the `python-keepass <https://github.com/brettviren/python-keepass>`_ project.
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
import struct
import logging
from datetime import datetime
from binascii import hexlify, unhexlify

from keepassdb import exc, const

class Marshall(object):
    """ Abstract base class for the marshall implementations. """
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod  
    def encode(self, val):
        """
        Encode the specified value as the binary string representation needed for the database.
        
        :rtype: str 
        """
    
    @abc.abstractmethod
    def decode(self, buf):
        """
        Decode value from database's binary string representation to something that will be
        useful for library consumers.
        
        :type buf: str
        """

class MarshallNone(Marshall):
    """ A None-returning dummy marshaller. """
    def encode(self, val):
        return None
    
    def decode(self, buf):
        return None

class MarshallPass(Marshall):
    """ Pass-through marshall implemenatation (e.g. for binary data). """
    def encode(self, val):
        return val
    
    def decode(self, buf):
        return buf

class MarshallString(Marshall):
    """ Encode/decode unicode or string values. """
    def encode(self, val):
        """
        Encode specified unicode value as UTF-8 string with null-byte termination.
         
        :param val: The unicode (or str) input value. 
        :type val: unicode
        :rtype: str
        """
        if val is None:
            val = u''
        return val.encode('utf-8') + b'\0'
    
    def decode(self, buf):
        """
        Decode buffer (UTF-8 bytes) to unicode string and remove null termination byte.
        
        :param buf: The bytes.
        :type buf: str
        :rtype: unicode
        """
        return buf.rstrip(b'\0').decode('utf-8')
    
class MarshallAscii(Marshall):
    """
    Encode/decode values by converting to hex notation.
    """
    def encode(self, val):
        """
        Encode the specified value by hex *decoding* the input string.
        
        :param val: The hex-encoded input string.
        :type val: str
        :returns: unhexlified / base-16-decoded byte value. 
        :rtype: str
        """
        return unhexlify(val)
    
    def decode(self, buf):
        """
        Decode the specified value by hex *encoding* the input string.
        
        :param buf: The the byte value to encode.
        :type buf: str
        :returns: hexlified / base-16-encoded value.
        :rtype: str  
        """
        return hexlify(buf)
    
class MarshallShort(Marshall):
    """ Encode/decode short int values. """
    def encode(self, val):
        return struct.pack("<H", val)
    
    def decode(self, buf):
        return struct.unpack("<H", buf)[0]
    
class MarshallInt(Marshall):
    """ Encode/decode int/long values. """
    def encode(self, val):
        return struct.pack("<L", val)
    
    def decode(self, buf):
        return struct.unpack("<L", buf)[0]
         
class MarshallDate(Marshall):
    """
    Marshall the date format needed for keepass db to/from python datetime objects.
    """
    
    def decode(self, buf):
        """
        Decodes the date field into a python datetime object. 
        
        :returns: The decoded datetime object.
        :rtype: :class:`datetime.datetime`
        """
        date_field = struct.unpack('<5B', buf)
        dw1 = date_field[0]
        dw2 = date_field[1]
        dw3 = date_field[2]
        dw4 = date_field[3]
        dw5 = date_field[4]

        y = (dw1 << 6) | (dw2 >> 2)
        mon = ((dw2 & 0x03) << 2) | (dw3 >> 6)
        d = (dw3 >> 1) & 0x1F
        h = ((dw3 & 0x01) << 4) | (dw4 >> 4)
        min_ = ((dw4 & 0x0F) << 2) | (dw5 >> 6)
        s = dw5 & 0x3F
        return datetime(y, mon, d, h, min_, s)
    
    def encode(self, val):
        """
        Encode the python datetime value into the bytes needed for database format. 
        
        :param val: The datetime object.
        :type val: :class:`datetime.datetime`
        :returns: Bytes for data. 
        :rtype: str
        """
        # Just copied from original KeePassX source
        y, mon, d, h, min_, s = val.timetuple()[:6]

        dw1 = 0x0000FFFF & ((y >> 6) & 0x0000003F)
        dw2 = 0x0000FFFF & ((y & 0x0000003F) << 2 | ((mon >> 2) & 0x00000003))
        dw3 = 0x0000FFFF & (((mon & 0x0000003) << 6) | ((d & 0x0000001F) << 1) \
                | ((h >> 4) & 0x00000001))
        dw4 = 0x0000FFFF & (((h & 0x0000000F) << 4) | ((min_ >> 2) & 0x0000000F))
        dw5 = 0x0000FFFF & (((min_ & 0x00000003) << 6) | (s & 0x0000003F))

        return struct.pack('<5B', dw1, dw2, dw3, dw4, dw5) 
    
    
class StructBase(object):
    """
    Abstract base class for the struct representations.
    """
    __metaclass__ = abc.ABCMeta
    
    order = None
    
    def __init__(self, buf=None):
        self.order = []         # keep field order
        self.log = logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))
        if buf:
            self.decode(buf)

    def __repr__(self):
        ret = [self.__class__.__name__ + ':']
        for num, form in self.format.items():
            attr = form[0]
            if attr is None:
                continue
            try:
                ret.append('  %s=%r' % (attr, getattr(self, attr)))
            except AttributeError:
                pass
        return '\n'.join(ret)

    def __str__(self):
        """
        Return formatted string for this entry.
        """
        dat = self.attributes()
        dat['path'] = self.path()
        return self.label_format % dat

    @abc.abstractproperty
    def label_format(self):
        pass
        
    @abc.abstractproperty
    def format(self):
        pass

    def attributes(self):
        """
        Returns a dict of all this structures attributes and values, skipping
        any attributes that start with an underscore (assumed they should be ignored).
        """
        return dict([(name, getattr(self, name)) for (name, _) in self.format.values() if name is not None and not name.startswith('_')])
    
    def decode(self, buf):
        """
        Set object attributes from binary string representation.
        
        :param buf: The binary string representation of this object in database.
        :type buf: str
        :raises: :class:`keepassdb.exc.ParseError` - If errors encountered parsing struct.
        """
        index = 0
        while True:
            #self.log.debug("buffer state: index={0}, buf-ahead={1!r}".format(index, buf[index:]))
            substr = buf[index:index + 6]
            index += 6
            if index > len(buf):
                raise ValueError("Group header offset is out of range: {0}".format(index))
            (typ, siz) = struct.unpack('<H L', substr)
            self.order.append((typ, siz))
            
            substr = buf[index:index + siz]
            index += siz
            encoded = struct.unpack('<%ds' % siz, substr)[0]
            
            (name, marshall) = self.format[typ]
            if name is None:
                break
            try:
                value = marshall.decode(encoded)
                self.log.debug("Decoded field [{0}] to value {1!r}".format(name, value))
            except struct.error, msg:
                msg = '%s, typ=%d[size=%d] -> %s [buf = "%r"]' % \
                    (msg, typ, siz, self.format[typ], encoded)
                raise exc.ParseError(msg)
            setattr(self, name, value)

    def __len__(self):
        length = 0
        for typ, siz in self.order:
            length += 2 + 4 + siz
        return length

    def encode(self):
        """
        Return binary string representation of object.
        
        :rtype: str
        """
        buf = bytearray()
        for typ in sorted(self.format.keys()):
            encoded = None
            if typ != 0xFFFF: # end of block
                (name, marshall) = self.format[typ]
                value = getattr(self, name, None)
                if value is not None:
                    try:
                        encoded = marshall.encode(value)
                        self.log.debug("Encoded field [{0}] to value {1!r}".format(name, encoded))
                    except:
                        self.log.exception("Error encoding key/value: key={0}, value={1!r}".format(name, value))
                        raise
            
            # Note, there is an assumption here that encode() func is returning
            # a byte string (so len = num bytes).  That should be a safe assumption.
            size = len(encoded) if encoded is not None else 0
            packed = struct.pack('<H', typ)
            packed += struct.pack('<I', size)
            if encoded is not None:
                if isinstance(encoded, bytearray):
                    encoded = str(encoded)
                elif isinstance(encoded, unicode):
                    encoded = encoded.encode('utf-8')
                packed += struct.pack('<%ds' % size, encoded)
                
            buf += packed
            
        return buf

    def path(self):
        path = ""
        parent = self.parent
        while parent:
            path = parent.title + "/" + path
            parent = parent.parent
        return "/" + path

    
class GroupStruct(StructBase):
    """
    Structure representing a single group.
    
    Basic structure: [FIELDTYPE(FT)][FIELDSIZE(FS)][FIELDDATA(FD)]
           [FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)]...
    
    General structure:
    
    - [ 2 bytes] FIELDTYPE
    - [ 4 bytes] FIELDSIZE, size of FIELDDATA in bytes
    - [ n bytes] FIELDDATA, n = FIELDSIZE
    
    Notes:
    
    * Strings are stored in UTF-8 encoded form and are null-terminated.
    * FIELDTYPE can be one of the following identifiers:
     * 0000: Invalid or comment block, block is ignored
     * 0001: Group ID, FIELDSIZE must be 4 bytes
             It can be any 32-bit value except 0 and 0xFFFFFFFF
     * 0002: Group name, FIELDDATA is an UTF-8 encoded string
     * 0003: Creation time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 0004: Last modification time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 0005: Last access time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 0006: Expiration time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 0007: Image ID, FIELDSIZE must be 4 bytes
     * 0008: Level, FIELDSIZE = 2
     * 0009: Flags, 32-bit value, FIELDSIZE = 4
     * FFFF: Group entry terminator, FIELDSIZE must be 0
    """
    
    # Struct attributes
    id = None
    title = None
    icon = None
    level = None
    created = None
    modified = None
    accessed = None
    expires = None
    flags = None
     
    format = {
            0x0: ('_ignored', MarshallNone()),
            0x1: ('id', MarshallInt()),
            0x2: ('title', MarshallString()),
            0x3: ('created', MarshallDate()),
            0x4: ('modified', MarshallDate()),
            0x5: ('accessed', MarshallDate()),
            0x6: ('expires', MarshallDate()),
            0x7: ('icon', MarshallInt()),
            0x8: ('level', MarshallShort()),
            0x9: ('flags', MarshallInt()),
            0xFFFF: (None, None),
        }
    
    @property
    def label_format(self):
        return "Group %(title)s"

class EntryStruct(StructBase):
    '''
    One entry: [FIELDTYPE(FT)][FIELDSIZE(FS)][FIELDDATA(FD)]
           [FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)][FT+FS+(FD)]...

    Basic structure:
    
    * [ 2 bytes] FIELDTYPE
    * [ 4 bytes] FIELDSIZE, size of FIELDDATA in bytes
    * [ n bytes] FIELDDATA, n = FIELDSIZE
    
    Notes:
    
    * Strings are stored in UTF-8 encoded form and are null-terminated.
    * FIELDTYPE can be one of the following identifiers:
     * 0000: Invalid or comment block, block is ignored
     * 0001: UUID, uniquely identifying an entry, FIELDSIZE must be 16
     * 0002: Group ID, identifying the group of the entry, FIELDSIZE = 4
             It can be any 32-bit value except 0 and 0xFFFFFFFF
     * 0003: Image ID, identifying the image/icon of the entry, FIELDSIZE = 4
     * 0004: Title of the entry, FIELDDATA is an UTF-8 encoded string
     * 0005: URL string, FIELDDATA is an UTF-8 encoded string
     * 0006: UserName string, FIELDDATA is an UTF-8 encoded string
     * 0007: Password string, FIELDDATA is an UTF-8 encoded string
     * 0008: Notes string, FIELDDATA is an UTF-8 encoded string
     * 0009: Creation time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 000A: Last modification time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 000B: Last access time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 000C: Expiration time, FIELDSIZE = 5, FIELDDATA = packed date/time
     * 000D: Binary description UTF-8 encoded string
     * 000E: Binary data
     * FFFF: Entry terminator, FIELDSIZE must be 0
    '''
    uuid = None
    group_id = None
    icon = None
    title = None
    url = None
    username = None
    password = None
    notes = None
    created = None
    modified = None
    accessed = None
    expires = None
    binary_desc = None
    binary = None
    
    format = {
            0x0: ('_ignored', MarshallNone()),
            0x1: ('uuid', MarshallAscii()),
            0x2: ('group_id', MarshallInt()),
            0x3: ('icon', MarshallInt()),
            0x4: ('title', MarshallString()),
            0x5: ('url', MarshallString()),
            0x6: ('username', MarshallString()),
            0x7: ('password', MarshallString()),
            0x8: ('notes', MarshallString()),
            0x9: ('created', MarshallDate()),
            0xa: ('modified', MarshallDate()),
            0xb: ('accessed', MarshallDate()),
            0xc: ('expires', MarshallDate()),
            0xd: ('binary_desc', MarshallString()),
            0xe: ('binary', MarshallPass()),
            0xFFFF: (None, None),
            }

    @property
    def label_format(self):
        return "%(title)s: %(username)s %(password)s"


class HeaderStruct(object):
    """
    The keepass file header.
    
    From the KeePass doc:
    
    Database header:
    
    * [ 4 bytes] DWORD    dwSignature1  = 0x9AA2D903
    * [ 4 bytes] DWORD    dwSignature2  = 0xB54BFB65
    * [ 4 bytes] DWORD    dwFlags
    * [ 4 bytes] DWORD    dwVersion       { Ve.Ve.Mj.Mj:Mn.Mn.Bl.Bl }
    * [16 bytes] BYTE{16} aMasterSeed
    * [16 bytes] BYTE{16} aEncryptionIV
    * [ 4 bytes] DWORD    dwGroups        Number of groups in database
    * [ 4 bytes] DWORD    dwEntries       Number of entries in database
    * [32 bytes] BYTE{32} aContentsHash   SHA-256 hash value of the plain contents
    * [32 bytes] BYTE{32} aMasterSeed2    Used for the dwKeyEncRounds AES
                                          master key transformations
    * [ 4 bytes] DWORD    dwKeyEncRounds  See above; number of transformations
    
    Notes:
    
    * dwFlags is a bitmap, which can include:
      * PWM_FLAG_SHA2     (1) for SHA-2.
      * PWM_FLAG_RIJNDAEL (2) for AES (Rijndael).
      * PWM_FLAG_ARCFOUR  (4) for ARC4.
      * PWM_FLAG_TWOFISH  (8) for Twofish.
    * aMasterSeed is a salt that gets hashed with the transformed user master key
      to form the final database data encryption/decryption key.
      * FinalKey = SHA-256(aMasterSeed, TransformedUserMasterKey)
    * aEncryptionIV is the initialization vector used by AES/Twofish for
      encrypting/decrypting the database data.
    * aContentsHash: "plain contents" refers to the database file, minus the
      database header, decrypted by FinalKey.
      * PlainContents = Decrypt_with_FinalKey(DatabaseFile - DatabaseHeader)
    """
    signature1 = None
    signature2 = None
    flags = None
    version = None
    seed_rand = None
    encryption_iv = None
    ngroups = None
    nentries = None
    contents_hash = None
    seed_key = None
    key_enc_rounds = None
    
    # format = '<L L L L 16s 16s L L 32s 32s L'
    
    format = (
        ('signature1', 4, 'L'),
        ('signature2', 4, 'L'),
        ('flags', 4, 'L'),
        ('version', 4, 'L'),
        ('seed_rand', 16, '16s'),
        ('encryption_iv', 16, '16s'),
        ('ngroups', 4, 'L'),
        ('nentries', 4, 'L'),
        ('contents_hash', 32, '32s'),
        ('seed_key', 32, '32s'),
        ('key_enc_rounds', 4, 'L'),
    )

    length = 124

    SHA2 = 1
    RIJNDAEL = 2
    AES = 2
    ARC_FOUR = 4
    TWO_FISH = 8
    
    encryption_flags = (
        ('SHA2', SHA2),
        ('Rijndael', RIJNDAEL),
        ('AES', AES),
        ('ArcFour', ARC_FOUR),
        ('TwoFish', TWO_FISH),
    )

    def __init__(self, buf=None):
        if buf:
            self.decode(buf)

    def __repr__(self):
        ret = ['Header:']
        for field in self.format:
            # field is a tuple (name, size, type)
            name = field[0]
            ret.append('\t%s %r' % (name, getattr(self, name)))
        return '\n'.join(ret)
    
    def __len__(self):
        """ This will equal 124 for the V1 database. """
        length = 0
        for typ, siz, _ in self.format:
            length += siz
        return length
    
    def encryption_type(self):
        for encflag in self.encryption_flags[1:]:
            if encflag[1] & self.flags:
                return encflag[0]
        return 'Unknown'

    def encode(self):
        """
        Returns binary string representation of this struct.
        
        :returns: Structure encoded as binary string for keepass database.
        :rtype: bytes
        """
        ret = bytearray()
        for name, len, typecode in self.format:
            value = getattr(self, name)
            buf = struct.pack('<' + typecode, value)
            ret.extend(buf)
        return bytes(ret)

    def decode(self, buf):
        """
        Set object attributes from binary string buffer.
        
        :param buf: The binary string representation of this struct from database.
        :type buf: bytes 
        """
        index = 0
        if self.length > len(buf):
            raise exc.ParseError("Insufficient data for reading header.") 
        for (name, nbytes, typecode) in self.format:
            string = buf[index:index + nbytes]
            index += nbytes
            value = struct.unpack('<' + typecode, string)[0]
            setattr(self, name, value)
        if const.DB_SIGNATURE1 != self.signature1 or \
                const.DB_SIGNATURE2 != self.signature2:
            msg = 'Bad signatures: {0} {0}'.format(hex(self.signature1),
                                                   hex(self.signature2))
            raise exc.InvalidDatabase(msg)


