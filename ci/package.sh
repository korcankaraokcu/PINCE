#!/bin/sh
: '
Copyright (C) 2024 brkzlr <brksys@icloud.com>

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

# Create cleanup function to remove remaining deps/files
cleanup () {
	cd "$PACKAGEDIR" || return
	# Remove everything outside of package.sh and AppImage output
	find ! -iname "package.sh" ! -iname "PINCE*.AppImage" ! -iname "PINCE*.zsync" -delete
}
trap cleanup EXIT

# Error checking function
exit_on_failure() {
	echo
	echo "Error occured while creating AppImage! Check the log above!"
	exit 1
}

# Reuse install.sh's functions
PINCE_LIB_ONLY=1
. ../install.sh

if [ -r /etc/os-release ]; then
	. /etc/os-release
	OS_NAME="$ID $ID_LIKE"
fi
set_install_vars "$OS_NAME" || LRELEASE_CMD="$(command -v lrelease6)" # fallback for unsupported distros
case $OS_NAME in *arch*) export NO_STRIP=1 ;; esac # skip strip on Arch for linuxdeploy

# Download necessary tools
curl -L -O https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
DEPLOYTOOL=./linuxdeploy-x86_64.AppImage
chmod +x $DEPLOYTOOL

curl -L -O https://raw.githubusercontent.com/TheAssassin/linuxdeploy-plugin-conda/master/linuxdeploy-plugin-conda.sh
CONDAPLUGIN=./linuxdeploy-plugin-conda.sh
chmod +x $CONDAPLUGIN

# Create AppImage's AppDir with a Conda environment pre-baked
# containing our required pip packages
export PIP_REQUIREMENTS="-r ../requirements.txt"
# Need this to get libstdc++ higher than default 6.0.29 and libxcb-cursor for Debian family
export CONDA_PACKAGES="libstdcxx-ng;xcb-util-cursor"
$DEPLOYTOOL --appdir AppDir -pconda || exit_on_failure

# Create PINCE directory
mkdir -p AppDir/opt/PINCE

# Set LIBMEMSCAN_CPU so libmemscan builds with SSE4.2 and not AVX512 (which is the default on our GitHub runner).
# This way users with CPUs older than 2016 (but not older than 2009) can use our AppImage.
cd ..
SCRIPTDIR="$PWD"
LIBMEMSCAN_CPU="-Dcpu=x86_64_v2"
build_libmemscan || exit_on_failure
build_mono_collector || exit_on_failure
compile_translations || exit_on_failure

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
export CPPFLAGS="-I${CONDA_PREFIX}/include ${CPPFLAGS}"
export LDFLAGS="-L${CONDA_PREFIX}/lib ${LDFLAGS}"
export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

NUM_MAKE_JOBS="$(nproc --ignore=1)"
# Grab latest GDB at time of writing and compile it with our conda Python
curl -L -O "https://ftp.gnu.org/gnu/gdb/gdb-17.2.tar.gz"
tar xf gdb-17.2.tar.gz
rm gdb-17.2.tar.gz
cd gdb-17.2 || exit
./configure --with-python="$(readlink -f ../wrapper.sh)" --prefix=/usr || exit_on_failure
make -j"$NUM_MAKE_JOBS" || exit_on_failure
make install DESTDIR="$INSTALLDIR"
cd ..
rm -rf gdb-17.2
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
	# Check if we have both polkit/pkexec installed AND also an authentication agent so we can properly prompt for credentials.
	# Some WMs (like Hyprland) come with no agent by default (they have to manually install hyprpolkitagent) so even though the distro has polkitd active,
	# there's no agent for the prompt and authentication fails for the user with a vague unrelated xcb message.
	if command -v pkexec > /dev/null 2>&1 && pgrep -f 'polkit.*agent|policykit.*agent|agent-polkit|xfce-polkit|mate-polkit|lxpolkit|cinnamon|gnome-shell|soteria|pkttyagent' > /dev/null 2>&1; then
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
		sudo -E --preserve-env=PATH "$APPIMAGE" "$PCT_FILE"
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
export LDAI_UPDATE_INFORMATION="gh-releases-zsync|korcankaraokcu|PINCE|latest|PINCE-x86_64.AppImage.zsync"
$DEPLOYTOOL --icon-file PINCE.png --appdir AppDir/ --output appimage --custom-apprun AppRun.sh || exit_on_failure
