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

install_gdb () {
if ! sudo sh install_gdb.sh ; then
    echo "Failed to install PINCE"
    exit 1
fi
}

OS_NAME="Debian"
PKG_MGR="apt-get"
PKG_NAMES_ALL="python3-setuptools python3-pip"
PKG_NAMES_DEBIAN="$PKG_NAMES_ALL python3-pyqt5"
PKG_NAMES_SUSE="$PKG_NAMES_ALL python3-qt5"
PKG_NAMES="$PKG_NAMES_DEBIAN"
PKG_NAMES_PIP="psutil pexpect distorm3 pygdbmi"

LSB_RELEASE="`which lsb_release`"
if [ -n "$LSB_RELEASE" ] ; then
    OS_NAME="`$LSB_RELEASE -d -s`"
fi

case "$OS_NAME" in
*SUSE*)
    PKG_MGR="zypper"
    PKG_NAMES="$PKG_NAMES_SUSE"
    ;;
esac

sudo $PKG_MGR install $PKG_NAMES
sudo pip3 install $PKG_NAMES_PIP

if [ -e libPINCE/gdb_pince/gdb-8.0/bin/gdb ] ; then
    echo "GDB has been already compiled&installed, recompile&install? (y/n)"
    read answer
    if echo "$answer" | grep -iq "^[Yy]" ;then
        install_gdb
    fi
else
    install_gdb
fi

echo "PINCE has been installed successfully!"
echo "Now, just run 'sh PINCE.sh' from terminal"
