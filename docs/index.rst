.. keepassdb documentation master file, created by
   sphinx-quickstart on Thu Dec 27 21:23:53 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Documentation for keepassdb 
===========================

Changelog
---------

High-level changes in library by version.

.. toctree::
   :maxdepth: 2

   news

Getting Started
---------------

The package is avialable on PyPI to be installed using easy_install or pip:

.. code-block:: none
   
   shell$ easy_install keepassdb

Using these tools, the PyCrypto 2.6+ dependency will be downloaded and installed automatically from PyPI.

For more traditional installation, you can download and install the package manually:

.. code-block:: none
   
   shell$ tar xvf ~/Downloads/keepassdb-x.x.x.tar.gz
   shell$ cd keepassdb-x.x.x
   shell$ python setup.py install
   
Of course, by itself this package doesn't do much; it's a library.  So it is more likely that you will 
list this package as a dependency in your own `install_requires` directive in `setup.py`.
   
Examples
---------

Example code to get you started reading & writing keepass files.

.. toctree::
   :maxdepth: 2

   examples/basic


API Reference
-------------

In-depth reference guide for developing software with keepassdb.

.. toctree::
   :maxdepth: 2

   api
   

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

