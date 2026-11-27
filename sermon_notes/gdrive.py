"""Publish the Sunday's Video Description folder and Sermon Notes to Google Drive.

Usage:
    python3 -m sermon_notes.gdrive VIDEO_FOLDER [--documents DIR]
    python3 -m sermon_notes.gdrive NOTES.pdf [--notes-pdf FILE]

The Google Drive is mapped at $HOME/google_drive. If it is empty it is mounted
with $HOME/bin/mount-google-drive first. Then any earlier dated folder under
"Video Design Assets/Documents" is removed, and VIDEO_FOLDER (for example
SermonVideo/2026/2026-11-29) is copied there whole, where the church's video
computer picks it up. The watcher runs this right after it makes the folder.

A Sermon Notes PDF is copied over "Sermon Notes/pcc-sermon-notes.pdf" in
place, so the Drive file and the website's link to it stay the same.
"""

import argparse
import os
import re
import shutil
import subprocess
import time

DRIVE = os.path.join(os.path.expanduser("~"), "google_drive")
DEFAULT_DOCUMENTS = os.path.join(DRIVE, "Video Design Assets", "Documents")
DEFAULT_NOTES_PDF = os.path.join(DRIVE, "Sermon Notes", "pcc-sermon-notes.pdf")
MOUNT_SCRIPT = os.path.join(os.path.expanduser("~"), "bin", "mount-google-drive")
# How long to wait for the drive's files to show up after mounting it.
MOUNT_WAIT_SECONDS = 60
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def ensure_mounted(needed, drive=DRIVE, mount_script=MOUNT_SCRIPT,
                   wait=MOUNT_WAIT_SECONDS):
    """Mount the Google Drive when its folder is empty, then wait for the needed folder."""
    if os.path.isdir(needed):
        return
    if not (os.path.isdir(drive) and os.listdir(drive)):
        if not os.access(mount_script, os.X_OK):
            raise SystemExit("Google Drive is not mounted and %s was not found" % mount_script)
        subprocess.run([mount_script], check=True)
    deadline = time.monotonic() + wait
    while not os.path.isdir(needed):
        if time.monotonic() >= deadline:
            raise SystemExit("Google Drive folder did not appear: " + needed)
        time.sleep(2)


def publish(folder, documents=DEFAULT_DOCUMENTS, **mount_args):
    """Replace the earlier week's dated folder in Documents with this one."""
    folder = os.path.abspath(folder)
    name = os.path.basename(folder)
    if not DATE_DIR.match(name):
        raise SystemExit("Not a dated Video Description folder: " + folder)
    ensure_mounted(documents, **mount_args)
    for old in os.listdir(documents):
        path = os.path.join(documents, old)
        # Only dated folders up to this Sunday; anything else on the drive stays.
        if DATE_DIR.match(old) and old <= name and os.path.isdir(path):
            shutil.rmtree(path)
    target = os.path.join(documents, name)
    shutil.copytree(folder, target)
    return target


def publish_notes(pdf, dest=DEFAULT_NOTES_PDF, **mount_args):
    """Overwrite the Drive's Sermon Notes PDF with this week's."""
    if not os.path.isfile(pdf):
        raise SystemExit("No Sermon Notes PDF at " + pdf)
    ensure_mounted(os.path.dirname(dest), **mount_args)
    # copyfile rewrites the existing file rather than replacing it, so Google
    # Drive keeps the same file (and share link) with new contents.
    shutil.copyfile(pdf, dest)
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="a dated SermonVideo folder, or a Sermon Notes .pdf")
    ap.add_argument("--documents", default=os.environ.get("SERMON_GDRIVE_DOCUMENTS",
                                                         DEFAULT_DOCUMENTS))
    ap.add_argument("--notes-pdf", default=os.environ.get("SERMON_GDRIVE_NOTES_PDF",
                                                         DEFAULT_NOTES_PDF))
    args = ap.parse_args(argv)
    if args.path.lower().endswith(".pdf"):
        print(publish_notes(args.path, args.notes_pdf))
    else:
        print(publish(args.path, args.documents))


if __name__ == "__main__":
    main()
