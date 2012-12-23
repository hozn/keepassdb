"""
Some constants used by the application.
"""

# TODO: Some of these need to move into the keepassdb.db.Database class.

__authors__ = ["Brett Viren <brett.viren@gmail.com>","Hans Lellelid <hans@xmpl.org>"]
__license__ = """
keepassdb is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or at your option) any later version.

keepassdb is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
keepassdb.  If not, see <http://www.gnu.org/licenses/>.
"""


from datetime import datetime

# Special date of '2999-12-28 23:59:59' means entities never expire
NEVER    = datetime(2999, 12, 28, 23, 59, 59)

# XXX: THis may need to get more sophisticated if we support multiple versions.
DB_SIGNATURE1 = 0x9AA2D903
DB_SIGNATURE2 = 0xB54BFB65
DB_SUPPORTED_VERSION = 0x00030002 
DB_SUPPORTED_VERSION_MASK = 0xFFFFFF00

DB_MAX_CONTENT_LEN = 2147483446