#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data=${XDG_DATA_HOME:-"$HOME/.local/share"}
dest=$data/shooty
bin=$HOME/.local/bin
applications=$data/applications
icons=$data/icons/hicolor/scalable/apps
launcher=$bin/shooty
desktop=$applications/shooty.desktop
icon=$icons/shooty.svg
mkdir -p "$data" "$bin" "$applications" "$icons"
owned_file() { [ ! -e "$1" ] || { [ -f "$1" ] && grep -q 'shooty-install-owned' "$1"; }; }
if [ -e "$dest" ] && [ ! -f "$dest/.shooty-install-owned" ]; then echo "Refusing to replace unowned path: $dest" >&2; exit 1; fi
for file in "$launcher" "$desktop" "$icon"; do
    if [ -e "$file" ] && ! owned_file "$file"; then echo "Refusing to replace unowned file: $file" >&2; exit 1; fi
done
stage=$(mktemp -d "$data/.shooty-install.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM
cp -R "$base/app/." "$stage/"
touch "$stage/.shooty-install-owned"
if [ -e "$dest" ]; then mv "$dest" "$stage/previous"; fi
mv "$stage" "$dest"
rm -rf "$dest/previous"
trap - EXIT HUP INT TERM
cat > "$launcher.tmp" <<EOF_LAUNCHER
#!/bin/sh
# shooty-install-owned
exec "$dest/bundle/shooty" "\$@"
EOF_LAUNCHER
chmod 755 "$launcher.tmp"
mv -f "$launcher.tmp" "$launcher"
cp "$base/shooty.desktop" "$desktop.tmp"
# Point the installed desktop entry directly at the stable user-local command.
sed "s|^Exec=shooty$|Exec=$launcher|; s|^Exec=shooty capture$|Exec=$launcher capture|; s|^Exec=shooty indicator$|Exec=$launcher indicator|" "$desktop.tmp" > "$desktop"
rm -f "$desktop.tmp"
sed -i '1a# shooty-install-owned' "$desktop"
cp "$base/shooty.svg" "$icon.tmp"
mv -f "$icon.tmp" "$icon"
sed -i '1a<!-- shooty-install-owned -->' "$icon"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$applications" >/dev/null 2>&1 || true
printf 'Installed Shooty. Ensure %s is on PATH to use the shooty command.\n' "$bin"
