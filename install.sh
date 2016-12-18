#!/bin/bash
: '
Copyright (C) 2016 Korcan Karaokçu <korcankaraokcu@gmail.com>

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

sudo apt-get install python3-setuptools
sudo apt-get install python3-pip
sudo apt-get install python3-pyqt5
sudo pip3 install psutil
sudo pip3 install pexpect

if [ -e libPINCE/gdb_pince/gdb-7.11.1/bin/gdb ] ; then
    echo "GDB has been already compiled&installed, recompile&install? (y/n)"
    read answer
    if echo "$answer" | grep -iq "^[Yy]" ;then
        sudo sh install_gdb.sh
    fi
else
    sudo sh install_gdb.sh
fi

# Creating .gdbinit in $HOME
cd
auto_load_command="set auto-load safe-path /"
if [ ! -e .gdbinit ] ; then
    touch .gdbinit
fi
if grep "$auto_load_command" .gdbinit
then
  echo "auto_load already satisfied"
else
  echo "\n"$auto_load_command >> .gdbinit
fi
echo "PINCE has been installed successfully!"
echo "Now, just run 'sh PINCE.sh' from terminal"