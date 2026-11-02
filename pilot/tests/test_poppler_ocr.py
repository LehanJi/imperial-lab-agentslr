import unittest

from src.ocr.clients.poppler import _plain_text_to_markdown


class PopplerMarkdownTest(unittest.TestCase):
    def test_preserves_page_boundaries(self):
        markdown, pages = _plain_text_to_markdown("Title\nBody\fSecond page\f")
        self.assertEqual(pages, 2)
        self.assertIn("<!-- PAGE 1 -->", markdown)
        self.assertIn("<!-- PAGE 2 -->", markdown)
        self.assertEqual(markdown.count("\n\n---\n\n"), 1)


if __name__ == "__main__":
    unittest.main()
