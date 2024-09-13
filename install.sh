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

if [ "$(id -u)" = "0" ]; then
	echo "Please do not run this script as root!"
	exit 1
fi

SCRIPTDIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd $SCRIPTDIR
if [ ! -d ".git" ]; then
	echo "Error! Could not find \".git\" folder!"
	echo "This can happen if you downloaded the ZIP file instead of cloning through git."
	echo "Please clone the PINCE repository using the \"--recursive\" flag and try again!"
	echo "For more information, please follow the installation instructions on GitHub."
	exit 1
fi

CURRENT_USER="$(whoami)"

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

exit_on_error() {
    if [ "$?" -ne 0 ]; then
        echo
        echo "Error occured while installing PINCE, check the output above for more information"
        echo "Installation failed."
        exit 1
    fi
}

# assumes you're in libscanmem directory
compile_libscanmem() {
    cmake -DCMAKE_BUILD_TYPE=Release . || return 1
    make -j"$NUM_MAKE_JOBS" || return 1
    chown -R "${CURRENT_USER}":"${CURRENT_USER}" . # give permissions for normal user to change file
    return 0
}

install_libscanmem() {
    echo "Downloading libscanmem"
    git submodule update --init --recursive || return 1

    if [ ! -d "libpince/libscanmem" ]; then
        mkdir libpince/libscanmem
        chown -R "${CURRENT_USER}":"${CURRENT_USER}" libpince/libscanmem
    fi
    (
        echo "Entering libscanmem directory"
        cd libscanmem-PINCE || return 1
        if [ -f "./libscanmem.so" ]; then
            echo "Recompile libscanmem? [y/n]"
            read -r answer
            if echo "$answer" | grep -iq "^[Yy]"; then
                make clean
                compile_libscanmem || return 1
            fi
        else
            compile_libscanmem || return 1
        fi
        cp --preserve libscanmem.so ../libpince/libscanmem/
        cp --preserve wrappers/scanmem.py ../libpince/libscanmem
        echo "Exiting libscanmem directory"
    ) || return 1
    return 0
}

install_libptrscan() {
	echo "Downloading libptrscan"

    if [ ! -d "libpince/libptrscan" ]; then
        mkdir libpince/libptrscan
        chown -R "${CURRENT_USER}":"${CURRENT_USER}" libpince/libptrscan
    fi
    (
		cd libpince/libptrscan
		# Source code download as we might be forced to distribute it due to licence
		curl -L -O https://github.com/kekeimiku/PointerSearcher-X/archive/refs/tags/v0.7.4-dylib.tar.gz || return 1
		# Actual .so and py wrapper
		curl -L -o libptrscan.tar.gz https://github.com/kekeimiku/PointerSearcher-X/releases/download/v0.7.4-dylib/libptrscan_pince-x86_64-unknown-linux-gnu.tar.gz || return 1
		tar xf libptrscan.tar.gz --strip-components 1 || return 1
		rm -f libptrscan.tar.gz
		cd ../..
    ) || return 1
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
PKG_NAMES_ALL="python3-pip gdb cmake"
PKG_NAMES_DEBIAN="$PKG_NAMES_ALL python3-dev python3-venv pkg-config qt6-l10n-tools libcairo2-dev libgirepository1.0-dev libxcb-randr0-dev libxcb-xtest0-dev libxcb-xinerama0-dev libxcb-shape0-dev libxcb-xkb-dev libxcb-cursor0"
PKG_NAMES_SUSE="$PKG_NAMES_ALL gcc python3-devel qt6-tools-linguist typelib-1_0-Gtk-3_0 cairo-devel gobject-introspection-devel make"
PKG_NAMES_FEDORA="$PKG_NAMES_ALL python3-devel qt6-linguist redhat-lsb cairo-devel gobject-introspection-devel cairo-gobject-devel"
PKG_NAMES_ARCH="python-pip qt6-tools gdb cmake lsb-release pkgconf gobject-introspection-runtime" # arch defaults to py3 nowadays

INSTALL_COMMAND="install"

set_install_vars() {
	case $1 in
	*SUSE*)
		PKG_MGR="zypper"
		PKG_NAMES="$PKG_NAMES_SUSE"
		LRELEASE_CMD="lrelease6"
		;;
	*Arch*)
		PKG_MGR="pacman"
		PKG_NAMES="$PKG_NAMES_ARCH"
		INSTALL_COMMAND="-S --needed"
		LRELEASE_CMD="/usr/lib/qt6/bin/lrelease"
		;;
	*Fedora*)
		PKG_MGR="dnf -y"
		PKG_NAMES="$PKG_NAMES_FEDORA"
		LRELEASE_CMD="lrelease-qt6"
		;;
	*Debian*|*Ubuntu*)
		PKG_MGR="apt -y"
		PKG_NAMES="$PKG_NAMES_DEBIAN"
		LRELEASE_CMD="/usr/lib/qt6/bin/lrelease"
		;;
	*)
		return 1
		;;
	esac

	return 0
}

compile_translations() {
	${LRELEASE_CMD} i18n/ts/*
	mkdir -p i18n/qm
	mv i18n/ts/*.qm i18n/qm/
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
pip3 install --upgrade pip || exit_on_error

# shellcheck disable=SC2086
pip3 install -r requirements.txt || exit_on_error

install_libscanmem || exit_on_error
install_libptrscan || exit_on_error

compile_translations || exit_on_error

echo
echo "PINCE has been installed successfully!"
echo "Now, just run 'sh PINCE.sh' from terminal"
