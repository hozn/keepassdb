"""
Some constants for the database.
"""

from datetime import datetime

# Special date of '2999-12-28 23:59:59' means entities never expire
NEVER = datetime(2999, 12, 28, 23, 59, 59)

# XXX: THis may need to get more sophisticated if we support multiple versions.
DB_SIGNATURE1 = 0x9AA2D903
DB_SIGNATURE2 = 0xB54BFB65
DB_SUPPORTED_VERSION = 0x00030002 
DB_SUPPORTED_VERSION_MASK = 0xFFFFFF00

DB_MAX_CONTENT_LEN = 2147483446