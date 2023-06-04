#!/bin/bash
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

# This script installs a specific gdb version locally, the default installation script doesn't need this anymore, you can use it as a fallback if system gdb is being problematic
# After installing a local gdb, you must specify its binary location via the Settings->Debug

GDB_VERSION="gdb-11.2"

if [ -z "$NUM_MAKE_JOBS" ]; then
    NUM_MAKE_JOBS=$(lscpu -p=core | uniq | awk '!/#/' | wc -l)
    MAX_NUM_MAKE_JOBS=8
    if [ "$NUM_MAKE_JOBS" -gt "$MAX_NUM_MAKE_JOBS" ]; then # set an upper limit to prevent Out-Of-Memory
        NUM_MAKE_JOBS=$MAX_NUM_MAKE_JOBS
    fi
    if ! echo "$NUM_MAKE_JOBS" | grep -Eq '^[0-9]+$'; then # fallback
        NUM_MAKE_JOBS=$MAX_NUM_MAKE_JOBS
    fi
fi

mkdir -p gdb_pince
cd gdb_pince || exit

# clean the directory if another installation happened
rm -rf $GDB_VERSION

if [ ! -e ${GDB_VERSION}.tar.gz ] ; then
    wget "http://ftp.gnu.org/gnu/gdb/${GDB_VERSION}.tar.gz"
fi
tar -zxvf ${GDB_VERSION}.tar.gz
cd $GDB_VERSION || exit
echo "-------------------------------------------------------------------------"
echo "DISCLAIMER"
echo "-------------------------------------------------------------------------"
echo "If you're not on debian or a similar distro with the 'apt' package manager the follow will not work if you don't have gcc and g++ installed"
echo "Please install them manually for this to work, this issue will be addressed at a later date"

sudo apt-get install python3-dev libgmp3-dev

CC=gcc CXX=g++ ./configure --prefix="$(pwd)" --with-python=python3 && make -j"$NUM_MAKE_JOBS" MAKEINFO=true && sudo make -C gdb install

if [ ! -e bin/gdb ] ; then
    echo "Failed to install GDB, restart the installation process"
    exit 1
fi

# In case of python part of gdb installation fails
sudo cp -R gdb/data-directory/* share/gdb/
