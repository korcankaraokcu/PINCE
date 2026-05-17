# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 brkzlr <brksys@icloud.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import collections, os
from . import utils, typedefs
from .libmemscan.memscan import Libmemscan, MatchType, DataType

memscan = Libmemscan(os.path.join(utils.get_libpince_directory(), "libmemscan", "libmemscan.so"))

# Used in set_data_type function of memscan
scan_index_to_memscan_dict = collections.OrderedDict(
    [
        (typedefs.SCAN_INDEX.INT_ANY, DataType.ANYINTEGER),
        (typedefs.SCAN_INDEX.INT8, DataType.INTEGER8),
        (typedefs.SCAN_INDEX.INT16, DataType.INTEGER16),
        (typedefs.SCAN_INDEX.INT32, DataType.INTEGER32),
        (typedefs.SCAN_INDEX.INT64, DataType.INTEGER64),
        (typedefs.SCAN_INDEX.FLOAT_ANY, DataType.ANYFLOAT),
        (typedefs.SCAN_INDEX.FLOAT32, DataType.FLOAT32),
        (typedefs.SCAN_INDEX.FLOAT64, DataType.FLOAT64),
        (typedefs.SCAN_INDEX.ANY, DataType.ANYNUMBER),
        (typedefs.SCAN_INDEX.STRING, DataType.STRING),
        (typedefs.SCAN_INDEX.AOB, DataType.BYTEARRAY),
    ]
)

scan_type_to_memscan_dict = collections.OrderedDict(
    [
        (typedefs.SCAN_TYPE.EXACT, MatchType.MATCHEQUALTO),
        (typedefs.SCAN_TYPE.NOT, MatchType.MATCHNOTEQUALTO),
        (typedefs.SCAN_TYPE.INCREASED, MatchType.MATCHINCREASED),
        (typedefs.SCAN_TYPE.INCREASED_BY, MatchType.MATCHINCREASEDBY),
        (typedefs.SCAN_TYPE.DECREASED, MatchType.MATCHDECREASED),
        (typedefs.SCAN_TYPE.DECREASED_BY, MatchType.MATCHDECREASEDBY),
        (typedefs.SCAN_TYPE.LESS, MatchType.MATCHLESSTHAN),
        (typedefs.SCAN_TYPE.MORE, MatchType.MATCHGREATERTHAN),
        (typedefs.SCAN_TYPE.BETWEEN, MatchType.MATCHRANGE),
        (typedefs.SCAN_TYPE.CHANGED, MatchType.MATCHCHANGED),
        (typedefs.SCAN_TYPE.UNCHANGED, MatchType.MATCHNOTCHANGED),
        (typedefs.SCAN_TYPE.UNKNOWN, MatchType.MATCHANY),
    ]
)
