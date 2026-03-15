import unittest

from whisper_subtitle_app.subtitle_buffer import SubtitleBuffer, SubtitleBufferConfig


class SubtitleBufferTests(unittest.TestCase):
    def test_deduplicates_adjacent_lines(self) -> None:
        buffer = SubtitleBuffer()

        self.assertTrue(buffer.add_line("Hello world"))
        self.assertFalse(buffer.add_line("  hello   world  "))
        self.assertEqual(buffer.to_display_text(), "Hello world")

    def test_respects_max_lines(self) -> None:
        buffer = SubtitleBuffer(SubtitleBufferConfig(max_lines=2))
        buffer.extend(["one", "two", "three"])

        self.assertEqual(buffer.to_display_text(), "two\nthree")

    def test_clear_resets_duplicate_tracking(self) -> None:
        buffer = SubtitleBuffer()
        buffer.add_line("same")
        buffer.clear()

        self.assertTrue(buffer.add_line("same"))


if __name__ == "__main__":
    unittest.main()
