"""Generate the Sunday Sermon Notes (.odt and .pdf) from Katie's email.

Usage:
    python3 -m sermon_notes.generate EMAIL.txt [--date YYYY-MM-DD]
        [--notes-dir DIR] [--suffix NAME] [--no-pdf]
"""

import argparse
import datetime
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from .email_parser import parse_email
from .odt_writer import FONT, write_odt

DEFAULT_NOTES_DIR = "/mnt/project-files/SermonNotes"
# SHA-256 of the Connect Card QR code used in every 2026 notes file. The image
# is copied from a past notes file and refused if it does not match exactly.
QR_SHA256 = "82f73a27079c4ca38c98a5a397e3e507c58914b2cdc627e79c0eeb0615667455"
# fontconfig family name of the brand font (the .odt names it as FONT).
FONT_FAMILY = "AvenirNext LT Pro"
SPEAKERS = os.path.join(os.path.dirname(__file__), "speakers.json")


def upcoming_sunday(today):
    # Notes are always for the next Sunday; on a Sunday that is today.
    return today + datetime.timedelta(days=(6 - today.weekday()) % 7)


def full_speaker_name(name):
    with open(SPEAKERS) as f:
        names = json.load(f)
    return names.get(name, name)


def find_qr(notes_dir):
    files = sorted(glob.glob(os.path.join(notes_dir, "*", "*.odt")), reverse=True)
    for path in files:
        try:
            with zipfile.ZipFile(path) as z:
                for entry in z.namelist():
                    if entry.startswith("Pictures/"):
                        data = z.read(entry)
                        if hashlib.sha256(data).hexdigest() == QR_SHA256:
                            return data
        except zipfile.BadZipFile:
            continue
    raise SystemExit("Could not find the original QR code in " + notes_dir)


def font_installed():
    try:
        out = subprocess.run(["fc-list", ":family"], capture_output=True,
                             text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return False
    return FONT_FAMILY in out


def convert_to_pdf(odt_path):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit("LibreOffice (soffice) is needed to make the PDF")
    outdir = os.path.dirname(odt_path)
    # A private profile lets this run even while LibreOffice is open elsewhere.
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [soffice, "-env:UserInstallation=file://" + profile, "--headless",
             "--convert-to", "pdf", "--outdir", outdir, odt_path],
            check=True, stdout=subprocess.DEVNULL)
    return os.path.splitext(odt_path)[0] + ".pdf"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("email", help="email text file, or - for stdin")
    ap.add_argument("--date", help="Sunday date YYYY-MM-DD (default: upcoming Sunday)")
    ap.add_argument("--notes-dir", default=DEFAULT_NOTES_DIR)
    ap.add_argument("--suffix", help="added to the file name, e.g. ToddJones")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--allow-font-substitution", action="store_true",
                    help="make a PDF even if %s is not installed" % FONT)
    args = ap.parse_args(argv)

    text = sys.stdin.read() if args.email == "-" else open(args.email).read()
    info = parse_email(text)

    if args.date:
        sunday = datetime.date.fromisoformat(args.date)
    else:
        sunday = upcoming_sunday(datetime.date.today())
    speaker = full_speaker_name(info.speaker)
    when = "%s %d, %d" % (sunday.strftime("%B"), sunday.day, sunday.year)
    speaker_line = "%s, %s" % (speaker, when) if speaker else when

    year_dir = os.path.join(args.notes_dir, str(sunday.year))
    os.makedirs(year_dir, exist_ok=True)
    name = "%s-sermon-notes" % sunday.isoformat()
    if args.suffix:
        name += "-" + args.suffix
    odt_path = os.path.join(year_dir, name + ".odt")

    write_odt(odt_path, info, speaker_line, find_qr(args.notes_dir))
    print(odt_path)
    if args.no_pdf:
        return
    if not font_installed() and not args.allow_font_substitution:
        raise SystemExit("%s is not installed, so the PDF would use the wrong "
                         "font. Install it and run again." % FONT)
    print(convert_to_pdf(odt_path))


if __name__ == "__main__":
    main()
