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
   :members:

Model
-----

.. automodule:: keepassdb.model
    :synopsis: The entity objects that form the structure of the database.
	:members:

Errors
------

The exception classes raised by the library.

.. module:: keepassdb.exc
   :synopsis:The exception classes raised by the application.
   
.. automodule:: keepassdb.exc
	:members:
	
Under-the-Hood
==============

This part of the documentation describes the under-the-hood of the database
parsing and serialization code.

Parsing
-------

.. module:: keepassdb.structs
   :synopsis: Under-the-hood database parsing and encoding.
      
.. automodule:: keepassdb.structs
   :members: