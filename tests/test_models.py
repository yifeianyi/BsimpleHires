import unittest

from models import FileManager


class FileManagerTests(unittest.TestCase):
    def test_add_file_deduplicates_by_absolute_path(self):
        manager = FileManager()

        first = manager.add_file("demo.mp4")
        second = manager.add_file(".\\demo.mp4")

        self.assertIs(first, second)
        self.assertEqual(1, len(manager.files))

    def test_remove_by_indices_and_clear(self):
        manager = FileManager()
        manager.add_file("a.mp4")
        manager.add_file("b.mp4")
        manager.add_file("c.mp4")

        manager.remove_by_indices([0, 2])
        self.assertEqual(["b.mp4"], [file.filename for file in manager.files])

        manager.clear()
        self.assertEqual([], manager.files)


if __name__ == "__main__":
    unittest.main()
