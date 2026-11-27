"""Make Sermon Notes for every email Thunderbird saved into an inbox folder.

Usage:
    python3 -m sermon_notes.inbox [--inbox DIR] [--notes-dir DIR] [--latest]

Each .eml file in the inbox is turned into the upcoming Sunday's notes, then
moved to a "done" folder beside the inbox, or to "failed" with a .log of what
went wrong. Run it by hand, or let the systemd units in contrib/ run it
whenever a new file lands in the inbox.

--latest instead (re)processes only the newest .eml found in the inbox, done
or failed folders, for when the watcher missed an email or choked on it.
"""

import argparse
import datetime
import glob
import os
import shutil
import subprocess
import time
import traceback

from . import gdrive, generate, video
from .email_parser import parse_email, read_email

DEFAULT_INBOX = "/MaresLeg/Church/SermonEmails/inbox"
# Leave files alone until Thunderbird has finished writing them.
SETTLE_SECONDS = 3


def notify(summary, body=""):
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "Sermon Notes", summary + "\n" + body])


def move(path, folder):
    if os.path.abspath(os.path.dirname(path)) == os.path.abspath(folder):
        return path
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
    pdf = os.path.splitext(odt)[0] + ".pdf"
    notify("Notes are ready", pdf)
    publish_notes(path, pdf, base)
    make_video(path, odt, base)
    move(path, os.path.join(base, "done"))
    return True


def make_video(path, odt, base):
    """Make the Video Description folder for the same Sunday as the notes."""
    try:
        sunday = datetime.date.fromisoformat(os.path.basename(odt)[:10])
        with open(path, "rb") as f:
            info = parse_email(read_email(f.read()))
        dest = video.make(info, sunday,
                          os.environ.get("SERMON_VIDEO_DIR", video.DEFAULT_VIDEO_DIR),
                          os.path.join(base, "inbox"))
    except (Exception, SystemExit) as err:
        log_failure(path, base, "video", err)
        notify("Could not make the Video Description", str(err))
        return None
    notify("Video Description is ready", dest)
    publish_video(path, dest, base)
    return dest


def publish_notes(path, pdf, base):
    """Copy the notes PDF over the one the website links to on Google Drive."""
    try:
        target = gdrive.publish_notes(pdf, os.environ.get("SERMON_GDRIVE_NOTES_PDF",
                                                          gdrive.DEFAULT_NOTES_PDF))
    except (Exception, SystemExit) as err:
        log_failure(path, base, "notes-gdrive", err)
        notify("Could not publish the Sermon Notes to Google Drive", str(err))
        return None
    notify("Sermon Notes are on Google Drive", target)
    return target


def publish_video(path, folder, base):
    """Copy the new Video Description folder to the Google Drive."""
    try:
        target = gdrive.publish(folder, os.environ.get("SERMON_GDRIVE_DOCUMENTS",
                                                       gdrive.DEFAULT_DOCUMENTS))
    except (Exception, SystemExit) as err:
        log_failure(path, base, "gdrive", err)
        notify("Could not publish the Video Description to Google Drive", str(err))
        return None
    notify("Video Description is on Google Drive", target)
    return target


def log_failure(path, base, step, err):
    log = os.path.join(base, "failed", "%s.%s.log" % (os.path.basename(path), step))
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w") as f:
        f.write("".join(traceback.format_exception(err)))


def latest_email(base):
    """The most recently saved .eml in the inbox, done or failed folder."""
    paths = []
    for folder in ("inbox", "done", "failed"):
        paths += glob.glob(os.path.join(base, folder, "*.eml"))
    return max(paths, key=os.path.getmtime, default=None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--inbox", default=DEFAULT_INBOX)
    ap.add_argument("--notes-dir", default=generate.DEFAULT_NOTES_DIR)
    ap.add_argument("--latest", action="store_true",
                    help="(re)process only the newest email in inbox, done or failed")
    args = ap.parse_args(argv)

    base = os.path.dirname(os.path.abspath(args.inbox))
    if args.latest:
        path = latest_email(base)
        if path is None:
            raise SystemExit("No saved emails found under %s" % base)
        print("Processing", path)
        ok = process(path, args.notes_dir, base)
        print("Notes are ready." if ok else "Failed: see the .log beside it in %s"
              % os.path.join(base, "failed"))
        return 0 if ok else 1
    for path in sorted(glob.glob(os.path.join(args.inbox, "*.eml")), key=os.path.getmtime):
        wait = SETTLE_SECONDS - (time.time() - os.path.getmtime(path))
        if wait > 0:
            time.sleep(wait)
        process(path, args.notes_dir, base)


if __name__ == "__main__":
    raise SystemExit(main())
