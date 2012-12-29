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
        group = db.create_group(title='Internet')
        group.create_entry(title='Entry1', username='root', password='test', url='')
        group.create_entry(title='Entry2', username='root', password='test', url='http://example.com')
        
        group = db.create_group(title='eMail')
        group.create_entry(title='Entry3', username='root', password='test3', url='')
        
        db.save(password='test')