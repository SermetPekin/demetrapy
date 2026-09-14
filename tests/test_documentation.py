from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^]]*\]\(([^)]+)\)")
GITHUB_BLOB_PREFIX = "https://github.com/SermetPekin/demetrapy/blob/main/"


class DocumentationLinkTests(unittest.TestCase):
    def markdown_files(self):
        yield REPOSITORY_ROOT / "README.md"
        yield from (REPOSITORY_ROOT / "docs").rglob("*.md")
        yield from (REPOSITORY_ROOT / "examples").rglob("*.md")

    def test_markdown_links_are_portable(self):
        relative_links = []
        for markdown_file in self.markdown_files():
            for target in MARKDOWN_LINK.findall(
                markdown_file.read_text(encoding="utf-8")
            ):
                if not target.startswith(("https://", "http://", "mailto:", "#")):
                    relative_links.append(f"{markdown_file.name}: {target}")

        self.assertEqual(relative_links, [])

    def test_github_blob_targets_exist(self):
        missing_targets = []
        for markdown_file in self.markdown_files():
            for target in MARKDOWN_LINK.findall(
                markdown_file.read_text(encoding="utf-8")
            ):
                if not target.startswith(GITHUB_BLOB_PREFIX):
                    continue
                repository_path = target.removeprefix(GITHUB_BLOB_PREFIX)
                if not (REPOSITORY_ROOT / repository_path).exists():
                    missing_targets.append(f"{markdown_file.name}: {repository_path}")

        self.assertEqual(missing_targets, [])


if __name__ == "__main__":
    unittest.main()