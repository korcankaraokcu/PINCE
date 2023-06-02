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

if [ "$(id -u)" = "0" ]; then
	echo "Please do not run this script as root!"
	exit 1
fi

CURRENT_USER="$(who mom likes | awk '{print $1}')"

exit_on_error() {
    if [ "$?" -ne 0 ]; then
        echo
        echo "Error occured while installing PINCE, check the output above for more information"
        echo "Installation failed."
        exit 1
    fi
}

# assumes you're in scanmem directory
compile_scanmem() {
    sh autogen.sh || return 1
    ./configure --prefix="$(pwd)" || return 1
    make -j libscanmem.la || return 1
    chown -R "${CURRENT_USER}":"${CURRENT_USER}" . # give permissions for normal user to change file
    return 0
}

install_scanmem() {
    echo "Downloading scanmem"
    git submodule update --init --recursive || return 1

    if [ ! -d "libpince/libscanmem" ]; then
        mkdir libpince/libscanmem
        chown -R "${CURRENT_USER}":"${CURRENT_USER}" libpince/libscanmem
    fi
    (
        echo "Entering scanmem"
        cd scanmem || return 1
        if [ -d "./.libs" ]; then
            echo "Recompile scanmem? [y/n]"
            read -r answer
            if echo "$answer" | grep -iq "^[Yy]"; then
                compile_scanmem || return 1
            fi
        else
            compile_scanmem || return 1
        fi
        cp --preserve .libs/libscanmem.so ../libpince/libscanmem/
        cp --preserve wrappers/scanmem.py ../libpince/libscanmem
        cp --preserve wrappers/misc.py ../libpince/libscanmem
        echo "Exiting scanmem"
    ) || return 1
    # required for relative import, since it will throw an import error if it's just `import misc`
    sed -i 's/import misc/from \. import misc/g' libpince/libscanmem/scanmem.py
    return 0
}

ask_pkg_mgr() {
	echo
	echo "Your distro is not officially supported! Trying to install anyway."
	echo "Please choose your package manager."
	echo "1) APT"
	echo "2) Pacman"
	echo "3) DNF"
	echo "4) Zypper"
	echo "5) None of the above"

	read -r -p "Choose: " OPTION
	OPTION=$(echo $OPTION | tr '[:lower:]' '[:upper:]')

	case $OPTION in
	1|*APT*)
		OS_NAME="Debian"
		;;
	2|*PACMAN*)
		OS_NAME="Arch"
		;;
	3|*DNF*)
		OS_NAME="Fedora"
		;;
	4|*ZYPPER*)
		OS_NAME="SUSE"
		;;
	*)
		return 1
		;;
	esac

	return 0
}

# About xcb packages -> https://github.com/cdgriffith/FastFlix/wiki/Common-questions-and-problems
PKG_NAMES_ALL="python3-pip gdb libtool intltool"
PKG_NAMES_DEBIAN="$PKG_NAMES_ALL libreadline-dev python3-dev python3-venv pkg-config libcairo2-dev libgirepository1.0-dev libxcb-randr0-dev libxcb-xtest0-dev libxcb-xinerama0-dev libxcb-shape0-dev libxcb-xkb-dev libxcb-cursor0"
PKG_NAMES_SUSE="$PKG_NAMES_ALL gcc readline-devel python3-devel typelib-1_0-Gtk-3_0 cairo-devel gobject-introspection-devel make"
PKG_NAMES_FEDORA="$PKG_NAMES_ALL readline-devel python3-devel redhat-lsb cairo-devel gobject-introspection-devel cairo-gobject-devel"
PKG_NAMES_ARCH="python-pip readline intltool gdb lsb-release" # arch defaults to py3 nowadays
PKG_NAMES_PIP="pyqt6 pexpect distorm3 keystone-engine pygdbmi keyboard pygobject"

INSTALL_COMMAND="install"

set_install_vars() {
	case $1 in
	*SUSE*)
		PKG_MGR="zypper"
		PKG_NAMES="$PKG_NAMES_SUSE"
		;;
	*Arch*)
		PKG_MGR="pacman"
		PKG_NAMES="$PKG_NAMES_ARCH"
		INSTALL_COMMAND="-S --needed"
		;;
	*Fedora*)
		PKG_MGR="dnf -y"
		PKG_NAMES="$PKG_NAMES_FEDORA"
		;;
	*Debian*|*Ubuntu*)
		PKG_MGR="apt -y"
		PKG_NAMES="$PKG_NAMES_DEBIAN"
		;;
	*)
		return 1
		;;
	esac

	return 0
}

LSB_RELEASE="$(command -v lsb_release)"
if [ -n "$LSB_RELEASE" ]; then
    OS_NAME="$(${LSB_RELEASE} -d -s)"
else
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_NAME="$NAME"
fi

set_install_vars $OS_NAME

if [ "$?" -ne 0  ]; then
	ask_pkg_mgr
	if [ "$?" -ne 0 ]; then
		echo
		echo "Sorry, your distro is not supported!"
		exit 1
	fi

	set_install_vars $OS_NAME
fi

# shellcheck disable=SC2086
sudo ${PKG_MGR} ${INSTALL_COMMAND} ${PKG_NAMES} || exit_on_error

# Prepare Python virtual environment
if [ ! -d ".venv/PINCE" ]; then
	python3 -m venv .venv/PINCE
fi
. .venv/PINCE/bin/activate

# shellcheck disable=SC2086
pip3 install ${PKG_NAMES_PIP} || exit_on_error

install_scanmem || exit_on_error

echo
echo "PINCE has been installed successfully!"
echo "Now, just run 'sh PINCE.sh' from terminal"
