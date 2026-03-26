# Image Metadata Extractor

A Python CLI tool to extract rich metadata and image properties from image files or entire directories.

## Features

- Extract key EXIF tags (camera make/model, capture time, exposure, aperture, ISO)
- Convert GPS EXIF coordinates to decimal latitude/longitude (when present)
- Show image properties (format, dimensions, color mode)
- Show advanced file metadata (MIME type, SHA256, created/modified UTC timestamps)
- Process a single image file or a directory of images
- Optional recursive directory scan (`--recursive`)
- Optional JSON output for automation (`--json`)
- Optional JSON export to file (`--output <file>`)
- Optional full EXIF dump (`--all-exif`)
- Works with either direct CLI path or interactive prompt input

## Requirements

- Python 3.8+
- Dependencies:
  - exifread
  - imagesize

Install dependencies:

```bash
pip install exifread imagesize
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

Run against a directory:

```bash
python metadata_extractor.py /path/to/folder
```

Run against a directory recursively:

```bash
python metadata_extractor.py /path/to/folder --recursive
```

JSON output:

```bash
python metadata_extractor.py /path/to/image.jpg --json
```

Save JSON output to a file:

```bash
python metadata_extractor.py /path/to/image.jpg --json --output metadata.json
```

Include all EXIF tags:

```bash
python metadata_extractor.py /path/to/image.jpg --all-exif
```
