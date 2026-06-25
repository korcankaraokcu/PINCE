#!/bin/sh
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

SCRIPTDIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
if [ ! -d "${SCRIPTDIR}/.venv/bin" ]; then
	echo "Please run \"sh install.sh\" first!"
	exit 1
fi
. "${SCRIPTDIR}/.venv/bin/activate"

PYTHON="${SCRIPTDIR}/.venv/bin/python3"
PINCE_PY="${SCRIPTDIR}/PINCE.py"

if [ -n "$1" ]; then
    PCT_DIR=$(cd -P -- "$(dirname -- "$1")" && pwd -P) || exit 1
    PCT_FILE="$PCT_DIR/$(basename -- "$1")"
fi

if [ "$(id -u)" = "0" ]; then
	"$PYTHON" "$PINCE_PY" "$PCT_FILE"
else
	if command -v pkexec > /dev/null 2>&1; then
		# Preserve env vars to keep settings like theme preferences.
		# Pkexec does not support passing all of env via a flag like `-E` so we need to
		# rebuild the env and then pass it through.
		set --
		while IFS= read -r line
		do
			set -- "$@" "$line"
		done <<EOF
$(printenv)
EOF
		set -- "$@" "PINCE_PARENT_PID=$$"

		pkexec_err=$(pkexec --disable-internal-agent env "$@" /bin/sh -c 'p=$PINCE_PARENT_PID; unset PINCE_PARENT_PID; exec "$@" >"/proc/$p/fd/1" 2>"/proc/$p/fd/2"' sh "$PYTHON" "$PINCE_PY" "$PCT_FILE" 2>&1)
		pkexec_status=$?

		case "$pkexec_status:$pkexec_err" in
		127:*"No authentication agent found"*) ;;
		*)
			if [ -n "$pkexec_err" ]; then
				printf '%s\n' "$pkexec_err" >&2
			fi
			exit "$pkexec_status"
			;;
		esac
	fi

	if command -v sudo > /dev/null 2>&1; then
		# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons
		# so we need to force PATH preservation with venv activated user's PATH.
		sudo -E --preserve-env=PATH "$PYTHON" "$PINCE_PY" "$PCT_FILE"
	else
		echo "No supported privilege escalation utility found. Please run this as root manually."
		echo "Don't forget to preserve normal user environment variables for proper functionality."
		exit 1
	fi
fi
