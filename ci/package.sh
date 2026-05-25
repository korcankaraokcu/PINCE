#!/bin/sh
: '
Copyright (C) 2024 brkzlr <brkozler@gmail.com>

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

# Check if the file is in the correct directory and cd there
# This script should be only in PINCE/ci folder
PACKAGEDIR="$(dirname "$(readlink -f "$0")")"
case $PACKAGEDIR in
	*"PINCE/ci") ;;
	*) echo "package.sh is not in PINCE/ci folder!"; exit 1;;
esac
cd "$PACKAGEDIR" || exit

# Check what distro we use for lrelease path
LSB_RELEASE="$(command -v lsb_release)"
if [ -n "$LSB_RELEASE" ]; then
	OS_NAME="$(${LSB_RELEASE} -d -s)"
else
	. /etc/os-release
	OS_NAME="$NAME"
fi
case $OS_NAME in
*SUSE*)
	LRELEASE_CMD="lrelease6"
	;;
*Arch*)
	LRELEASE_CMD="/usr/lib/qt6/bin/lrelease"
	export NO_STRIP=1
	;;
*Fedora*)
	LRELEASE_CMD="lrelease-qt6"
	;;
*Debian*|*Ubuntu*)
	LRELEASE_CMD="/usr/lib/qt6/bin/lrelease"
	;;
*)
	LRELEASE_CMD="$(which lrelease6)" # Placeholder
	;;
esac

# Download necessary tools
curl -L -O https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
DEPLOYTOOL=./linuxdeploy-x86_64.AppImage
chmod +x $DEPLOYTOOL

curl -L -O https://raw.githubusercontent.com/TheAssassin/linuxdeploy-plugin-conda/master/linuxdeploy-plugin-conda.sh
CONDAPLUGIN=./linuxdeploy-plugin-conda.sh
chmod +x $CONDAPLUGIN

# Create cleanup function to remove remaining deps/files
cleanup () {
	cd "$PACKAGEDIR" || return
	# Remove everything outside of package.sh and AppImage output
	find ! -iname "package.sh" ! -iname "PINCE*.AppImage" -delete
}
trap cleanup EXIT

# Error checking function
exit_on_failure() {
	if [ "$?" -ne 0 ]; then
		echo
		echo "Error occured while creating AppImage! Check the log above!"
		exit 1
	fi
}

# Create AppImage's AppDir with a Conda environment pre-baked
# containing our required pip packages
export PIP_REQUIREMENTS="-r ../requirements.txt"
# Need this to get libstdc++ higher than default 6.0.29 and libxcb-cursor for Debian family
export CONDA_PACKAGES="libstdcxx-ng;xcb-util-cursor"
$DEPLOYTOOL --appdir AppDir -pconda || exit_on_failure

# Create PINCE directory
mkdir -p AppDir/opt/PINCE

# Install libmemscan
cd ..
git submodule update --init --recursive
if [ ! -d "libpince/libmemscan" ]; then
	mkdir libpince/libmemscan
fi
cd libmemscan || exit
if [ ! -f "./zig" ]; then
	curl -L -o zig.tar.xz https://ziglang.org/download/0.16.0/zig-x86_64-linux-0.16.0.tar.xz
	tar xf zig.tar.xz --strip-components 1 --wildcards "*/lib" "*/zig"
	rm zig.tar.xz
fi
./zig build -Doptimize=ReleaseFast || exit_on_failure
cp --preserve zig-out/lib/libmemscan.so ../libpince/libmemscan/ || exit_on_failure
cp --preserve memscan.py ../libpince/libmemscan/ || exit_on_failure
cd ..

