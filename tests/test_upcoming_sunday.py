import argparse
import datetime
import os
import tempfile
import unittest
import unittest.mock as mock

from sermon_notes import generate
from sermon_notes.email_parser import SermonInfo
from sermon_notes.generate import upcoming_sunday


class FakeDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2026, 12, 31)


class UpcomingSundayTest(unittest.TestCase):
    def test_weekdays_get_this_coming_sunday(self):
        for day in range(23, 29):  # Monday 2026-11-23 to Saturday 2026-11-28
            self.assertEqual(upcoming_sunday(datetime.date(2026, 11, day)),
                             datetime.date(2026, 11, 29))

    def test_sunday_rolls_to_the_next_one(self):
        self.assertEqual(upcoming_sunday(datetime.date(2026, 11, 29)),
                         datetime.date(2026, 12, 6))


    def test_new_years_eve_email_goes_in_next_years_folder(self):
        self.assertEqual(upcoming_sunday(datetime.date(2026, 12, 31)),
                         datetime.date(2027, 1, 3))
        info = SermonInfo("Steve", "Series", "Title", "John 1:1", ["Words."])
        with tempfile.TemporaryDirectory() as notes, \
                mock.patch.object(generate.datetime, "date", FakeDate), \
                mock.patch.object(generate, "find_qr", return_value=b""), \
                mock.patch.object(generate, "write_odt") as write, \
                mock.patch("builtins.print"):
            args = argparse.Namespace(date=None, notes_dir=notes, suffix=None, no_pdf=True)
            odt = generate.generate(info, args)
            self.assertEqual(odt, os.path.join(notes, "2027", "2027-01-03-sermon-notes.odt"))
        self.assertEqual(write.call_args[0][2], "Steve Higgs, January 3, 2027")


if __name__ == "__main__":
    unittest.main()
