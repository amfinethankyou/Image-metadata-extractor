import argparse
import hashlib
import json
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

KEY_TAGS = [
    "Image Make",
    "Image Model",
    "EXIF DateTimeOriginal",
    "EXIF ExposureTime",
    "EXIF FNumber",
    "EXIF ISOSpeedRatings",
    "Image Orientation",
]

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
}


def load_dependencies():
    try:
        import exifread  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'exifread'. Install with: pip install exifread"
        ) from exc

    # Avoid printing informational parser messages for images without EXIF.
    logging.getLogger("exifread").setLevel(logging.ERROR)

    try:
        import imagesize  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'imagesize'. Install with: pip install imagesize"
        ) from exc

    return exifread, imagesize


def human_file_size(size_bytes):
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(size_bytes)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.2f} {units[unit_index]}"


def to_utc_iso(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def file_sha256(file_path):
    digest = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _ratio_to_float(value):
    if hasattr(value, "num") and hasattr(value, "den") and value.den != 0:
        return float(value.num) / float(value.den)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _gps_values_to_decimal(values, ref):
    if not values or len(values) != 3:
        return None
    d = _ratio_to_float(values[0])
    m = _ratio_to_float(values[1])
    s = _ratio_to_float(values[2])
    if d is None or m is None or s is None:
        return None
    decimal = d + (m / 60.0) + (s / 3600.0)
    if ref in ("S", "W"):
        decimal *= -1
    return round(decimal, 7)


def extract_gps(tags):
    lat_tag = tags.get("GPS GPSLatitude")
    lat_ref_tag = tags.get("GPS GPSLatitudeRef")
    lon_tag = tags.get("GPS GPSLongitude")
    lon_ref_tag = tags.get("GPS GPSLongitudeRef")

    if not all((lat_tag, lat_ref_tag, lon_tag, lon_ref_tag)):
        return None

    lat_ref = str(lat_ref_tag).strip().upper()
    lon_ref = str(lon_ref_tag).strip().upper()

    latitude = _gps_values_to_decimal(getattr(lat_tag, "values", None), lat_ref)
    longitude = _gps_values_to_decimal(getattr(lon_tag, "values", None), lon_ref)

    if latitude is None or longitude is None:
        return None

    return {"latitude": latitude, "longitude": longitude}


def iter_image_files(input_path, recursive=False):
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {input_path}")

    if path.is_file():
        return [str(path)]

    if not path.is_dir():
        raise ValueError(f"Unsupported path type: {input_path}")

    pattern = "**/*" if recursive else "*"
    files = [
        str(candidate)
        for candidate in path.glob(pattern)
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        raise ValueError("No supported image files found in directory.")

    return sorted(files)


def extract_metadata(image_path, include_all_exif=False):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"File not found: {image_path}")

    exifread, imagesize = load_dependencies()
    abs_path = os.path.abspath(image_path)
    file_size = os.path.getsize(image_path)
    stat = os.stat(image_path)
    mime_type = mimetypes.guess_type(image_path)[0] or "unknown"

    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

        filtered_exif = {}
        for tag in KEY_TAGS:
            if tag in tags:
                filtered_exif[tag] = str(tags[tag])

        width, height = imagesize.get(image_path)
        if width <= 0 or height <= 0:
            raise ValueError("Unable to detect image dimensions.")

        extension = Path(abs_path).suffix.lower()
        image_format = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".tif": "TIFF",
            ".tiff": "TIFF",
            ".bmp": "BMP",
            ".webp": "WEBP",
        }.get(extension, extension.lstrip(".").upper() or "UNKNOWN")

        metadata = {
            "file": {
                "path": abs_path,
                "name": os.path.basename(abs_path),
                "extension": extension,
                "mime_type": mime_type,
                "size_bytes": file_size,
                "size_human": human_file_size(file_size),
                "sha256": file_sha256(image_path),
                "created_utc": to_utc_iso(stat.st_ctime),
                "modified_utc": to_utc_iso(stat.st_mtime),
            },
            "image_properties": {
                "format": image_format,
                "size": [width, height],
                "width": width,
                "height": height,
                "megapixels": round((width * height) / 1_000_000, 3),
                "mode": str(tags.get("Image PhotometricInterpretation", "unknown")),
            },
            "exif": filtered_exif,
        }

        gps = extract_gps(tags)
        if gps is not None:
            metadata["gps"] = gps

        if include_all_exif:
            metadata["all_exif"] = {key: str(value) for key, value in tags.items()}

        return metadata
    except OSError as exc:
        raise ValueError(f"Unable to read image file: {exc}") from exc


