.. _examples:

Basic Usage
***********

Opening and Saving Databases
============================

The basics of opening a database is very simple::
    
    from keepassdb import Database
    db = Database('./example.kdb', password='test')
        
The database may be specified by file or stream. ::

    stream = StringIO()
    # Populate stream with bytes from somewhere. A database?
    stream.seek(0) # Rewind the stream!
    
    db = Database(stream, password='test')

If you are opening a database in an environment where other applications may also try to open 
the database, you should use the :class:`keepassdb.db.LockingDatabase` class which will create a .lock file.

Typically the lock file is created automatically when the database is parsed or the filepath changes (e.g.
if a new path is specified to the :meth:`keepassdb.db.Database.save` method). ::
  
    from keepassdb import LockingDatabase
    db = LockingDatabase('./example.kdb', password='test')
    # The lock is acquired automatically after the db load succeeds.
    db.save()
    db.close() # Automatically releases the lock.
    
More explicit control is also possible. ::
    
    db = LockingDatabase('./example.kdb', password='test')
    try:
        # Do database things.
        db.save()
    finally:
        db.release_lock()
        
You may wish to use the context manager which provides some syntactic simplification.::
 
    with LockingDatabase('./example.kdb', password='test') as db:
        # Do stuff with the database here.
        db.save()
    
Reading Database Contents
=========================

The database is stored in a hierarchy of groups with entry members which is rooted at 
the aptly-named `root` attribute (:class:`keepassdb.model.RootGroup`) of the 
:class:`keepassdb.db.Database` instance.  The root group is not stored in the database; there 
is guaranteed to be at least one top-level (child of root) group in a database, since database 
entries must be associated with a group.

Iterating over a hierarchy lends itself to recursion; here is a simple example enumerate all 
entries::

    db = Database('./example.kdb', password='test')
    def print_group(group, level=0):
        indent = " " * level
        print '%s%s' % (indent, group.title)
        for entry in group.entries:
              print '%s -%s' % (indent, entry.title)
        for child in group.children:
            print_group(child, level+1)
    
    print_group(db.root)
    
Of course, if you just want to iterate over the groups or entries in a flat list, you can access
the `groups` attributes directly::

    db = Database('./example.kdb', password='test')
    for g in db.groups:
        print g.title
        for e in g.entries:
            print " -%s" % e.title

... Or iterate over all the entries in a flat list with the `entries` attribute::

    db = Database('./example.kdb', password='test')
    for e in db.entries:
        print '%s: %s' % (e.title, e.password)

You can use the `to_dict` methods to quickly view the contents of the database. ::

    from pprint import pprint
    db = Database('./example.kdb', password='test')
    d = db.to_dict(hide_passwords=True)
    pprint(d)

(See :ref:`exporting` for more examples on database eporting.)    
    
Creating Database Contents
==========================

New groups should be created using the :meth:`keepassdb.db.Database.create_group` method, since this will ensure
that the group is bound to the database instance. Similarly entries should be created using the 
:meth:`keepassdb.model.Group.create_entry` method.  For example::

    db = Database()
    group = db.create_group(title=u"My First Group", icon=1)
    group.create_entry(title="Entry 1", url="http://example.com",
                       username=u"myuser", password="test")
    db.save("./example.kdb", password="test")

There is a shortcut (though admittedly it doesn't save much typing) to create the conventional 'Internet' group on an
empty database::

    db = Database()
    db.create_default_group()
    db.save('empty.kdb', password='test')

The filename (and password/keyfile) may also be specified at database initialization (this is most useful with a 
:class:`keepassdb.db.LockingDatabase` since the .lock file will be created automatically), but the 
`new` parameter must then also be specified (so that the constructor does not attempt to load the database)::

    with LockingDatabase('./example.kdb', password='test', new=True) as db:
    	# Add stuff to the database.
    	db.save()
   
   