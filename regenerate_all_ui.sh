#!/bin/bash

cd -P "$( dirname "${BASH_SOURCE[0]}" )"
cd /pince/GUI

for file in `ls -1 *.ui`
do
	pyuic5 $file -o ${file%\.*}.py 
done
