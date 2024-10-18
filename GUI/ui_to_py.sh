#!/bin/bash
script_dir="$(dirname "$(readlink -f "$0")")"
cd $script_dir
venv_activator="../.venv/PINCE/bin/activate"

if [ -f "$venv_activator" ]; then
	. "$venv_activator"
else
    echo "ERROR: Virtual environment not found, please use install.sh to install PINCE first"
    exit
fi

for uifile in *.ui Widgets/*/Form/*.ui
do
    uidir=$(dirname "$uifile")
    uiname=$(basename "$uifile")
    outfile="${uiname%.ui}.py"
    (cd "$uidir" && pyuic6 "$uiname" -o "$outfile")
done
