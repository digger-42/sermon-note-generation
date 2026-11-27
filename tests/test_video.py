import datetime
import os
import tempfile
import time
import unittest

from sermon_notes import video
from sermon_notes.email_parser import SermonInfo

SUNDAY = datetime.date(2026, 11, 29)


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
        for name in (video.MORNING, video.EVENING, "notes.txt"):
            self.write(os.path.join(template, name), "template " + name)
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
        self.write(os.path.join(dest, video.MORNING), "edited")
        self.write(os.path.join(dest, "notes.txt"), "edited")
        self.make()
        with open(os.path.join(dest, "notes.txt")) as f:
            self.assertEqual(f.read(), "edited")
        self.assertIn("series.png", os.listdir(dest))
        self.assertNotIn(video.EVENING, os.listdir(dest))

    def test_previous_week_from_last_year(self):
        os.makedirs(os.path.join(self.video_dir, "2025", "2025-12-28"))
        prev = video.previous_week_dir(self.video_dir, datetime.date(2026, 1, 4))
        self.assertTrue(prev.endswith("2025-12-28"))

    def test_missing_template(self):
        with self.assertRaises(SystemExit):
            video.make(self.info, datetime.date(2027, 1, 3), self.video_dir, self.inbox)


if __name__ == "__main__":
    unittest.main()
