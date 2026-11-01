import os
import tempfile
import time
import unittest
from unittest import mock

from sermon_notes import inbox


class LatestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        for folder in ("inbox", "done", "failed"):
            os.makedirs(os.path.join(self.base, folder))

    def tearDown(self):
        self.tmp.cleanup()

    def save(self, folder, name, age):
        path = os.path.join(self.base, folder, name)
        with open(path, "w") as f:
            f.write("x")
        t = time.time() - age
        os.utime(path, (t, t))
        return path

    def run_latest(self, result="/notes/x.odt"):
        with mock.patch.object(inbox.generate, "main", return_value=result) as gen, \
                mock.patch.object(inbox, "notify"), mock.patch("builtins.print"):
            code = inbox.main(["--inbox", os.path.join(self.base, "inbox"),
                               "--notes-dir", "/notes", "--latest"])
        return code, gen

    def test_picks_newest_across_folders(self):
        self.save("done", "old.eml", 3600)
        newest = self.save("failed", "new.eml", 60)
        self.save("failed", "new.eml.log", 0)
        code, gen = self.run_latest()
        self.assertEqual(code, 0)
        gen.assert_called_once_with([newest, "--notes-dir", "/notes"])
        self.assertTrue(os.path.exists(os.path.join(self.base, "done", "new.eml")))

    def test_reprocessing_done_email_leaves_it_in_place(self):
        path = self.save("done", "week.eml", 60)
        code, _ = self.run_latest()
        self.assertEqual(code, 0)
        self.assertEqual(os.listdir(os.path.join(self.base, "done")), ["week.eml"])
        self.assertTrue(os.path.exists(path))

    def test_no_emails(self):
        with self.assertRaises(SystemExit):
            self.run_latest()


if __name__ == "__main__":
    unittest.main()
