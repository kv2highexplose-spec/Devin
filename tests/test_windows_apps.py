import tempfile
import unittest
from pathlib import Path

from windows_apps.core import (
    Move, duplicate_groups, execute_moves, rename_plan, sort_plan, transform_text,
)


class FileToolsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def create(self, name, content=b"content"):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_rename_preview_apply_and_undo(self):
        original = self.create("notes.txt")
        plan = rename_plan([original], find="notes", replace="ideas", prefix="2026_",
                           numbering=True)
        self.assertTrue(original.exists())
        self.assertEqual(plan[0].destination.name, "2026_001_ideas.txt")
        execute_moves(plan)
        self.assertFalse(original.exists())
        self.assertEqual(plan[0].destination.read_bytes(), b"content")
        execute_moves([Move(plan[0].destination, original, plan[0].size, plan[0].modified_ns)])
        self.assertTrue(original.exists())

    def test_rename_refuses_existing_destination_and_reserved_names(self):
        first = self.create("one.txt")
        self.create("two.txt")
        with self.assertRaises(FileExistsError):
            rename_plan([first], find="one", replace="two")
        with self.assertRaises(ValueError):
            rename_plan([first], find="one", replace="CON")

    def test_rename_refuses_duplicate_destinations(self):
        one = self.create("a.txt")
        two = self.create("aa.txt")
        with self.assertRaises(ValueError):
            rename_plan([one, two], find="a", replace="")

    def test_execute_refuses_files_changed_after_preview(self):
        original = self.create("one.txt")
        plan = rename_plan([original], prefix="new_")
        original.write_bytes(b"updated content")
        with self.assertRaises(ValueError):
            execute_moves(plan)
        self.assertTrue(original.exists())

    def test_sort_only_moves_top_level_files(self):
        photo = self.create("photo.JPG")
        archive = self.create("thing.unknown")
        nested = self.create("nested/document.pdf")
        plan = sort_plan(self.folder)
        self.assertEqual({move.destination.parent.name for move in plan}, {"Images", "Other"})
        execute_moves(plan)
        self.assertTrue((self.folder / "Images" / photo.name).exists())
        self.assertTrue((self.folder / "Other" / archive.name).exists())
        self.assertTrue(nested.exists())

    def test_duplicate_scan_compares_contents_and_skips_links(self):
        first = self.create("a.txt", b"same")
        second = self.create("nested/b.txt", b"same")
        self.create("c.txt", b"else")
        try:
            (self.folder / "shortcut.txt").symlink_to(first)
        except OSError:
            pass
        groups, skipped = duplicate_groups(self.folder)
        self.assertEqual(groups, [[first, second]])
        self.assertEqual(skipped, [])


class TextToolsTests(unittest.TestCase):
    def test_transformations(self):
        self.assertEqual(transform_text(" a  \n b \n", "Trim lines"), "a\nb\n")
        self.assertEqual(transform_text("a\n \nb\n", "Remove empty lines"), "a\nb\n")
        self.assertEqual(transform_text("A\na\nA", "Unique lines"), "A\na")
        self.assertEqual(transform_text("beta\nAlpha\n", "Sort lines"), "Alpha\nbeta\n")
        self.assertEqual(transform_text("a  b\t c", "Collapse spaces"), "a b c")


if __name__ == "__main__":
    unittest.main()
