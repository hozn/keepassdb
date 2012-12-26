"""
Unit tests for group-related operations.
"""
import os.path
from StringIO import StringIO

from freezegun import freeze_time

from keepassdb import Database, model, exc

from tests import TestBase, RESOURCES_DIR

class EntryTest(TestBase):
        
    def test_move(self):
        """ Test moving an entry to a new group. """
        db = Database(os.path.join(RESOURCES_DIR, 'example.kdb'), password='test')
        
        new_parent = self.get_group_by_name(db, 'A1')
        
        entry = self.get_entry_by_name(db, 'B1Entry1')
        orig_parent = entry.group
        
        self.assertEquals('B1', orig_parent.title)
        
        self.assertEquals([u'AEntry2', u'AEntry1', u'AEntry3'], [e.title for e in new_parent.entries])
        
        entry.move(new_parent)
        
        self.assertIs(new_parent, entry.group)
        
        self.assertEquals([u'AEntry2', u'AEntry1', u'AEntry3', u'B1Entry1'], [e.title for e in new_parent.entries])
        
    def test_move_index(self):
        """ Test moving an entry to a new group with index. """
        db = Database(os.path.join(RESOURCES_DIR, 'example.kdb'), password='test')
        
        new_parent = self.get_group_by_name(db, 'A1')
        
        entry = self.get_entry_by_name(db, 'B1Entry1')
        orig_parent = entry.group
        
        self.assertEquals('B1', orig_parent.title)
        
        self.assertEquals([u'AEntry2', u'AEntry1', u'AEntry3'], [e.title for e in new_parent.entries])
        
        entry.move(new_parent, 0)
        
        self.assertIs(new_parent, entry.group)
        
        self.assertEquals([u'B1Entry1', u'AEntry2', u'AEntry1', u'AEntry3'], [e.title for e in new_parent.entries])

    def test_move_within_group(self):
        """ Test moving an entry within the same group. """
        db = Database(os.path.join(RESOURCES_DIR, 'example.kdb'), password='test')
        
        new_parent = self.get_group_by_name(db, 'A1')
        
        entry = self.get_entry_by_name(db, 'AEntry2')
        
        self.assertEquals([u'AEntry2', u'AEntry1', u'AEntry3'], [e.title for e in new_parent.entries])
        
        entry.move(entry.group, 1)
        
        self.assertEquals([u'AEntry1', u'AEntry2', u'AEntry3'], [e.title for e in new_parent.entries])
