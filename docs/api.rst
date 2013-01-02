.. _api:

API
***

Main Interaction
================

This part of the documentation covers the primary API for interacting with the
keepass database. 

Database
--------
	
.. automodule:: keepassdb.db
   :synopsis: The database classes provide the primary API to the db structure.
   :members: Database, LockingDatabase

Model
-----

.. automodule:: keepassdb.model
   :synopsis: The entity objects that form the structure of the database.
   :members:

Export
------

The export package contains classes for exporting the database.

.. automodule:: keepassdb.export.xml
   :synopsis: Exporter for the KeePassX XML format.
   :members:

Errors
------

The exception classes raised by the library.

.. automodule:: keepassdb.exc
   :synopsis: The exception classes raised by the application.
   :members:
	
Under-the-Hood
==============

This part of the documentation describes the under-the-hood of the database
parsing and serialization code.

Parsing
-------
      
.. automodule:: keepassdb.structs
   :synopsis: Under-the-hood database parsing and encoding.
   :members: