import unittest

from sermon_notes.email_parser import parse_email, read_email

BODY = """Good Morning,

Here is the sermon information for Steve's message Sunday morning:

Series: How the West Will Be Won
Title: The Many Ways That Jesus Saves
Scripture: Romans 5, Hebrews 9, 2 Corinthians 4

Description: In this message, we will explore the many ways that Jesus saves.

We'll take a deeper look at justification, sanctification, and glorification.
"""
# The signature separator is "-- " with a trailing space.
SIGNATURE = "\n-- \n" + """Katie Winstanley

Rooted.
"Therefore, as you received Christ Jesus the Lord, so walk in him." Colossians 2:6-7
"""
EXPECTED_DESCRIPTION = [
    "In this message, we will explore the many ways that Jesus saves.",
    "We'll take a deeper look at justification, sanctification, and glorification.",
]


class ParseEmailTest(unittest.TestCase):
    def check(self, text):
        info = parse_email(text)
        self.assertEqual(info.speaker, "Steve")
        self.assertEqual(info.series, "How the West Will Be Won")
        self.assertEqual(info.title, "The Many Ways That Jesus Saves")
        self.assertEqual(info.scripture, "Romans 5, Hebrews 9, 2 Corinthians 4")
        self.assertEqual(info.description, EXPECTED_DESCRIPTION)

    def test_with_signature(self):
        self.check(BODY + SIGNATURE)

    def test_without_signature(self):
        self.check(BODY)

    def test_signature_without_separator(self):
        self.check(BODY + SIGNATURE.replace("-- \n", ""))

    def test_missing_field(self):
        with self.assertRaises(ValueError):
            parse_email(BODY.replace("Title:", "Topic:"))


class ReadEmailTest(unittest.TestCase):
    def test_plain_text_paste(self):
        self.assertEqual(read_email(BODY.encode()), BODY)

    def test_saved_plain_message(self):
        eml = ("From: Katie Winstanley <worship@pccmi.org>\n"
               "Subject: Sunday Morning Sermon Information\n"
               "Content-Type: text/plain; charset=utf-8\n"
               "Content-Transfer-Encoding: quoted-printable\n\n"
               + BODY.replace("=", "=3D") + SIGNATURE)
        self.assertEqual(parse_email(read_email(eml.encode())).title,
                         "The Many Ways That Jesus Saves")

    def test_saved_html_message(self):
        html = BODY.replace("Steve's", "Steve&#8217;s").replace("\n", "<br>\n")
        eml = ("From: worship@pccmi.org\nSubject: Sunday Morning Sermon Information\n"
               "Content-Type: text/html; charset=utf-8\n\n<div>%s</div>" % html)
        info = parse_email(read_email(eml.encode()))
        self.assertEqual(info.speaker, "Steve")
        self.assertEqual(info.description, EXPECTED_DESCRIPTION)


if __name__ == "__main__":
    unittest.main()
