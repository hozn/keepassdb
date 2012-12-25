"""
Unit tests for group-related operations.
"""
import os.path
from StringIO import StringIO

from freezegun import freeze_time

from keepassdb import Database, model, exc

from tests import TestBase, RESOURCES_DIR

class GroupTest(TestBase):
        
    def test_move(self):
        """ Test moving group to another level. """
        db = Database(os.path.join(RESOURCES_DIR, 'example.kdb'), password='test')
        
        group = self.get_group_by_name(db, 'B1')
        target = self.get_group_by_name(db, 'A1')
        group.move(target) 
        
        self.assertEquals(target, group.parent)
        
        a1 = db.root.children[0].children[0]
        #             Internet     A1
        
        self.assertEquals(['A2', 'B1'], [g.title for g in a1.children])
        