def print_metadata(metadata):
    print("\n--- File Information ---")
    print(f"Path: {metadata['file']['path']}")
    print(f"Name: {metadata['file']['name']}")
    print(f"MIME Type: {metadata['file']['mime_type']}")
    print(f"File Size: {metadata['file']['size_human']} ({metadata['file']['size_bytes']} bytes)")
    print(f"SHA256: {metadata['file']['sha256']}")
    print(f"Created (UTC): {metadata['file']['created_utc']}")
    print(f"Modified (UTC): {metadata['file']['modified_utc']}")

    print("\n--- Image Properties ---")
    print(f"Image Format: {metadata['image_properties']['format']}")
    print(f"Image Size: {tuple(metadata['image_properties']['size'])} (Width x Height)")
    print(f"Megapixels: {metadata['image_properties']['megapixels']}")
    print(f"Image Mode: {metadata['image_properties']['mode']}")

    print("\n--- EXIF Metadata ---")
    if metadata["exif"]:
        for tag, value in metadata["exif"].items():
            print(f"{tag}: {value}")
    else:
        print("No key EXIF tags found.")

    gps = metadata.get("gps")
    if gps:
        print("\n--- GPS ---")
        print(f"Latitude: {gps['latitude']}")
        print(f"Longitude: {gps['longitude']}")

    all_exif = metadata.get("all_exif")
    if all_exif is not None:
        print("\n--- All EXIF Tags ---")
        if all_exif:
            for tag, value in all_exif.items():
                print(f"{tag}: {value}")
        else:
            print("No EXIF tags found.")


def parse_args():
    parser = argparse.ArgumentParser(description="Extract metadata from image files.")
    parser.add_argument(
        "image_path",
        nargs="?",
        help="Path to the image file (optional; prompts if not provided).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output metadata as JSON.",
    )
    parser.add_argument(
        "--all-exif",
        action="store_true",
        help="Include all available EXIF tags in output.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="If image_path is a directory, process images recursively.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write JSON output.",
    )
    return parser.parse_args()


def build_output_payload(successful_results, failures):
    if len(successful_results) == 1 and not failures:
        return successful_results[0]

    return {
        "summary": {
            "processed": len(successful_results) + len(failures),
            "success_count": len(successful_results),
            "failure_count": len(failures),
        },
        "results": successful_results,
        "failures": failures,
    }


def main():
    args = parse_args()
    image_path = args.image_path

    if not image_path:
        image_path = input("Please enter the path to the image file: ").strip()

    if not image_path:
        print("Error: No image path provided.")
        return 1

    try:
        image_files = iter_image_files(image_path, recursive=args.recursive)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    successful_results = []
    failures = []

    for candidate in image_files:
        try:
            metadata = extract_metadata(candidate, include_all_exif=args.all_exif)
            successful_results.append(metadata)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            failures.append({"path": os.path.abspath(candidate), "error": str(exc)})

    output_payload = build_output_payload(successful_results, failures)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)

    if args.json:
        print(json.dumps(output_payload, indent=2))
    else:
        if isinstance(output_payload, dict) and "file" in output_payload:
            print_metadata(output_payload)
        else:
            for item in output_payload["results"]:
                print_metadata(item)
                print("\n" + ("=" * 60))

            print("\n--- Summary ---")
            summary = output_payload["summary"]
            print(f"Processed: {summary['processed']}")
            print(f"Success: {summary['success_count']}")
            print(f"Failures: {summary['failure_count']}")

            if output_payload["failures"]:
                print("\n--- Failures ---")
                for failure in output_payload["failures"]:
                    print(f"{failure['path']}: {failure['error']}")

    if not successful_results:
        return 1

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
