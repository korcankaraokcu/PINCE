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

if [ "$(id -u)" = "0" ]; then
	echo "Please do not run this script as root!"
	exit 1
fi

SCRIPTDIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
if [ ! -d "${SCRIPTDIR}/.venv/bin" ]; then
	echo "Please run \"sh install.sh\" first!"
	exit 1
fi
. ${SCRIPTDIR}/.venv/bin/activate

PYTHON="${SCRIPTDIR}/.venv/bin/python3"
PINCE_PY="${SCRIPTDIR}/PINCE.py"

if type pkexec &> /dev/null; then
	# Preserve env vars to keep settings like theme preferences.
	# Pkexec does not support passing all of env via a flag like `-E` so we need to
	# rebuild the env and then pass it through.
	ENV=()
	while IFS= read -r line
	do
		ENV+=("$line")
	done < <(printenv)

	pkexec env "${ENV[@]}" "$PYTHON" "$PINCE_PY"
elif type sudo &> /dev/null; then
	# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons
	# so we need to force PATH preservation with venv activated user's PATH.
	sudo -E --preserve-env=PATH PYTHONDONTWRITEBYTECODE=1 "$PYTHON" "$PINCE_PY"
else
	echo "No supported privilege escalation utility found. Please run this as root manually."
	exit 1
fi
