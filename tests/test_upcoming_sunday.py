import datetime
import unittest

from sermon_notes.generate import upcoming_sunday


class UpcomingSundayTest(unittest.TestCase):
    def test_weekdays_get_this_coming_sunday(self):
        for day in range(23, 29):  # Monday 2026-11-23 to Saturday 2026-11-28
            self.assertEqual(upcoming_sunday(datetime.date(2026, 11, day)),
                             datetime.date(2026, 11, 29))

    def test_sunday_rolls_to_the_next_one(self):
        self.assertEqual(upcoming_sunday(datetime.date(2026, 11, 29)),
                         datetime.date(2026, 12, 6))


if __name__ == "__main__":
    unittest.main()
