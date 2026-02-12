#!/bin/bash
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
cd $PACKAGEDIR

# Check what distro we use for lrelease path
LSB_RELEASE="$(command -v lsb_release)"
if [ -n "$LSB_RELEASE" ]; then
    OS_NAME="$(${LSB_RELEASE} -d -s)"
else
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_NAME="$NAME"
fi
case $OS_NAME in
*SUSE*)
	LRELEASE_CMD="lrelease6"
	;;
*Arch*)
	LRELEASE_CMD="/usr/lib/qt6/bin/lrelease"
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
	cd $PACKAGEDIR
	# Remove everything outside of package.sh and AppImage output
	ls --hide=package.sh --hide=PINCE*.AppImage | xargs rm -rf
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

# Install libscanmem
NUM_MAKE_JOBS="$(nproc --ignore=1)"
cd ..
git submodule update --init --recursive
if [ ! -d "libpince/libscanmem" ]; then
	mkdir libpince/libscanmem
fi
cd libscanmem-PINCE
cmake -DCMAKE_BUILD_TYPE=Release . || exit_on_failure
make -j"$NUM_MAKE_JOBS" || exit_on_failure
cp --preserve libscanmem.so ../libpince/libscanmem
cp --preserve wrappers/scanmem.py ../libpince/libscanmem
cd ..

# Install libptrscan
if [ ! -d "libpince/libptrscan" ]; then
	mkdir libpince/libptrscan
fi
cd libpince/libptrscan
curl -L -o libptrscan.tar.gz https://github.com/kekeimiku/PointerSearcher-X/releases/download/v0.7.4-dylib/libptrscan_pince-x86_64-unknown-linux-gnu.tar.gz || exit_on_failure
tar xf libptrscan.tar.gz --strip-components 1 || exit_on_failure
rm -f libptrscan.tar.gz
cd ../..

# Compile translations
${LRELEASE_CMD} i18n/ts/* || exit_on_failure
mkdir -p i18n/qm
mv i18n/ts/*.qm i18n/qm/

# Copy necessary PINCE folders/files to inside AppDir
cp -r GUI i18n libpince media tr AUTHORS COPYING COPYING.CC-BY PINCE.py THANKS ci/AppDir/opt/PINCE/
cd ci

# Create a wrapper so GDB can correctly link against the
# included conda's python environment to ensure compatibility
# Taken from: https://github.com/pwndbg/pwndbg/pull/892
cat > wrapper.sh <<\EOF
#!/bin/bash
if [[ -z "$CONDA_PREFIX" ]]; then
	echo "Error: CONDA_PREFIX not set"
	exit 2
fi
echo "$(date +%F) -- $@" >> /tmp/args.txt
if [[ $1 != *"python-config.py"* ]]; then
	exec "$CONDA_PREFIX"/bin/python3
fi
# get rid of the first parameter, which is the path to the python-config.py script
shift
# python3-config --ldflags lacks the python library
# also gdb won't link on GitHub actions without libtinfow, which is not provided by the conda environment
if [[ "$1" == "--ldflags" ]]; then
	echo -n "-lpython3.13 -ltinfow "
fi
exec "$CONDA_PREFIX"/bin/python3-config "$@"
EOF
chmod +x wrapper.sh

# Prepare some env vars for GDB compilation
INSTALLDIR=$(pwd)/AppDir
export CONDA_PREFIX="$(readlink -f $INSTALLDIR/usr/conda)"

# Grab latest GDB at time of writing and compile it with our conda Python
curl -L -O "https://ftp.gnu.org/gnu/gdb/gdb-16.3.tar.gz"
tar xf gdb-16.3.tar.gz
rm gdb-16.3.tar.gz
cd gdb-16.3
./configure --with-python="$(readlink -f ../wrapper.sh)" --prefix=/usr || exit_on_failure
make -j"$NUM_MAKE_JOBS" || exit_on_failure
make install DESTDIR=$INSTALLDIR
cd ..
rm -rf gdb-16.3
rm wrapper.sh

# Create a fake but needed desktop file for AppImage
cat > AppDir/usr/share/applications/PINCE.desktop <<\EOF
[Desktop Entry]
Name=PINCE
Exec=PINCE
Icon=PINCE
Type=Application
Terminal=true
Categories=Development;
EOF

# Placeholder icon for above desktop file
touch AppDir/usr/share/icons/hicolor/scalable/apps/PINCE.svg

# Create main running script
cat > AppRun.sh <<\EOF
#!/bin/bash

if [ "$(id -u)" != "0" ]; then
	if type pkexec &> /dev/null; then
		# Preserve env vars to keep settings like theme preferences.
		# Pkexec does not support passing all of env via a flag like `-E` so we need to
		# rebuild the env and then pass it through.
		ENV=()
		while IFS='=' read -r key value; do
			[ -z "$key" ] && continue
			value="${value//\\/\\\\}"
			value="${value//\"/\\\"}"
			ENV+=("$key=$value")
		done < <(env)

		pkexec env "${ENV[@]}" "$APPIMAGE"
	elif type sudo &> /dev/null; then
		# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons
		# so we need to force PATH preservation with venv activated user's PATH.
		sudo -E --preserve-env=PATH,PYTHONDONTWRITEBYTECODE "$APPIMAGE"
	else
		echo "No supported privilege escalation utility found. Please run this AppImage as root manually."
		exit 1
	fi
else
	export APPDIR="$(dirname "$0")"
	export PYTHONHOME="$APPDIR/usr/conda"

	"$APPDIR/usr/bin/python3" "$APPDIR/opt/PINCE/PINCE.py"
fi
EOF
chmod +x AppRun.sh

# Patch libqxcb's runpath (not rpath) to point to our packaged libxcb-cursor to fix X11 issues
patchelf --add-rpath "\$ORIGIN/../../../../../../" AppDir/usr/conda/lib/python3.13/site-packages/PyQt6/Qt6/plugins/platforms/libqxcb.so

# Package AppDir into AppImage
export LD_LIBRARY_PATH="$(readlink -f ./AppDir/usr/conda/lib)"
$DEPLOYTOOL --appdir AppDir/ --output appimage --custom-apprun AppRun.sh || exit_on_failure
