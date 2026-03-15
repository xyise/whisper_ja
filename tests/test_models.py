import unittest

from whisper_subtitle_app.models import AppSource


class AppSourceTests(unittest.TestCase):
    def test_label_includes_bundle_identifier(self) -> None:
        app = AppSource(name="VLC", bundle_identifier="org.videolan.vlc", process_id=123)

        self.assertEqual(app.label, "VLC (org.videolan.vlc)")


if __name__ == "__main__":
    unittest.main()
