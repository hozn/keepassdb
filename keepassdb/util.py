import struct
from datetime import datetime
import hashlib

from Crypto.Cipher import AES
from Crypto.Hash import SHA256

def derive_key(seed_key, seed_rand, rounds, password=None, keyfile=None):
    """
    Derives the correct (final) master key from the password and/or keyfile and
    sepcified transform seed & num rounds.
    """
    if password == '': password = None
    if keyfile == '': keyfile = None
    if password is None and keyfile is None:
        raise ValueError("Password and/or keyfile is required.")
        
    if password is None:
        masterkey = key_from_keyfile(keyfile)
    elif password and keyfile:
        passwordkey = key_from_password(password)
        filekey = key_from_keyfile(keyfile)
        sha = SHA256.new()
        sha.update(passwordkey + filekey)
        masterkey = sha.digest()
    else:
        masterkey = key_from_password(password)

    # Create the key that is needed to...
    final_key = transform_key(masterkey, seed_key=seed_key, seed_rand=seed_rand, rounds=rounds)
    
    return final_key
    
def key_from_keyfile(keyfile):
    """
    This method reads in the bytes in the keyfile and returns the
    SHA256 as the key.
    """
    if hasattr(keyfile, 'read'):
        buf = keyfile.read()
    else:
        # Assume it is a filename and open it to read contents.
        with open(keyfile, 'rb') as fp:
            buf = fp.read()
            
    sha = SHA256.new()
    if len(buf) == 33:
        sha.update(buf)
        return sha.digest()
    elif len(buf) == 65:
        sha.update(struct.unpack('<65s', buf)[0].decode())
        return sha.digest()
    else:
        # This chunked updating of the sha is probably not really necessary
        while buf:
            if len(buf) <= 2049:
                sha.update(buf)
                buf = ''
            else:
                sha.update(buf[:2048])
                buf = buf[2048:]
        return sha.digest()
    
def key_from_password(password):
    """This method just hashes self.password."""
    if isinstance(password, unicode):
        password = password.encode('utf-8')
    if not isinstance(password, str):
        raise TypeError("password must be byte string")
    
    sha = SHA256.new()
    sha.update(password)
    return sha.digest()


def transform_key(startkey, seed_key, seed_rand, rounds):
    """
    This method creates the key to decrypt the database.
    """
    masterkey = startkey
    aes = AES.new(seed_key, AES.MODE_ECB)

    # Encrypt the created hash <rounds> times
    for _i in range(rounds):
        masterkey = aes.encrypt(masterkey)

    # Finally, hash it again...
    masterkey = hashlib.sha256(masterkey).digest()
    # ...and hash the result together with the randomseed
    return hashlib.sha256(seed_rand + masterkey).digest()    

def decrypt_aes_cbc(ciphertext, key, iv):
    """
    This method decrypts contents and strips padding.
    
    :rtype: str
    """
    if not isinstance(ciphertext, str):
        raise TypeError("content to decrypt must by bytes.")
    
    # Just decrypt the content with the created key
    aes = AES.new(key, AES.MODE_CBC, iv)
    decrypted_content = aes.decrypt(ciphertext)
    padding = ord(decrypted_content[-1])
    decrypted_content = decrypted_content[:len(decrypted_content) - padding]
    return decrypted_content

def encrypt_aes_cbc(cleartext, key, iv):
    """
    This method encrypts the content.
    
    :rtype: str
    """
    if isinstance(cleartext, unicode):
        cleartext = cleartext.encode('utf8')
    elif isinstance(cleartext, bytearray):
        cleartext = str(cleartext)
    if not isinstance(cleartext, str):
        raise TypeError("content to encrypt must by bytes.")
    
    aes = AES.new(key, AES.MODE_CBC, iv)
    padding = AES.block_size - (len(cleartext) % AES.block_size)
    cleartext += chr(padding) * padding
    return aes.encrypt(cleartext)

def now():
    """
    Save some typing by providing a datetime.now() object w/o the microsecond precision.
    """
    return datetime.now().replace(microsecond=0)
    