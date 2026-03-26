import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import metadata_extractor


def create_test_image(path: Path):
    image = Image.new("RGB", (10, 10), color="blue")
    image.save(path, format="JPEG")


class MetadataExtractorTests(unittest.TestCase):
    def test_extract_metadata_includes_image_properties(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.jpg"
            create_test_image(image_path)
            details_seen = []

            class FakeExifModule:
                @staticmethod
                def process_file(_file_obj, details=False):
                    details_seen.append(details)
                    return {"Image Make": "TestCam", "EXIF ISOSpeedRatings": "100"}

            with patch.object(
                metadata_extractor,
                "load_dependencies",
                return_value=(Image, FakeExifModule),
            ):
                result = metadata_extractor.extract_metadata(str(image_path))

            self.assertEqual(details_seen, [False])
            self.assertEqual(result["image_properties"]["format"], "JPEG")
            self.assertEqual(result["image_properties"]["size"], [10, 10])
            self.assertEqual(result["exif"]["Image Make"], "TestCam")
            self.assertGreater(result["file"]["size_bytes"], 0)

    def test_extract_metadata_raises_for_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            metadata_extractor.extract_metadata("/does/not/exist.jpg")

    def test_main_json_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "sample.jpg"
            create_test_image(image_path)
            details_seen = []

            class FakeExifModule:
                @staticmethod
                def process_file(_file_obj, details=False):
                    details_seen.append(details)
                    return {"Image Model": "ModelX"}

            with patch.object(
                metadata_extractor,
                "load_dependencies",
                return_value=(Image, FakeExifModule),
            ), patch(
                "sys.argv",
                ["metadata_extractor.py", str(image_path), "--json"],
            ):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    exit_code = metadata_extractor.main()

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertEqual(details_seen, [False])
            parsed = json.loads(output)
            self.assertEqual(parsed["exif"]["Image Model"], "ModelX")


if __name__ == "__main__":
    unittest.main()
