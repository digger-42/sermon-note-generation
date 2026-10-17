"""Make Sermon Notes for every email Thunderbird saved into an inbox folder.

Usage:
    python3 -m sermon_notes.inbox [--inbox DIR] [--notes-dir DIR]

Each .eml file in the inbox is turned into the upcoming Sunday's notes, then
moved to a "done" folder beside the inbox, or to "failed" with a .log of what
went wrong. Run it by hand, or let the systemd units in contrib/ run it
whenever a new file lands in the inbox.
"""

import argparse
import glob
import os
import shutil
import subprocess
import time
import traceback

from . import generate

DEFAULT_INBOX = "/MaresLeg/Church/SermonEmails/inbox"
# Leave files alone until Thunderbird has finished writing them.
SETTLE_SECONDS = 3


def notify(summary, body=""):
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "Sermon Notes", summary + "\n" + body])


def move(path, folder):
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, os.path.basename(path))
    if os.path.exists(dest):
        stem, ext = os.path.splitext(dest)
        dest = "%s-%d%s" % (stem, int(time.time()), ext)
    shutil.move(path, dest)
    return dest


def process(path, notes_dir, base):
    try:
        odt = generate.main([path, "--notes-dir", notes_dir])
    except (Exception, SystemExit) as err:
        dest = move(path, os.path.join(base, "failed"))
        with open(dest + ".log", "w") as log:
            log.write("".join(traceback.format_exception(err)))
        notify("Could not make the notes", "%s: %s" % (os.path.basename(path), err))
        return False
    move(path, os.path.join(base, "done"))
    notify("Notes are ready", os.path.splitext(odt)[0] + ".pdf")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inbox", default=DEFAULT_INBOX)
    ap.add_argument("--notes-dir", default=generate.DEFAULT_NOTES_DIR)
    args = ap.parse_args(argv)

    base = os.path.dirname(os.path.abspath(args.inbox))
    for path in sorted(glob.glob(os.path.join(args.inbox, "*.eml")), key=os.path.getmtime):
        wait = SETTLE_SECONDS - (time.time() - os.path.getmtime(path))
        if wait > 0:
            time.sleep(wait)
        process(path, args.notes_dir, base)


if __name__ == "__main__":
    main()
