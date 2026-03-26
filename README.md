# Image Metadata Extractor

A Python CLI tool to extract useful metadata and image properties from image files.

## Features

- Extract key EXIF tags (camera make/model, capture time, exposure, aperture, ISO)
- Show image properties (format, dimensions, color mode)
- Show file size (bytes and human-readable)
- Optional JSON output for automation (`--json`)
- Optional full EXIF dump (`--all-exif`)
- Works with either direct CLI path or interactive prompt input

## Requirements

- Python 3.8+
- Dependencies:
  - Pillow
  - exifread

Install dependencies:

```bash
pip install Pillow exifread
```

## Usage

Run with interactive prompt:

```bash
python metadata_extractor.py
```

Run with direct file path:

```bash
python metadata_extractor.py /path/to/image.jpg
```

JSON output:

```bash
python metadata_extractor.py /path/to/image.jpg --json
```

Include all EXIF tags:

```bash
python metadata_extractor.py /path/to/image.jpg --all-exif
```

## Testing

Run tests:

```bash
python -m unittest -q
```
