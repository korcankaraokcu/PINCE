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
if [ ! -d "${SCRIPTDIR}/.venv/PINCE" ]; then
	echo "Please run \"sh install.sh\" first!"
	exit 1
fi
. ${SCRIPTDIR}/.venv/PINCE/bin/activate
PINCE_PATH="${SCRIPTDIR}/PINCE.py"

export PYTHONDONTWRITEBYTECODE=1

run_with_pkexec() {
	# Preserve env vars to keep settings like theme preferences.
	# Pkexec does not support passing all of env via a flag like `-E` so we need to
	# rebuild the env and then pass it through.
	ENV=(env)
	while IFS='=' read -r key value; do
		CMD+=("$key=$value")
	done < <(env)

	pkexec env "${CMD[@]}" python3 "$PINCE_PATH"
}

run_with_sudo() {
	# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons
	# so we need to force PATH preservation with venv activated user's PATH.
	sudo -E --preserve-env=PATH,PYTHONDONTWRITEBYTECODE python3 "$PINCE_PATH"
}

# Prefer pkexec, fallback to sudo.
if ! run_with_pkexec; then
	run_with_sudo
fi
