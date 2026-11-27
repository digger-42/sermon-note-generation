import datetime
import os
import re
import tempfile
import time
import unittest
import zipfile

from sermon_notes import video
from sermon_notes.email_parser import SermonInfo, parse_email

SUNDAY = datetime.date(2026, 11, 29)

# The parts of the real Morning Template that get filled in.
CONTENT = (
    '<office:document-content><office:automatic-styles></office:automatic-styles>'
    '<office:body><office:text>'
    '<text:p text:style-name="P1"><text:span text:style-name="T3">MM</text:span>/DD/2026: '
    '[Optional Series:] Title</text:p>'
    '<text:p text:style-name="P5">Worship Leader: Katie Winstanley</text:p>'
    '<text:p text:style-name="P9">S<text:span text:style-name="T11">cripture:</text:span></text:p>'
    '<text:p text:style-name="P10"><text:span text:style-name="T8">OOK CC:VV-VV</text:span>'
    '</text:p><text:p text:style-name="P7"/>'
    '<text:p text:style-name="P11">N<text:span text:style-name="T11">otes:</text:span></text:p>'
    '<text:p text:style-name="P12"/><text:p text:style-name="P13"/>'
    '</office:text></office:body></office:document-content>'
)
STYLES = "<office:document-styles><office:styles></office:styles></office:document-styles>"


