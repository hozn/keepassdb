"""
A simple example illustragint parsing the database and dumping out a dict hierarchy.
"""
import logging
from pprint import pprint

from keepassdb import LockingDatabase

logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    
    with LockingDatabase('./example.kdb', password='test') as db:
        pprint(db.to_dict(hierarchy=True, show_passwords=True))
