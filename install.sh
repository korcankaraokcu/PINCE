#!/bin/sh
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

exit_on_error() {
	echo
	echo "Error occured while installing PINCE, check the output above for more information"
	echo "Installation failed."
	exit 1
}

build_libmemscan() {
	git submodule update --init --recursive || return 1
	mkdir -p libpince/libmemscan
	if [ -f "libpince/libmemscan/libmemscan.so" ] && [ -z "$PINCE_LIB_ONLY" ]; then
		echo "Recompile libmemscan? [y/n]"
		read -r answer
		if ! echo "$answer" | grep -iq "^[Yy]"; then
			return 0
		fi
	fi
	(
		echo "Building libmemscan..."
		cd libmemscan || return 1
		if [ ! -f "./zig" ]; then
			echo "Downloading Zig v0.16.0"
			curl -L -o zig.tar.xz https://ziglang.org/download/0.16.0/zig-x86_64-linux-0.16.0.tar.xz
			tar xf zig.tar.xz --strip-components 1 --wildcards "*/lib" "*/zig"
			rm zig.tar.xz
		fi
		./zig build -Doptimize=ReleaseFast ${LIBMEMSCAN_CPU} || return 1
		cp --preserve zig-out/lib/libmemscan.so ../libpince/libmemscan/ || return 1
		cp --preserve memscan.py ../libpince/libmemscan/ || return 1
	) || return 1
	return 0
}

build_mono_collector() {
	ZIG="$SCRIPTDIR/libmemscan/zig"
	mkdir -p libpince/libmono_collector
	if [ -f "libpince/libmono_collector/mono_collector_x64.so" ] && [ -f "libpince/libmono_collector/mono_collector_x86.so" ] && [ -f "libpince/libmono_collector/mono_collector_wine_x64.so" ] && [ -f "libpince/libmono_collector/mono_collector_wine_x86.so" ] && [ -z "$PINCE_LIB_ONLY" ]; then
		echo "Recompile Mono collector? [y/n]"
		read -r answer
		if ! echo "$answer" | grep -iq "^[Yy]"; then
			return 0
		fi
	fi
	(
		echo "Building Mono collector..."
		cd mono_collector || return 1
		"$ZIG" build -Doptimize=ReleaseFast -Dtarget=x86_64-linux-gnu || return 1
		cp --preserve zig-out/lib/libmono_collector.so ../libpince/libmono_collector/mono_collector_x64.so || return 1
		"$ZIG" build -Doptimize=ReleaseFast -Dtarget=x86-linux-gnu || return 1
		cp --preserve zig-out/lib/libmono_collector.so ../libpince/libmono_collector/mono_collector_x86.so || return 1
		"$ZIG" build -Doptimize=ReleaseFast -Dtarget=x86_64-linux-gnu -Dwine=true || return 1
		cp --preserve zig-out/lib/libmono_collector.so ../libpince/libmono_collector/mono_collector_wine_x64.so || return 1
		"$ZIG" build -Doptimize=ReleaseFast -Dtarget=x86-linux-gnu -Dwine=true || return 1
		cp --preserve zig-out/lib/libmono_collector.so ../libpince/libmono_collector/mono_collector_wine_x86.so || return 1
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

	printf "%s" "Choose: "; read -r OPTION
	OPTION=$(echo "$OPTION" | tr '[:lower:]' '[:upper:]')

	case $OPTION in
	1|*APT*)
		OS_NAME="debian"
		;;
	2|*PACMAN*)
		OS_NAME="arch"
		;;
	3|*DNF*)
		OS_NAME="fedora"
		;;
	4|*ZYPPER*)
		OS_NAME="suse"
		;;
	*)
		return 1
		;;
	esac

	return 0
}

# About xcb packages -> https://github.com/cdgriffith/FastFlix/wiki/Common-questions-and-problems
PKG_NAMES_ALL="python3-pip gdb"
PKG_NAMES_DEBIAN="$PKG_NAMES_ALL python3-dev python3-venv qt6-l10n-tools libxcb-randr0 libxcb-shape0 libxcb-xkb1 libxcb-cursor0"
PKG_NAMES_SUSE="$PKG_NAMES_ALL python3-devel qt6-tools-linguist"
PKG_NAMES_FEDORA="$PKG_NAMES_ALL python3-devel qt6-linguist"
PKG_NAMES_ARCH="python-pip qt6-tools gdb" # arch defaults to py3 nowadays

INSTALL_COMMAND="install"

set_install_vars() {
	case $1 in
	*suse*)
		PKG_MGR="zypper"
		PKG_NAMES="$PKG_NAMES_SUSE"
		LRELEASE_CMD="lrelease6"
		;;
	*arch*)
		PKG_MGR="pacman"
		PKG_NAMES="$PKG_NAMES_ARCH"
		INSTALL_COMMAND="-S --needed"
		LRELEASE_CMD="/usr/lib/qt6/bin/lrelease"
		;;
	*fedora*)
		PKG_MGR="dnf -y"
		PKG_NAMES="$PKG_NAMES_FEDORA"
		LRELEASE_CMD="lrelease-qt6"
		;;
	*debian*|*ubuntu*)
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
	${LRELEASE_CMD} i18n/ts/* || return 1
	mkdir -p i18n/qm
	mv i18n/ts/*.qm i18n/qm/
	return 0
}

main() {
	if [ "$(id -u)" = "0" ]; then
		echo "Please do not run this script as root!"
		exit 1
	fi

	SCRIPTDIR=$(cd -- "$(dirname -- "$0")" && pwd -P)
	cd "$SCRIPTDIR" || exit

	if [ ! -d ".git" ]; then
		echo "Error! Could not find \".git\" folder!"
		echo "This can happen if you downloaded the ZIP file instead of cloning through git."
		echo "Please clone the PINCE repository using the \"--recursive\" flag and try again!"
		echo "For more information, please follow the installation instructions on GitHub."
		exit 1
	fi

	if [ -r /etc/os-release ]; then
		. /etc/os-release
		OS_NAME="$ID $ID_LIKE"
	fi

	if ! set_install_vars "$OS_NAME"; then
		if ! ask_pkg_mgr; then
			echo
			echo "Sorry, your distro is not supported!"
			exit 1
		fi

		set_install_vars "$OS_NAME"
	fi

	sudo ${PKG_MGR} ${INSTALL_COMMAND} ${PKG_NAMES} || exit_on_error

	# Prepare Python virtual environment
	if [ ! -d ".venv/bin" ]; then
		python3 -m venv .venv
	fi
	. .venv/bin/activate

	pip3 install --upgrade pip || exit_on_error
	pip3 install -r requirements.txt || exit_on_error

	build_libmemscan || exit_on_error
	build_mono_collector || exit_on_error
	compile_translations || exit_on_error

	echo
	echo "PINCE has been installed successfully!"
	echo "Now, just run 'sh PINCE.sh' from terminal"
}

if [ -z "$PINCE_LIB_ONLY" ]; then
	main
fi
