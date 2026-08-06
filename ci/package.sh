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
cd "$PACKAGEDIR" || exit
[ -f ../install.sh ] && [ -f ../PINCE.py ] || { echo "package.sh is not in PINCE/ci folder!"; exit 1; }

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
	echo "Error occurred while creating AppImage! Check the log above!"
	exit 1
}
cleanup || exit_on_failure

# Reuse install.sh's functions
PINCE_LIB_ONLY=1
. ../install.sh

if [ -r /etc/os-release ]; then
	. /etc/os-release
	OS_NAME="$ID $ID_LIKE"
fi
set_install_vars "$OS_NAME" || LRELEASE_CMD="$(command -v lrelease6)" # fallback for unsupported distros
case $OS_NAME in *arch*) export NO_STRIP=1 ;; esac # skip strip on Arch for linuxdeploy
export ARCH=x86_64

# Download necessary tools
DEPLOYTOOL=./linuxdeploy-x86_64.AppImage
curl -fLO https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage || exit_on_failure
curl -fLO https://raw.githubusercontent.com/TheAssassin/linuxdeploy-plugin-conda/master/linuxdeploy-plugin-conda.sh || exit_on_failure
chmod +x "$DEPLOYTOOL" linuxdeploy-plugin-conda.sh || exit_on_failure

# Create AppImage's AppDir with a Conda environment pre-baked containing Python, GDB and our pip packages.
# Need xcb-util-cursor for Debian family and a CA bundle for Python HTTPS requests inside the AppImage.
# Qt intentionally stays on the PyQt6 wheels instead of conda because the wheels bundle no glib/pango/cairo,
# so the entire GTK stack comes from the host and stays self-consistent.
# Conda ships its own copies of those and wins some SONAMEs while the host wins others, breaking the GTK platform theme when the versions differ.
printf '%s\n' 'channels: [conda-forge]' 'default_channels: []' > conda-appimage.yml || exit_on_failure
CONDARC="$PWD/conda-appimage.yml" PIP_REQUIREMENTS="--only-binary=:all: -r ../requirements.txt" \
	CONDA_PACKAGES="python=3.14.6;gdb=17.2;xcb-util-cursor;ca-certificates" "$DEPLOYTOOL" --appdir AppDir -pconda || exit_on_failure

# The wheels ship the whole of Qt, so walk the ELF dependencies of the modules a widgets app actually loads and delete everything unreachable,
# dropping Quick, QML, 3D, Multimedia/ffmpeg and Designer.
AppDir/usr/conda/bin/python3 - AppDir/usr/conda/lib/python3.14/site-packages/PyQt6/Qt6 <<'PRUNE_EOF' || exit_on_failure
import glob, os, shutil, subprocess, sys
qt_dir, lib = sys.argv[1], sys.argv[1] + "/lib"
keep = ["platforms", "platformthemes", "platforminputcontexts", "iconengines", "imageformats", "printsupport",
	"xcbglintegrations", "tls", "networkinformation", "generic", "wayland-decoration-client",
	"wayland-graphics-integration-client", "wayland-shell-integration"]
todo = [f"{lib}/libQt6{m}.so.6" for m in ("Core", "Gui", "Widgets", "DBus", "Svg", "PrintSupport", "Network")]
todo += [p for name in keep for p in glob.glob(f"{qt_dir}/plugins/{name}/*.so")]
alive = set()
while todo:
	path = os.path.realpath(todo.pop())
	if path in alive or not os.path.isfile(path):
		continue
	alive.add(path)
	needed = subprocess.run(["patchelf", "--print-needed", path], capture_output=True, text=True).stdout
	todo += [f"{lib}/{so}" for so in needed.split()]
for path in glob.glob(f"{lib}/*.so*"):
	if os.path.isfile(path) and os.path.realpath(path) not in alive:
		os.remove(path)
for name in os.listdir(f"{qt_dir}/plugins"):
	if name not in keep:
		shutil.rmtree(f"{qt_dir}/plugins/{name}")
shutil.rmtree(f"{qt_dir}/qml", ignore_errors=True)
PRUNE_EOF

# Keep AppImage paths out of programs launched by GDB
rm AppDir/usr/bin/gdb || exit_on_failure
cat > AppDir/usr/bin/gdb <<'GDB_WRAPPER_EOF' || exit_on_failure
#!/bin/sh
exec "$(dirname "$0")/../conda/bin/gdb" -iex 'unset environment PYTHONHOME' -iex 'unset environment APPDIR' "$@"
GDB_WRAPPER_EOF
chmod +x AppDir/usr/bin/gdb || exit_on_failure

