#!/usr/bin/env bash
# Make the notes now from the most recently saved email (in SermonEmails/inbox,
# done or failed), exactly as the watcher service would. Use it when the
# watcher missed an email or failed on it.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo"
exec /usr/bin/python3 -m sermon_notes.inbox --latest "$@"
