"""
A simple example illustrating how to create & save a database.

NOTE: THIS IS BROKEN RIGHT NOW.
"""
import logging
from pprint import pprint

from keepassdb import LockingDatabase

logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
        
    with LockingDatabase('./new.kdb', new=True) as db:
        group = db.create_group(title='A new group')
        entry = group.create_entry(title='Entry1', username='root', password='test')
        # etc.
        # pprint(db.to_dict())
        db.save(password='test')