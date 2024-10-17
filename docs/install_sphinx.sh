#!/bin/bash
venv_activator="../.venv/PINCE/bin/activate"

if [ -f "$venv_activator" ]; then
	. "$venv_activator"
else
  echo "ERROR: Virtual environment not found, please use install.sh to install PINCE first"
  exit
fi

pip install sphinx
pip install sphinx-autodoc-typehints
