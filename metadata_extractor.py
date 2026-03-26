import argparse
import json
import os

KEY_TAGS = [
    "Image Make",
    "Image Model",
    "EXIF DateTimeOriginal",
    "EXIF ExposureTime",
    "EXIF FNumber",
    "EXIF ISOSpeedRatings",
]


def load_dependencies():
    try:
        from PIL import Image  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'Pillow'. Install with: pip install Pillow"
        ) from exc

    try:
        import exifread  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'exifread'. Install with: pip install exifread"
        ) from exc

    return Image, exifread


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


def extract_metadata(image_path, include_all_exif=False):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"File not found: {image_path}")

    Image, exifread = load_dependencies()
    abs_path = os.path.abspath(image_path)
    file_size = os.path.getsize(image_path)

    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)

        filtered_exif = {}
        for tag in KEY_TAGS:
            if tag in tags:
                filtered_exif[tag] = str(tags[tag])

        with Image.open(image_path) as img:
            metadata = {
                "file": {
                    "path": abs_path,
                    "size_bytes": file_size,
                    "size_human": human_file_size(file_size),
                },
                "image_properties": {
                    "format": img.format,
                    "size": list(img.size),
                    "mode": img.mode,
                },
                "exif": filtered_exif,
            }

        if include_all_exif:
            metadata["all_exif"] = {key: str(value) for key, value in tags.items()}

        return metadata
    except OSError as exc:
        raise ValueError(f"Unable to read image file: {exc}") from exc


def print_metadata(metadata):
    print("\n--- File Information ---")
    print(f"Path: {metadata['file']['path']}")
    print(f"File Size: {metadata['file']['size_human']} ({metadata['file']['size_bytes']} bytes)")

    print("\n--- Image Properties ---")
    print(f"Image Format: {metadata['image_properties']['format']}")
    print(f"Image Size: {tuple(metadata['image_properties']['size'])} (Width x Height)")
    print(f"Image Mode: {metadata['image_properties']['mode']}")

    print("\n--- EXIF Metadata ---")
    if metadata["exif"]:
        for tag, value in metadata["exif"].items():
            print(f"{tag}: {value}")
    else:
        print("No key EXIF tags found.")

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
    return parser.parse_args()

def main():
    args = parse_args()
    image_path = args.image_path

    if not image_path:
        image_path = input("Please enter the path to the image file: ").strip()

    if not image_path:
        print("Error: No image path provided.")
        return 1

    try:
        metadata = extract_metadata(image_path, include_all_exif=args.all_exif)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(metadata, indent=2))
    else:
        print_metadata(metadata)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
