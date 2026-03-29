import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.converter_service import ConverterService
from services.settings_service import AppSettings, SettingsService
from utils import path_utils


class SettingsServiceTests(unittest.TestCase):
    def test_load_and_save_round_trip(self):
        with tempfile.TemporaryDirectory(dir=".") as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"

            with patch.object(SettingsService, "SETTINGS_FILE", settings_path):
                SettingsService.invalidate_cache()
                SettingsService.save(
                    AppSettings(
                        default_output_dir="E:/output",
                        max_workers=9,
                        naming_strategy="overwrite",
                        custom_ffmpeg_dir="E:/ffmpeg-bin",
                        open_output_dir_after_completion=True,
                    )
                )

                SettingsService.invalidate_cache()
                loaded = SettingsService.load()

                self.assertEqual("E:/output", loaded.default_output_dir)
                self.assertEqual(4, loaded.max_workers)
                self.assertEqual("overwrite", loaded.naming_strategy)
                self.assertEqual("E:/ffmpeg-bin", loaded.custom_ffmpeg_dir)
                self.assertTrue(loaded.open_output_dir_after_completion)


class ConverterServiceTests(unittest.TestCase):
    def test_build_output_path_auto_increment(self):
        with tempfile.TemporaryDirectory(dir=".") as temp_dir:
            output_dir = Path(temp_dir)
            existing = output_dir / "song_bsimple.mov"
            existing.write_text("existing", encoding="utf-8")

            with patch("services.converter_service.SettingsService.load", return_value=AppSettings()):
                output_path = ConverterService.build_output_path("song.mp4", str(output_dir))

            self.assertEqual("song_bsimple_2.mov", Path(output_path).name)

    def test_build_output_path_overwrite(self):
        with tempfile.TemporaryDirectory(dir=".") as temp_dir:
            output_dir = Path(temp_dir)
            existing = output_dir / "song_bsimple.mov"
            existing.write_text("existing", encoding="utf-8")

            settings = AppSettings(naming_strategy="overwrite")
            with patch("services.converter_service.SettingsService.load", return_value=settings):
                output_path = ConverterService.build_output_path("song.mp4", str(output_dir))

            self.assertEqual("song_bsimple.mov", Path(output_path).name)


class PathUtilsTests(unittest.TestCase):
    def test_custom_ffmpeg_dir_takes_priority(self):
        with tempfile.TemporaryDirectory(dir=".") as temp_dir:
            ffmpeg_dir = Path(temp_dir)
            ffmpeg_path = ffmpeg_dir / "ffmpeg.exe"
            ffprobe_path = ffmpeg_dir / "ffprobe.exe"
            ffmpeg_path.write_text("binary", encoding="utf-8")
            ffprobe_path.write_text("binary", encoding="utf-8")

            settings = AppSettings(custom_ffmpeg_dir=str(ffmpeg_dir))
            with patch.object(path_utils.SettingsService, "load", return_value=settings):
                self.assertEqual(str(ffmpeg_path.resolve()), path_utils.find_ffmpeg_executable())
                self.assertEqual(str(ffprobe_path.resolve()), path_utils.find_ffprobe_executable())


if __name__ == "__main__":
    unittest.main()
