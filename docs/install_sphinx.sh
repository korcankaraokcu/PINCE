#!/bin/bash
script_dir="$(dirname "$(readlink -f "$0")")"
cd $script_dir
venv_activator="../.venv/bin/activate"

if [ -f "$venv_activator" ]; then
	. "$venv_activator"
else
    echo "ERROR: Virtual environment not found, please use install.sh to install PINCE first"
    exit
fi

pip install sphinx
pip install sphinx-autodoc-typehints
