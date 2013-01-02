import os.path
import sys

if sys.version_info < (2, 7):
    try:
        from unittest2 import TestCase
    except ImportError:
        raise Exception("Need unittest2 for running tests under python 2.6")
else:
    from unittest import TestCase

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources')


class TestBase(TestCase):
    
    def setUp(self):
        super(TestBase, self).setUp()
        
    def tearDown(self):
        super(TestBase, self).tearDown()
        
    def get_group_by_name(self, db, name):
        """ Returns first group in database that matches specified name. """
        for g in db.groups:
            if g.title == name:
                return g
        else:
            raise Exception("Group not found: {0}".format(name))
    
    def get_entry_by_name(self, db, name):
        """ Return first entry in database that matches specified name. """
        for e in db.entries:
            if e.title == name:
                return e
        else:
            raise Exception("Entry not found: {0}".format(name))