for uifile in *.ui
do
    outfile=$(echo $uifile | sed 's/\.ui/\.py/g')
    pyuic6 $uifile -o $outfile
done