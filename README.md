# keepassdb

**IMPORTANT**
This library is alpha-quality/stability. Tread carefully!

keepassdb is a python module to provide an API to read and write KeePass 1.x / KeePassX 
database files.

This project began as a desire to merge together several python keepass projects that provided 
strengths in different areas (but none of which worked fully as a standalone solution).

Specifically this project owes its roots to: 
* [kppy](https://github.com/raymontag/kppy) by Karsten-Kai König <kkoenig@posteo.de>,
* [python-keepass](https://github.com/brettviren/python-keepass) by Brett Viren <brett.viren@gmail.com>, and
* [kptool](https://github.com/shirou/kptool/) by Wakayama Shirou <shirou.faw@gmail.com>

This project is currently for Python 2.x only.

This software is licensed under the GPLv3 (or later), in accordance with the upstream libraries and 
the KeePass project itself.

* Homepage: https://github.com/hozn/keepassdb
* Project Documentation: http://packages.python.org/keepassdb/
 
## Dependencies
 
* Python 2.6+.  (This does not currently work with Python 3.)
* Setuptools/Distribute
* PyCrypto

## Limitations

* Supports only KeePass V1 databases.  
* Currently supports only AES encryption.
* Does not fully support the tree state MetaInfo entries that may be added by other programs.
* Does not work (yet) on Python 3.x

## Installation

Via easy_install/distribute:

    easy_install keepassdb

Or more traditionally:

    python setup.py install
    
## Basic Usage

### Reading	
```python

from keepassdb import Database
db = Database('./test.kdb', password='test'):
# Display a flat list of all groups and the entries in each group.
for group in db.groups:
	print group.name
	for entry in group.entries:
		print "\t-%s" % entry.name
```

### Writing
```python

# A locking database will create the .lock file that other KeePass programs expect.
from keepassdb import LockingDatabase
with LockingDatabase('./new.kdb', new=True) as db:
    group = db.create_group(title='A new group')
    entry = group.create_entry(title='Entry1', username='root', password='test')
    # etc.
    db.save(password='test')
```