# Compile translations
${LRELEASE_CMD} i18n/ts/* || exit_on_failure
mkdir -p i18n/qm
mv i18n/ts/*.qm i18n/qm/

# Copy necessary PINCE folders/files to inside AppDir
cp -r GUI i18n libpince media tr AUTHORS COPYING COPYING.CC-BY PINCE.py THANKS ci/AppDir/opt/PINCE/
cd ci || exit

# Create a wrapper so GDB can correctly link against the
# included conda's python environment to ensure compatibility
# Taken from: https://github.com/pwndbg/pwndbg/pull/892
cat > wrapper.sh <<\EOF
#!/bin/sh
if [ -z "$CONDA_PREFIX" ]; then
	echo "Error: CONDA_PREFIX not set"
	exit 2
fi
echo "$(date +%F) -- $*" >> /tmp/args.txt
case $1 in
	*python-config.py*) ;;
	*) exec "$CONDA_PREFIX"/bin/python3 ;;
esac
# get rid of the first parameter, which is the path to the python-config.py script
shift
# python3-config --ldflags lacks the python library
# also gdb won't link on GitHub actions without libtinfow, which is not provided by the conda environment
if [ "$1" = "--ldflags" ]; then
	printf '%s' "-lpython3.13 -ltinfow "
fi
exec "$CONDA_PREFIX"/bin/python3-config "$@"
EOF
chmod +x wrapper.sh

# Prepare some env vars for GDB compilation
INSTALLDIR=$(pwd)/AppDir
CONDA_PREFIX="$(readlink -f "$INSTALLDIR/usr/conda")"
export CONDA_PREFIX

NUM_MAKE_JOBS="$(nproc --ignore=1)"
# Grab latest GDB at time of writing and compile it with our conda Python
curl -L -O "https://ftp.gnu.org/gnu/gdb/gdb-17.1.tar.gz"
tar xf gdb-17.1.tar.gz
rm gdb-17.1.tar.gz
cd gdb-17.1 || exit
./configure --with-python="$(readlink -f ../wrapper.sh)" --prefix=/usr || exit_on_failure
make -j"$NUM_MAKE_JOBS" || exit_on_failure
make install DESTDIR="$INSTALLDIR"
cd ..
rm -rf gdb-17.1
rm wrapper.sh

# Create a desktop file for AppImage
cat > AppDir/usr/share/applications/PINCE.desktop <<\EOF
[Desktop Entry]
Name=PINCE
Exec=PINCE
Icon=PINCE
Type=Application
Categories=Development;
EOF

# Copy icon for the above desktop file
cp ../media/logo/ozgurozbek/pince_appimage.png PINCE.png

# Create main running script
cat > AppRun.sh <<\APPRUN_EOF
#!/bin/sh

if [ -n "$1" ]; then
    PCT_DIR=$(cd -P -- "$(dirname -- "$1")" && pwd -P) || exit 1
    PCT_FILE="$PCT_DIR/$(basename -- "$1")"
fi

if [ "$(id -u)" != "0" ]; then
	if command -v pkexec > /dev/null 2>&1; then
		# Preserve env vars to keep settings like theme preferences.
		# Pkexec does not support passing all of env via a flag like `-E` so we need to
		# rebuild the env and then pass it through.
		set --
		while IFS= read -r line
		do
			set -- "$@" "$line"
		done <<EOF
$(printenv)
EOF

		pkexec env "$@" "$APPIMAGE" "$PCT_FILE"
	elif command -v sudo > /dev/null 2>&1; then
		# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons
		# so we need to force PATH preservation with venv activated user's PATH.
		sudo -E --preserve-env=PATH PYTHONDONTWRITEBYTECODE=1 "$APPIMAGE" "$PCT_FILE"
	else
		echo "No supported privilege escalation utility found. Please run this as root manually."
		exit 1
	fi

	exit
fi
APPDIR="$(dirname "$0")"
export APPDIR
export PYTHONHOME=$APPDIR/usr/conda
$APPDIR/usr/bin/python3 $APPDIR/opt/PINCE/PINCE.py "$PCT_FILE"
APPRUN_EOF
chmod +x AppRun.sh

# Patch libqxcb's runpath (not rpath) to point to our packaged libxcb-cursor to fix X11 issues
patchelf --add-rpath "\$ORIGIN/../../../../../../" AppDir/usr/conda/lib/python3.13/site-packages/PyQt6/Qt6/plugins/platforms/libqxcb.so

# Package AppDir into AppImage
LD_LIBRARY_PATH="$(readlink -f ./AppDir/usr/conda/lib)"
export LD_LIBRARY_PATH
$DEPLOYTOOL --icon-file PINCE.png --appdir AppDir/ --output appimage --custom-apprun AppRun.sh || exit_on_failure
