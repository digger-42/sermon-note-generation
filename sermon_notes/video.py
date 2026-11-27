"""Make the next Sunday's Video Description folder from the Template.

Usage:
    python3 -m sermon_notes.video EMAIL [--date YYYY-MM-DD]
        [--video-dir DIR] [--image-inbox DIR]

SermonVideo/<year>/Template is copied to SermonVideo/<year>/YYYY-MM-DD/, the
unused Evening description is deleted, the series image is brought in, and
the Morning description is filled in from Katie's email. The watcher runs
this right after it makes the Sermon Notes.

The image comes from the SermonEmails inbox when a new one is waiting there
(it is copied, then filed in SermonEmails/done so it is not reused as "new"
next week). Otherwise it is moved from the previous Sunday's folder.
"""

import argparse
import datetime
import glob
import os
import re
import shutil
import sys

from .email_parser import parse_email, read_email

DEFAULT_VIDEO_DIR = "/media/dan/MaresLeg/Church/SermonVideo"
DEFAULT_IMAGE_INBOX = "/media/dan/MaresLeg/Church/SermonEmails/inbox"
TEMPLATE = "Template"
MORNING = "Morning-PCCMI-Video-Description.odt"
EVENING = "Evening-PCCMI-Video-Description.odt"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_image(path):
    return os.path.isfile(path) and path.lower().endswith(IMAGE_EXTS)


def images_in(folder):
    if not os.path.isdir(folder):
        return []
    paths = [os.path.join(folder, n) for n in os.listdir(folder)]
    return sorted((p for p in paths if is_image(p)), key=os.path.getmtime)


def previous_week_dir(video_dir, sunday):
    """The newest dated folder before this Sunday, looking back into last year too."""
    found = []
    for year in (sunday.year, sunday.year - 1):
        year_dir = os.path.join(video_dir, str(year))
        if not os.path.isdir(year_dir):
            continue
        for name in os.listdir(year_dir):
            if DATE_DIR.match(name) and name < sunday.isoformat():
                found.append((name, os.path.join(year_dir, name)))
    return max(found)[1] if found else None


def copy_template(template, dest):
    """Copy the Template into dest, keeping anything already there except Morning."""
    if not os.path.isdir(template):
        raise SystemExit("No Template folder at " + template)
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(template):
        src = os.path.join(template, name)
        target = os.path.join(dest, name)
        if os.path.isdir(src):
            if not os.path.exists(target):
                shutil.copytree(src, target)
        elif name == MORNING or not os.path.exists(target):
            # The Morning file is always refilled from a fresh Template copy.
            shutil.copy2(src, target)


def bring_image(dest, previous, image_inbox):
    """Copy a new image from the inbox, else move last week's. Returns the path or None."""
    new = images_in(image_inbox) if image_inbox else []
    if new:
        src = new[-1]
        target = os.path.join(dest, os.path.basename(src))
        shutil.copy2(src, target)
        done = os.path.join(os.path.dirname(os.path.abspath(image_inbox)), "done")
        os.makedirs(done, exist_ok=True)
        for path in new:
            filed = os.path.join(done, os.path.basename(path))
            if os.path.exists(filed):
                stem, ext = os.path.splitext(filed)
                filed = "%s-%d%s" % (stem, int(os.path.getmtime(path)), ext)
            shutil.move(path, filed)
        return target
    existing = images_in(dest)
    if existing:
        return existing[-1]
    if previous:
        old = images_in(previous)
        if old:
            target = os.path.join(dest, os.path.basename(old[-1]))
            shutil.move(old[-1], target)
            return target
    return None


def make(info, sunday, video_dir=DEFAULT_VIDEO_DIR, image_inbox=DEFAULT_IMAGE_INBOX):
    year_dir = os.path.join(video_dir, str(sunday.year))
    dest = os.path.join(year_dir, sunday.isoformat())
    previous = previous_week_dir(video_dir, sunday)
    copy_template(os.path.join(year_dir, TEMPLATE), dest)
    evening = os.path.join(dest, EVENING)
    if os.path.exists(evening):
        os.remove(evening)
    image = bring_image(dest, previous, image_inbox)
    if image is None:
        sys.stderr.write("No series image found for %s\n" % dest)
    morning = os.path.join(dest, MORNING)
    if os.path.exists(morning):
        fill_morning(morning, info, sunday)
    return dest


def fill_morning(path, info, sunday):
    # Filled in once the Template and two finished weeks have been compared.
    pass


def main(argv=None):
    from .generate import upcoming_sunday

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("email", help="email as plain text or a saved .eml file")
    ap.add_argument("--date", help="Sunday date YYYY-MM-DD (default: upcoming Sunday)")
    ap.add_argument("--video-dir", default=os.environ.get("SERMON_VIDEO_DIR",
                                                         DEFAULT_VIDEO_DIR))
    ap.add_argument("--image-inbox", default=os.environ.get("SERMON_IMAGE_INBOX",
                                                           DEFAULT_IMAGE_INBOX))
    args = ap.parse_args(argv)
    with open(args.email, "rb") as f:
        info = parse_email(read_email(f.read()))
    sunday = (datetime.date.fromisoformat(args.date) if args.date
              else upcoming_sunday(datetime.date.today()))
    dest = make(info, sunday, args.video_dir, args.image_inbox)
    print(dest)
    return dest


if __name__ == "__main__":
    main()
