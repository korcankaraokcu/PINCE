#!/bin/bash
: '
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

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
'

if [ ! -d ".venv/PINCE" ]; then
	echo "Please run \"sh install_pince.sh\" first!"
	exit 1
fi
. .venv/PINCE/bin/activate

# Change this bullcrap when polkit is implemented
OS=$(lsb_release -si)
# Get rid of gksudo when Debian 8 support drops or polkit gets implemented
if [ $OS = "Debian" ] && [ -x "$(command -v gksudo)" ]; then
  gksudo env PYTHONDONTWRITEBYTECODE=1 python3 PINCE.py
else
  # Preserve env vars to keep settings like theme preferences
  sudo -E PYTHONDONTWRITEBYTECODE=1 python3 PINCE.py
fi
