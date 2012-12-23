# -*- coding: utf-8 -*-
"""
This module implements the access to KeePass 1.x-databases.
"""

__authors__ = ["Hans Lellelid <hans@xmpl.org>"]
__copyright__ = "Copyright (C) 2012 Karsten-Kai König <kkoenig@posteo.de>"
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

from keepassdb.db import LockingDatabase, Database