#!/bin/bash
supported_locale_list=$(python3 -c "
import locale
print('\n'.join(value.split('.')[0] for value in locale.locale_alias.values()))
")
list_ts=$(find i18n/ts -maxdepth 1 -type f -name '*.ts')

# If there's a user parameter, create a new locale based on it
if [ -n "$1" ]; then
    list_ts="$list_ts i18n/ts/$1.ts"
fi

for ts in $list_ts; do
	# Check if the locale is valid
	if echo "$supported_locale_list" | grep -q "$(basename "$ts" .ts)"; then
		pylupdate6 GUI/*.ui tr/tr.py --no-obsolete --ts "$ts"
		python3 fix_ts.py "$ts"
	else
		list_invalidts="$list_invalidts $ts"
	fi
done

if [ -n "$list_invalidts" ]; then
	echo
	echo "ERROR: The following locales are invalid, please check:"
	echo "$list_invalidts"
	exit 1
fi