# Create PINCE directory
mkdir -p AppDir/opt/PINCE || exit_on_failure

# Set LIBMEMSCAN_CPU so libmemscan builds with SSE4.2 and not AVX512 (which is the default on our GitHub runner).
# This way users with CPUs older than 2016 (but not older than 2009) can use our AppImage.
# Also target glibc 2.35 so the build does not inherit a newer runner host's ABI.
cd ..
SCRIPTDIR="$PWD"
LIBMEMSCAN_CPU="-Dtarget=x86_64-linux-gnu.2.35 -Dcpu=x86_64_v2"
build_libmemscan || exit_on_failure
build_mono_collector || exit_on_failure
compile_translations || exit_on_failure

# Copy necessary PINCE folders/files to inside AppDir
cp -r GUI i18n libpince media tr AUTHORS COPYING COPYING.CC-BY PINCE.py THANKS ci/AppDir/opt/PINCE/ || exit_on_failure
cd ci || exit_on_failure

cat > AppDir/opt/PINCE/update-check.json <<\EOF || exit_on_failure
{
  "type": "zsync",
  "url": "https://github.com/korcankaraokcu/PINCE/releases/latest/download/PINCE-x86_64.AppImage.zsync"
}
EOF

# Create a desktop file for AppImage
cat > AppDir/usr/share/applications/PINCE.desktop <<\EOF || exit_on_failure
[Desktop Entry]
Name=PINCE
Exec=PINCE
Icon=PINCE
Type=Application
Categories=Development;
EOF

# Copy icon for the above desktop file
cp ../media/logo/ozgurozbek/pince_appimage.png PINCE.png || exit_on_failure

# Create main running script
cat > AppRun.sh <<\APPRUN_EOF || exit_on_failure
#!/bin/sh

if [ -n "$1" ]; then
    PCT_DIR=$(cd -P -- "$(dirname -- "$1")" && pwd -P) || exit 1
    PCT_FILE="$PCT_DIR/$(basename -- "$1")"
fi

if [ "$(id -u)" != "0" ]; then
	if command -v pkexec > /dev/null 2>&1; then
		# Preserve env vars to keep settings like theme preferences.
		# Pkexec does not support passing all of env via a flag like "-E",
		# so we need to rebuild the env and then pass it through.
		set --
		while IFS= read -r line
		do
			case "$line" in
				BASH_FUNC_*%%=*) continue ;;
				*=*) ;;
				*) continue ;;
			esac
			set -- "$@" "$line"
		done <<EOFENV
$(printenv)
EOFENV

		pince_stdout=/dev/null
		pince_stderr=/dev/null
		[ -t 1 ] && pince_stdout="/proc/$$/fd/1"
		[ -t 2 ] && pince_stderr="/proc/$$/fd/2"

		pkexec_err=$(LC_ALL=C pkexec --disable-internal-agent env "$@" \
			sh -c 'out=$1; err=$2; shift 2; exec "$@" >"$out" 2>"$err"' \
			sh "$pince_stdout" "$pince_stderr" "$APPIMAGE" "$PCT_FILE" \
			2>&1 >/dev/null)
		pkexec_status=$?

		case "$pkexec_err" in
			*"No authentication agent found"*) ;;
			*"Request dismissed"*) exit 126 ;;
			*)
				[ -z "$pkexec_err" ] || printf '%s\n' "$pkexec_err" >&2
				exit "$pkexec_status"
				;;
		esac
	fi

	if command -v sudo > /dev/null 2>&1; then
		# Debian/Ubuntu does not preserve PATH through sudo even with -E for security reasons,
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
export PYTHONHOME="$APPDIR/usr/conda"
exec "$APPDIR/usr/conda/bin/python3" "$APPDIR/opt/PINCE/PINCE.py" "$PCT_FILE"
APPRUN_EOF
chmod +x AppRun.sh || exit_on_failure

# Patch libqxcb's runpath (not rpath) to point to our packaged libxcb-cursor to fix X11 issues
patchelf --add-rpath "\$ORIGIN/../../../../../../" AppDir/usr/conda/lib/python3.14/site-packages/PyQt6/Qt6/plugins/platforms/libqxcb.so || exit_on_failure

# Package AppDir into AppImage
export LDAI_UPDATE_INFORMATION="gh-releases-zsync|korcankaraokcu|PINCE|latest|PINCE-x86_64.AppImage.zsync"
"$DEPLOYTOOL" --icon-file PINCE.png --appdir AppDir/ --output appimage --custom-apprun AppRun.sh || exit_on_failure
