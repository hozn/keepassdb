# -*- coding: utf-8 -*-
import os.path
import re
import warnings

try:
    from setuptools import setup, find_packages
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

version = '0.1'

news = os.path.join(os.path.dirname(__file__), 'docs', 'news.rst')
news = open(news).read()
parts = re.split(r'([0-9\.]+)\s*\n\r?-+\n\r?', news)
found_news = ''
for i in range(len(parts)-1):
    if parts[i] == version:
        found_news = parts[i+i]
        break
if not found_news:
    warnings.warn('No news for this version found.')

long_description = """
keepassdb is a Python library that provides functionality for reading and writing
KeePass 1.x (and KeePassX) password databases.

This library brings together work by multiple authors, including:
 - Karsten-Kai König <kkoenig@posteo.de>
 - Brett Viren <brett.viren@gmail.com>
 - Wakayama Shirou <shirou.faw@gmail.com>
"""

if found_news:
    title = 'Changes in %s' % version
    long_description += "\n%s\n%s\n" % (title, '-'*len(title))
    long_description += found_news 

setup( 
    name = "keepassdb", 
    version = version, 
    author = "Hans Lellelid", 
    author_email = "hans@xmpl.org",
    url = "http://github.com/hozn/keepassdb",
    license = "GPLv3",
    description = "Python library for reading and writing KeePass 1.x databases.",
    long_description = long_description,
    packages = find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=['pycrypto>=2.6,<3.0dev'],
    tests_require = ['nose', 'unittest2', 'freezegun'],
    test_suite = 'nose.collector',
    classifiers=[
       'Development Status :: 3 - Alpha',
       'License :: OSI Approved :: GNU General Public License (GPL)',
       'Intended Audience :: Developers',
       'Operating System :: OS Independent',
       'Programming Language :: Python :: 2.6',
       'Programming Language :: Python :: 2.7',
       'Topic :: Security :: Cryptography',
       'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
