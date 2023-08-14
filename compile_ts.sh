#!/bin/bash
file_supportlocale='/usr/share/i18n/SUPPORTED'
list_ts=$(find i18n/ts -maxdepth 1 -type f -name '*.ts')

# If there's a user parameter, create a new locale based on it
if [ -n "$1" ]; then
    list_ts="$list_ts i18n/ts/$1.ts"
fi

if [ -e "$file_supportlocale" ]; then
	for ts in $list_ts; do
		# Check if the locale is valid
		if grep -E "^$(basename "$ts" .ts)(.)?.*\s.*" "$file_supportlocale" > /dev/null 2>&1; then
			pylupdate6 GUI/*.ui tr/tr.py --no-obsolete --ts "$ts"
			python3 fix_ts.py "$ts"
		else
			list_invalidts="$list_invalidts $ts"
		fi
	done
else
	echo "file $file_supportlocale not exist, aborting"
	exit 2
fi

if [ -n "$list_invalidts" ]; then
	echo
	echo "ERROR: The following locales are invalid, please check:"
	echo "$list_invalidts"
	exit 1
fi
