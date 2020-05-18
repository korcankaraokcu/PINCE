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

# this file cannot (or any file) be named `install.sh` since libtoolize(automake) will not work properly if it does
# it will create the necessary files in PINCEs directory instead of scanmems, which will result in having to run `sh autogen.sh`
# twice, see this link https://github.com/protocolbuffers/protobuf/issues/149#issuecomment-473092810


CURRENT_USER="$(who mom likes | awk '{print $1}')"

install_gdb () {
if ! sudo sh install_gdb.sh ; then
    echo "Failed to install PINCE"
    exit 1
fi
}

# assumes you're in scanmem directory
compile_scanmem() {
    sh autogen.sh
    ./configure --prefix=/usr 
    make -j libscanmem.la
    chown -R "${CURRENT_USER}":"${CURRENT_USER}" . # give permissions for normal user to change file
}

install_scanmem() {
    echo "Downloading scanmem"
    git submodule update --init --recursive
    
    if [ ! -d "libPINCE/libscanmem" ]; then
        mkdir libPINCE/libscanmem
        chown -R "${CURRENT_USER}":"${CURRENT_USER}" libPINCE/libscanmem
    fi
    (
        echo "Entering scanmem"
        cd scanmem || exit
        if [ -d "./.libs" ]; then 
            echo "Recompile scanmem? [y/n]"
            read -r answer
            if echo "$answer" | grep -iq "^[Yy]"; then
                compile_scanmem
            fi
        else
            compile_scanmem
        fi
        cp --preserve .libs/libscanmem.so ../libPINCE/libscanmem/libscanmem.so
        cp --preserve gui/scanmem.py ../libPINCE/libscanmem
        cp --preserve gui/misc.py ../libPINCE/libscanmem
        echo "Exitting scanmem"
    )
    # required, since it will throw an import error if it's just `import misc`
    # some odd things python does with packages or something, I'm not a python dev
    # I don't know why it does it, I just know it fixes the error
    sed -i 's/import misc/from \. import misc/g' libPINCE/libscanmem/scanmem.py
}

OS_NAME="Debian"
PKG_MGR="apt-get"
INSTALL_COMMAND="install"

PKG_NAMES_ALL="python3-setuptools python3-pip"
PKG_NAMES_DEBIAN="$PKG_NAMES_ALL python3-pyqt5 autotools-dev libtool libreadline-dev intltool"
PKG_NAMES_SUSE="$PKG_NAMES_ALL python3-qt5"
PKG_NAMES_ARCH="python-pyqt5 python-setuptools autoconf readline intltool" # arch defaults to py3 now days
PKG_NAMES="$PKG_NAMES_DEBIAN"
PKG_NAMES_PIP="psutil pexpect distorm3 pygdbmi"

LSB_RELEASE="$(command -v lsb_release)"
if [ -n "$LSB_RELEASE" ] ; then
    OS_NAME="$(${LSB_RELEASE} -d -s)"
fi
case "$OS_NAME" in
*SUSE*)
    PKG_MGR="zypper"
    PKG_NAMES="$PKG_NAMES_SUSE"
    ;;
*Arch*)
    PKG_MGR="pacman"
    PKG_NAMES="$PKG_NAMES_ARCH"
    INSTALL_COMMAND="-S"
    ;;
esac

sudo ${PKG_MGR} ${INSTALL_COMMAND} ${PKG_NAMES}
sudo pip3 install ${PKG_NAMES_PIP}

if [ -e libPINCE/gdb_pince/gdb-8.3.1/bin/gdb ] ; then
    echo "GDB has been already compiled&installed, recompile&install? (y/n)"
    read -r answer
    if echo "$answer" | grep -iq "^[Yy]" ;then
        install_gdb
    fi
else
    install_gdb
fi
install_scanmem

echo "PINCE has been installed successfully!"
echo "Now, just run 'sh PINCE.sh' from terminal"
