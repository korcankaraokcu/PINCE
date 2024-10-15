#!/bin/bash
. ../.venv/PINCE/bin/activate

for uifile in *.ui Widgets/*/Form/*.ui
do
    uidir=$(dirname "$uifile")
    uiname=$(basename "$uifile")
    outfile="${uiname%.ui}.py"
    (cd "$uidir" && pyuic6 "$uiname" -o "$outfile")
done
