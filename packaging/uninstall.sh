#!/bin/sh
set -eu
data=${XDG_DATA_HOME:-"$HOME/.local/share"}
[ ! -f "$data/shooty/.shooty-install-owned" ] || rm -rf "$data/shooty"
launcher=$HOME/.local/bin/shooty
desktop=$data/applications/shooty.desktop
icon=$data/icons/hicolor/scalable/apps/shooty.svg
for file in "$launcher" "$desktop" "$icon"; do
    if [ -f "$file" ] && grep -q 'shooty-install-owned' "$file"; then rm -f "$file"; fi
done
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$data/applications" >/dev/null 2>&1 || true
printf 'Removed Shooty files owned by this installer.\n'
