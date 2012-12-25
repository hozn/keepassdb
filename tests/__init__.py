import os.path
import unittest2

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), 'resources')


class TestBase(unittest2.TestCase):
    
    def setUp(self):
        super(TestBase, self).setUp()
        
    def tearDown(self):
        super(TestBase, self).tearDown()
        
    def get_group_by_name(self, db, name):
        """ Returns first group in database that matches specified name. """
        for g in db.groups:
            if g.title == name:
                return g
        return None # Just to be explicit