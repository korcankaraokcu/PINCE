#!/bin/bash
file_supportlocale='/usr/share/i18n/SUPPORTED'
list_ts=$(find i18n/ts -maxdepth 1 -type f -name '*.ts')

if [ -e "$file_supportlocale" ]; then
	for ts in $list_ts; do
		# Check if the locale is valid
		if grep -E "^$(basename "$ts" .ts)(.)?.*\s.*" "$file_supportlocale" > /dev/null 2>&1; then
			# Remove empty file to prevent error
			# "invalid translation file: no element found: line 1, column 0"
			[ -s "$ts" ] || rm "$ts"
			pylupdate6 GUI/*.ui tr/tr.py --no-obsolete --ts "$ts"
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
