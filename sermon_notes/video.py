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
import os
import re
import shutil
import sys
import zipfile
from xml.sax.saxutils import escape

from .email_parser import parse_email, read_email

DEFAULT_VIDEO_DIR = "/MaresLeg/Church/SermonVideo"
DEFAULT_IMAGE_INBOX = "/MaresLeg/Church/SermonEmails/inbox"
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


def year_template(video_dir, year):
    """This year's Template folder, started from last year's on the first Sunday of a year."""
    template = os.path.join(video_dir, str(year), TEMPLATE)
    if not os.path.isdir(template):
        last = os.path.join(video_dir, str(year - 1), TEMPLATE)
        if os.path.isdir(last):
            shutil.copytree(last, template)
    return template


def make(info, sunday, video_dir=DEFAULT_VIDEO_DIR, image_inbox=DEFAULT_IMAGE_INBOX):
    year_dir = os.path.join(video_dir, str(sunday.year))
    dest = os.path.join(year_dir, sunday.isoformat())
    previous = previous_week_dir(video_dir, sunday)
    copy_template(year_template(video_dir, sunday.year), dest)
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


CONNECT_URL = "https://pccmi.breezechms.com/form/ce988b"
# Styles added to the Template's own: single-spaced Notes paragraphs, centered
# ones for the Connect Card block, and LibreOffice's standard link style for its two links.
EXTRA_STYLES = (
    '<style:style style:name="VDCenter" style:family="paragraph" '
    'style:parent-style-name="Standard"><style:paragraph-properties fo:margin-left="0in" '
    'fo:text-align="center" style:justify-single-word="false" fo:text-indent="0in" '
    'style:auto-text-indent="false"/><style:text-properties '
    'style:font-name="AvenirNext LT Pro Regular" fo:font-size="12pt" '
    'style:font-size-asian="12pt" style:font-size-complex="12pt"/></style:style>'
    '<style:style style:name="VDBody" style:family="paragraph" '
    'style:parent-style-name="Standard"><style:paragraph-properties fo:margin-top="0in" '
    'fo:margin-bottom="0in" style:contextual-spacing="false" fo:text-align="start"/>'
    '<style:text-properties style:font-name="AvenirNext LT Pro Regular" fo:font-size="12pt" '
    'style:font-size-asian="12pt" style:font-size-complex="12pt"/></style:style>'
)
LINK_STYLE = (
    '<style:style style:name="Internet_20_link" style:display-name="Internet link" '
    'style:family="text"><style:text-properties fo:color="#000080" '
    'style:text-underline-style="solid" style:text-underline-width="auto" '
    'style:text-underline-color="font-color"/></style:style>'
)


def _link(text):
    return ('<text:a xlink:type="simple" xlink:href="%s" text:style-name="Internet_20_link">'
            '%s</text:a>' % (CONNECT_URL, text))


def _p(style, inner=""):
    return '<text:p text:style-name="%s">%s</text:p>' % (style, inner)


def _replace_one(pattern, repl, text, what):
    new, n = re.subn(pattern, lambda m: repl, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("The Morning Template no longer has its %s line" % what)
    return new


def fill_content(xml, info, sunday):
    """Fill the Template's content.xml the way the finished weeks are filled in."""
    heading = "%s: %s" % (info.series, info.title) if info.series else info.title
    title = _p("P1", '<text:span text:style-name="T1">PCCMI </text:span>'
                     '<text:span text:style-name="T2">Morning Worship</text:span>'
                     '<text:span text:style-name="T1">: %s: </text:span>'
                     '<text:span text:style-name="T8">%s</text:span>'
               % (sunday.strftime("%m/%d/%Y"), escape(heading)))
    xml = _replace_one(r'<text:p text:style-name="P1">.*?</text:p>', title, xml, "title")

    refs = "".join(_p("P10", escape(r)) for r in (info.scriptures or [info.scripture]))
    xml = _replace_one(r'<text:p text:style-name="P10">.*?</text:p>', refs, xml, "scripture")

    notes = "".join(_p("VDBody", escape(d)) for d in info.description)
    notes += _p("VDBody")
    notes += _p("VDCenter", "One of the ways you can take your next step in faith")
    notes += _p("VDCenter", "is by filling out the Connect Card.")
    notes += _p("VDCenter", _link("Click the link") + " and let us know how we can help:")
    notes += _p("VDBody")
    notes += _p("VDCenter", _link(CONNECT_URL))
    notes += _p("VDBody")
    # Everything after the "Notes:" heading is the Template's empty lines.
    xml = _replace_one(r'(?<=otes:</text:span></text:p>).*?(?=</office:text>)', notes, xml,
                       "Notes")
    return xml.replace("</office:automatic-styles>", EXTRA_STYLES + "</office:automatic-styles>")


def fill_styles(xml):
    if 'style:name="Internet_20_link"' in xml:
        return xml
    return xml.replace("</office:styles>", LINK_STYLE + "</office:styles>", 1)


def fill_morning(path, info, sunday):
    with zipfile.ZipFile(path) as z:
        entries = [(i, z.read(i)) for i in z.infolist()]
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w") as out:
        for item, data in entries:
            if item.filename == "content.xml":
                data = fill_content(data.decode("utf-8"), info, sunday).encode("utf-8")
            elif item.filename == "styles.xml":
                data = fill_styles(data.decode("utf-8")).encode("utf-8")
            # mimetype must stay first and uncompressed; the rest are deflated.
            kind = zipfile.ZIP_STORED if item.filename == "mimetype" else zipfile.ZIP_DEFLATED
            out.writestr(item.filename, data, compress_type=kind)
    os.replace(tmp, path)


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
