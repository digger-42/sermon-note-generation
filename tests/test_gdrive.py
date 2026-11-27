import os
import tempfile
import unittest
import unittest.mock as mock

from sermon_notes import gdrive


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.drive = os.path.join(root, "google_drive")
        self.documents = os.path.join(self.drive, "Video Design Assets", "Documents")
        self.folder = os.path.join(root, "SermonVideo", "2026", "2026-11-29")
        os.makedirs(os.path.join(self.folder, "sub"))
        for name in ("Morning-PCCMI-Video-Description.odt", "series.png", "sub/x.txt"):
            with open(os.path.join(self.folder, name), "w") as f:
                f.write(name)
        self.mount = os.path.join(root, "mount-google-drive")

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self):
        return gdrive.publish(self.folder, self.documents, drive=self.drive,
                              mount_script=self.mount, wait=0)

    def test_replaces_old_week_and_keeps_other_files(self):
        for name in ("2026-11-22", "2026-11-15", "Logos", "2026-12-06"):
            os.makedirs(os.path.join(self.documents, name))
        with open(os.path.join(self.documents, "notes.txt"), "w") as f:
            f.write("keep")
        target = self.publish()
        self.assertEqual(target, os.path.join(self.documents, "2026-11-29"))
        self.assertEqual(sorted(os.listdir(self.documents)),
                         ["2026-11-29", "2026-12-06", "Logos", "notes.txt"])
        self.assertEqual(sorted(os.listdir(target)),
                         ["Morning-PCCMI-Video-Description.odt", "series.png", "sub"])
        self.assertTrue(os.path.exists(os.path.join(target, "sub", "x.txt")))

    def test_rerun_replaces_same_week(self):
        os.makedirs(os.path.join(self.documents, "2026-11-29"))
        stale = os.path.join(self.documents, "2026-11-29", "stale.txt")
        with open(stale, "w") as f:
            f.write("old")
        self.publish()
        self.assertFalse(os.path.exists(stale))

    def test_mounts_empty_drive(self):
        os.makedirs(self.drive)
        with open(self.mount, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(self.mount, 0o700)

        def mount(cmd, check):
            os.makedirs(self.documents)
        with mock.patch.object(gdrive.subprocess, "run", side_effect=mount) as run:
            self.publish()
        run.assert_called_once_with([self.mount], check=True)
        self.assertIn("2026-11-29", os.listdir(self.documents))

    def test_no_mount_script(self):
        with self.assertRaises(SystemExit):
            self.publish()

    def test_mounted_drive_without_documents(self):
        os.makedirs(os.path.join(self.drive, "Other"))
        with self.assertRaises(SystemExit):
            self.publish()

    def test_refuses_undated_folder(self):
        with self.assertRaises(SystemExit):
            gdrive.publish(os.path.dirname(self.folder), self.documents)


class PublishNotesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.drive = os.path.join(root, "google_drive")
        self.dest = os.path.join(self.drive, "Sermon Notes", "pcc-sermon-notes.pdf")
        self.pdf = os.path.join(root, "2026-11-29-sermon-notes.pdf")
        with open(self.pdf, "wb") as f:
            f.write(b"%PDF new week")

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self):
        return gdrive.publish_notes(self.pdf, self.dest, drive=self.drive,
                                    mount_script=os.path.join(self.tmp.name, "none"), wait=0)

    def test_overwrites_same_file_in_place(self):
        os.makedirs(os.path.dirname(self.dest))
        with open(self.dest, "wb") as f:
            f.write(b"%PDF last week, which was longer")
        inode = os.stat(self.dest).st_ino
        self.assertEqual(self.publish(), self.dest)
        with open(self.dest, "rb") as f:
            self.assertEqual(f.read(), b"%PDF new week")
        self.assertEqual(os.stat(self.dest).st_ino, inode)
        self.assertEqual(os.listdir(os.path.dirname(self.dest)), ["pcc-sermon-notes.pdf"])

    def test_creates_file_when_missing(self):
        os.makedirs(os.path.dirname(self.dest))
        self.publish()
        self.assertTrue(os.path.exists(self.dest))

    def test_missing_pdf(self):
        os.remove(self.pdf)
        with self.assertRaises(SystemExit):
            self.publish()

    def test_drive_not_mounted(self):
        with self.assertRaises(SystemExit):
            self.publish()


if __name__ == "__main__":
    unittest.main()