def write_template_odt(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("content.xml", CONTENT)
        z.writestr("styles.xml", STYLES)


def body_text(path):
    """The document's paragraphs, one per line."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("content.xml").decode()
    xml = re.sub(r"</text:p>|<text:p [^>]*/>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


class VideoFolderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.video_dir = os.path.join(root, "SermonVideo")
        self.inbox = os.path.join(root, "SermonEmails", "inbox")
        os.makedirs(self.inbox)
        self.year = os.path.join(self.video_dir, "2026")
        template = os.path.join(self.year, "Template")
        os.makedirs(template)
        for name in (video.EVENING, "notes.txt"):
            self.write(os.path.join(template, name), "template " + name)
        write_template_odt(os.path.join(template, video.MORNING))
        self.last = os.path.join(self.year, "2026-11-22")
        os.makedirs(self.last)
        self.write(os.path.join(self.last, "series.png"), "old image")
        os.makedirs(os.path.join(self.year, "2026-11-15"))
        self.info = SermonInfo("Steve", "Series", "Title", "John 1:1", ["Words."])

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text, age=0):
        with open(path, "w") as f:
            f.write(text)
        t = time.time() - age
        os.utime(path, (t, t))
        return path

    def make(self):
        return video.make(self.info, SUNDAY, self.video_dir, self.inbox)

    def test_copies_template_and_drops_evening(self):
        dest = self.make()
        self.assertEqual(dest, os.path.join(self.year, "2026-11-29"))
        names = sorted(os.listdir(dest))
        self.assertEqual(names, sorted([video.MORNING, "notes.txt", "series.png"]))

    def test_moves_image_from_previous_sunday(self):
        dest = self.make()
        self.assertFalse(os.path.exists(os.path.join(self.last, "series.png")))
        with open(os.path.join(dest, "series.png")) as f:
            self.assertEqual(f.read(), "old image")

    def test_new_inbox_image_is_copied_and_filed(self):
        self.write(os.path.join(self.inbox, "older.jpg"), "older", age=60)
        self.write(os.path.join(self.inbox, "new-series.jpg"), "new")
        self.write(os.path.join(self.inbox, "week.eml"), "email")
        dest = self.make()
        self.assertIn("new-series.jpg", os.listdir(dest))
        self.assertNotIn("series.png", os.listdir(dest))
        # Last week's folder keeps its image, the email is left for the watcher.
        self.assertTrue(os.path.exists(os.path.join(self.last, "series.png")))
        self.assertEqual(os.listdir(self.inbox), ["week.eml"])
        done = os.path.join(os.path.dirname(self.inbox), "done")
        self.assertEqual(sorted(os.listdir(done)), ["new-series.jpg", "older.jpg"])

    def test_rerun_keeps_image_and_refreshes_morning(self):
        dest = self.make()
        self.write(os.path.join(dest, "notes.txt"), "edited")
        self.info.title = "Second Try"
        self.make()
        self.assertIn("Series: Second Try", body_text(os.path.join(dest, video.MORNING)))
        with open(os.path.join(dest, "notes.txt")) as f:
            self.assertEqual(f.read(), "edited")
        self.assertIn("series.png", os.listdir(dest))
        self.assertNotIn(video.EVENING, os.listdir(dest))

    def test_previous_week_from_last_year(self):
        os.makedirs(os.path.join(self.video_dir, "2025", "2025-12-28"))
        prev = video.previous_week_dir(self.video_dir, datetime.date(2026, 1, 4))
        self.assertTrue(prev.endswith("2025-12-28"))

    def test_new_year(self):
        # An email on Thursday 2026-12-31 is for Sunday 2027-01-03.
        from sermon_notes.generate import upcoming_sunday
        sunday = upcoming_sunday(datetime.date(2026, 12, 31))
        self.assertEqual(sunday, datetime.date(2027, 1, 3))
        os.rename(self.last, os.path.join(self.year, "2026-12-27"))
        dest = video.make(self.info, sunday, self.video_dir, self.inbox)
        self.assertEqual(dest, os.path.join(self.video_dir, "2027", "2027-01-03"))
        self.assertEqual(sorted(os.listdir(dest)),
                         sorted([video.MORNING, "notes.txt", "series.png"]))
        self.assertIn("Worship: 01/03/2027: Series: Title\n",
                      body_text(os.path.join(dest, video.MORNING)))
        # 2027 gets its own Template, copied from 2026's, which is left as it was.
        self.assertIn(video.EVENING, os.listdir(os.path.join(self.video_dir, "2027", "Template")))
        self.assertIn(video.EVENING, os.listdir(os.path.join(self.year, "Template")))

    def test_missing_template(self):
        with self.assertRaises(SystemExit):
            video.make(self.info, datetime.date(2028, 1, 2), self.video_dir, self.inbox)


class FillMorningTest(unittest.TestCase):
    def fill(self, email):
        info = parse_email(email) if isinstance(email, str) else email
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, video.MORNING)
            write_template_odt(path)
            video.fill_morning(path, info, datetime.date(2026, 11, 15))
            with zipfile.ZipFile(path) as z:
                self.assertEqual(z.namelist()[0], "mimetype")
                self.assertEqual(z.getinfo("mimetype").compress_type, zipfile.ZIP_STORED)
                self.assertIn("Internet_20_link", z.read("styles.xml").decode())
            return body_text(path)

    def test_fills_like_the_finished_weeks(self):
        text = self.fill(
            "Here is the info for Steve's message.\n"
            "Series: The Thanksgiving Table\nTitle: Keep Watch\n"
            "Scripture: 2 Corinthians 11:23-28; 1 Timothy 1:12-17\nColossians 4:2\n"
            "Description: To maintain thanksgiving requires diligence & watchfulness.\n\n"
            "Second paragraph.\n")
        self.assertIn("PCCMI Morning Worship: 11/15/2026: "
                      "The Thanksgiving Table: Keep Watch\n", text)
        self.assertIn("\n2 Corinthians 11:23-28\n1 Timothy 1:12-17\nColossians 4:2\n", text)
        self.assertNotIn("OOK CC:VV", text)
        self.assertIn("\nTo maintain thanksgiving requires diligence &amp; watchfulness.\n"
                      "Second paragraph.\n\n", text)
        self.assertIn("One of the ways you can take your next step in faith", text)
        self.assertIn("\nClick the link and let us know how we can help:\n\n%s\n"
                      % video.CONNECT_URL, text)
        self.assertIn("Worship Leader: Katie Winstanley", text)

    def test_no_series(self):
        text = self.fill(SermonInfo("", "", "Just A Title", "John 1:1", ["Words."]))
        self.assertIn("Worship: 11/15/2026: Just A Title\n", text)
        self.assertIn("\nJohn 1:1\n", text)


if __name__ == "__main__":
    unittest.main()
