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

cd libPINCE
mkdir -p gdb_pince
cd gdb_pince

# clean the directory if another installation happened
rm -rf gdb-8.3.1

if [ ! -e gdb-8.3.1.tar.gz ] ; then
    wget "http://ftp.gnu.org/gnu/gdb/gdb-8.3.1.tar.gz"
fi
tar -zxvf gdb-8.3.1.tar.gz
cd gdb-8.3.1
echo "-------------------------------------------------------------------------"
echo "DISCLAIMER"
echo "-------------------------------------------------------------------------"
echo "If you're not on debian or a similar distro with the 'apt' package manager the follow will not work if you don't have gcc and g++ installed"
echo "Please install them manually for this to work, this issue will be addressed at a later date"
command -v gcc g++ # extremely lazy fix for other distros, if gcc&g++ is available it will work, if not it won't
if [ $? -gt 0 ]; then
    # Dependencies required for compiling GDB
    sudo apt-get install python3-dev
    sudo apt-get install gcc g++
    if [ $? -gt 0 ]; then
        sudo apt-get install software-properties-common
        sudo add-apt-repository ppa:ubuntu-toolchain-r/test
        sudo apt-get update
        sudo apt-get install gcc g++
        if [ $? -gt 0 ]; then
            echo "Failed to install gcc or g++, aborting..."
            exit 1
        fi
    fi
fi
CC=gcc CXX=g++ ./configure --prefix="$(pwd)" --with-python=python3 && make -j $(grep -m 1 "cpu cores" /proc/cpuinfo | cut -d: -f 2 | xargs) MAKEINFO=true && sudo make -C gdb install
if [ ! -e bin/gdb ] ; then
    echo "Failed to install GDB, restart the installation process"
    exit 1
fi

# In case of python part of gdb installation fails
sudo cp -R gdb/data-directory/* share/gdb/
