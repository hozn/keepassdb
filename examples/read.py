"""
A simple example illustragint parsing the database and dumping out a dict hierarchy.
"""
import sys
import optparse
import logging
from pprint import pprint

from keepassdb import LockingDatabase

logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    
    parser = optparse.OptionParser("usage: %prog -d DATABASE")
    parser.add_option('-d', '--database', metavar="DBFILE", help="Path to database file.", default="./example.kdb")
    parser.add_option('-p', '--password', metavar="PASSWORD", help="Password for database.", default="test")
    (opts,args) = parser.parse_args(sys.argv)
    
    with LockingDatabase(opts.database, password=opts.password) as db:
        pprint(db.to_dict(hierarchy=True, show_passwords=True))
