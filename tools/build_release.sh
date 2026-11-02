#!/bin/sh
# Build the Ubuntu 24.04 PyInstaller release archive. `uv` and PyInstaller are
# developer build tools; the resulting end-user archive needs no Python PM.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(PYTHONPATH="$root/src" python3 -c 'from shooty import __version__; print(__version__)')
name=shooty-$version
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
mkdir -p "$stage/$name/app/bundle"
uv venv --system-site-packages --python /usr/bin/python3 "$stage/build-env"
uv pip install --python "$stage/build-env/bin/python" pyinstaller==6.22.3 platformdirs jaraco.text
PYTHONNOUSERSITE=1 "$stage/build-env/bin/pyinstaller" --noconfirm --clean --onedir \
    --name shooty --paths "$root/src" \
    --distpath "$stage/pyinstaller-dist" --workpath "$stage/pyinstaller-work" \
    --specpath "$stage" \
    --collect-all PIL --collect-all platformdirs --collect-all jaraco \
    --hidden-import=gi._gi_cairo --hidden-import=cairo \
    --hidden-import=gi.repository.Gtk --hidden-import=gi.repository.Gdk \
    --hidden-import=gi.repository.GdkPixbuf --hidden-import=gi.repository.Gio \
    --hidden-import=gi.repository.GLib --hidden-import=gi.repository.AyatanaAppIndicator3 \
    --exclude-module=gi.repository.Gst --exclude-module=gi.repository.GstBase \
    --exclude-module=gi.repository.GstApp --exclude-module=gi.repository.GstAudio \
    --exclude-module=gi.repository.GstVideo --exclude-module=gi.repository.GstController \
    "$root/tools/pyinstaller_entry.py"
cp -R "$stage/pyinstaller-dist/shooty/." "$stage/$name/app/bundle/"
cp "$root/packaging/install.sh" "$root/packaging/uninstall.sh" "$root/packaging/shooty.desktop" "$root/packaging/shooty.svg" "$stage/$name/"
cp "$root/README.md" "$stage/$name/README.md"
chmod +x "$stage/$name/install.sh" "$stage/$name/uninstall.sh"
mkdir -p "$root/dist"
tar -C "$stage" -czf "$root/dist/$name.tar.gz" "$name"
(cd "$root/dist" && sha256sum "$name.tar.gz" > "$name.tar.gz.sha256")
printf 'Built dist/%s.tar.gz\n' "$name"
