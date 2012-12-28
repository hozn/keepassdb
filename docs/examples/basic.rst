.. _examples:

Basic Usage
***********

Opening and Saving Databases
============================

The basics of opening a database are very simple:::
    
    from keepassdb import Database
    
	db = Database('./example.kdb', password='test')
	    
The database may be specified by file or stream.::

	stream = StringIO()
	# Populate stream with bytes from somewhere. A database?
	stream.seek(0) # Rewind the stream!
	
	db = Database(stream, password='test')

If you are opening a database in an environment where other applications may also try to open 
the database, you should use the :class:`keepassdb.db.LockingDatabase` class which will create a .lock file.::
  
  	from keepassdb import LockingDatabase
  	
    db = LockingDatabase('./example.kdb', password='test')
    db.acquire_lock()
    try:
        # Do database things.
        db.save()
    finally:
        db.release_lock()
        
You may wish to use the context manager which provides some syntactic simplification.::
 
	with LockingDatabase(opts.database, password=opts.password) as db:
        # Do stuff with the database here.
        db.save()
    
.. danger::
   The locking API is under active development.  There are some intricacies such as when exactly 
   the lock should be acquired (e.g. after database successfully loaded?) and released and how
   to correctly handle things like a new filename being passed to :meth:`keepassdb.db.Database.save` method.  