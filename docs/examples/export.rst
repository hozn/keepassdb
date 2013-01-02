.. _exporting:

Exporting
*********

Exporting to Dict
=================

There are convenience methods to export the contents of the tree as a python dictionary.  This can be
useful for just viewing the contents::

    from pprint import pprint
    db = Database('./example.kdb', password='test')
    d = db.to_dict(hide_passwords=True)
    pprint(d)
    
... Or perhaps exporting the database to other serialization formats such as YAML or JSON::

    import json
    db = Database('./example.kdb', password='test')
    d = db.to_dict(hide_passwords=False)
    data = json.dumps(d)


Exporting to XML
================

**keepassdb** has experimental support for exporting to the KeePassX XML format. ::

    from keepassdb.export.xml import XmlExporter
    db = Database('./example.kdb', password='test') 
    exporter = XmlExporter()
    output = exporter.export(db)
    
See the :module:`keepassdb.export.xml` module for more details.