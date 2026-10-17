import os
import unittest
from unittest import mock

from sermon_notes import generate


class FindSofficeTest(unittest.TestCase):
    def test_env_override_wins(self):
        with mock.patch.dict(os.environ, {"SOFFICE": "/custom/soffice"}):
            self.assertEqual(generate.find_soffice(), "/custom/soffice")

    def test_newest_opt_install_when_not_on_path(self):
        installs = ["/opt/libreoffice7.6/program/soffice",
                    "/opt/libreoffice25.10/program/soffice",
                    "/opt/libreoffice25.2/program/soffice"]
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("shutil.which", return_value=None), \
                mock.patch("glob.glob", return_value=list(installs)), \
                mock.patch("os.access", side_effect=lambda p, m: p in installs):
            self.assertEqual(generate.find_soffice(), "/opt/libreoffice25.10/program/soffice")

    def test_none_found(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch("shutil.which", return_value=None), \
                mock.patch("glob.glob", return_value=[]), \
                mock.patch("os.access", return_value=False):
            self.assertIsNone(generate.find_soffice())


if __name__ == "__main__":
    unittest.main()
