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

function check_apply_venv {
	if [ ! -d ".venv/PINCE" ]; then
		echo "Please run \"sh install_pince.sh\" first!"
		exit 1
	fi
	. .venv/PINCE/bin/activate
}

function start {
	# Preserve env vars to keep settings like theme preferences.
	# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons
	# so we need to force PATH preservation with venv activated user's PATH.
	sudo -E --preserve-env=PATH PYTHONDONTWRITEBYTECODE=1 python3 PINCE.py
}

if [ "$(id -u)" = "0" ]; then
	echo "Please do not run this script as root!"
	exit 1
fi

[[ -z $USE_SYSTEM_PYTHON ]] && check_apply_venv

# If exit code not 0, apply venv and try again
start || (check_apply_venv && start)
