"""
Unit tests for group-related operations.
"""
import os.path
#from xml.dom import minidom
from xml.etree import ElementTree as ET

from freezegun import freeze_time

from keepassdb import Database, model, exc
from keepassdb.export.xml import XmlExporter

from tests import TestBase, RESOURCES_DIR

class XmlExporterTest(TestBase):
        
    def test_export(self):
        """ Really basic XML-export smoke test. """
        # This is a pretty half-hearted smoke test currently.
        db = Database(os.path.join(RESOURCES_DIR, 'example.kdb'), password='test')
 
        exporter = XmlExporter()
        output = exporter.export(db)
        
        tree = ET.fromstring(output)
        entries = tree.findall('.//entry')
        
        s1 = set([e.find('./title').text for e in entries])
        s2 = set([e.title for e in db.entries if e.title != 'Meta-Info'])
        self.assertEquals(s2, s1)
        