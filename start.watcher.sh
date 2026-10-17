#!/usr/bin/env bash
# Install (or refresh) and start the systemd user watcher that turns emails
# saved by Thunderbird into Sermon Notes. Safe to run again after a git pull.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
units="$HOME/.config/systemd/user"

git -C "$repo" pull --ff-only

mkdir -p "$units"
cp "$repo/contrib/sermon-notes.path" "$units/"
# Point the service at wherever this repo actually lives.
sed "s|^WorkingDirectory=.*|WorkingDirectory=$repo|" \
    "$repo/contrib/sermon-notes.service" > "$units/sermon-notes.service"

systemctl --user daemon-reload
systemctl --user enable --now sermon-notes.path
# Process anything already waiting in the inbox.
systemctl --user start sermon-notes.service || true

systemctl --user --no-pager status sermon-notes.path | head -3
journalctl --user -u sermon-notes.service -n 5 --no-pager | cat
