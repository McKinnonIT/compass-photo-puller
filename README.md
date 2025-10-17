# Compass Photo Puller

A unified Python package for getting staff and student profile photo URLs from Compass Education, with optional photo downloading. This tool provides both programmatic access via Python classes/functions and command-line interface for easy photo management.

## Quick Start

### 1. Installation

You can install this package in development mode:

```bash
git clone <repository-url>
cd compass_photo_puller
pip install -e .
```

Or install the dependencies directly:

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in your project directory:

```bash
COMPASS_USERNAME=your_username
COMPASS_PASSWORD=your_password
COMPASS_BASE_URL=https://your-school.compass.education
```

### 3. Initialize the Class

```python
from compass_photo import CompassPhoto

# Initialize with your credentials
compass = CompassPhoto(username="your_username", password="your_password", base_url="https://your-school.compass.education")

# Or use environment variables (recommended)
compass = CompassPhoto()
```

### 4. Get Photo URLs (Default Behavior)

```python
# Get staff photo URLs (returns JSON map)
staff_urls = compass.get_staff_photos()
print(staff_urls)  # {"JOHN_SMITH": "https://...", "JANE_DOE": "https://..."}

# Get student photo URLs (returns JSON map)
student_urls = compass.get_student_photos()
print(student_urls)  # {"STU001": "https://...", "STU002": "https://..."}

# Get all photo URLs (returns combined JSON map)
all_urls = compass.get_all_photos()
print(all_urls)  # {"staff": {...}, "student": {...}, "duration": "..."}
```

## Complete Example

```python
from compassphoto import CompassPhoto
import json

# Step 1: Initialize with credentials
compass = CompassPhoto(username="your_username", password="your_password")

# Step 2: Get photo URLs
print("Getting staff photo URLs...")
staff_urls = compass.get_staff_photos()
print(f"Found {len(staff_urls)} staff photos")
print(json.dumps(staff_urls, indent=2))

print("Getting student photo URLs...")
student_urls = compass.get_student_photos()
print(f"Found {len(student_urls)} student photos")
print(json.dumps(student_urls, indent=2))

# Step 3: Download photos (optional)
print("Downloading staff photos...")
staff_result = compass.get_staff_photos(download=True)
print(f"Downloaded {staff_result['download_stats']['downloaded']} staff photos")
```

## JSON Structure

### Default Behavior (download=False)

**Staff Photos:**
```json
{
  "JOHN_SMITH": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_12345678_2502250258AM?requestguid=abc123",
  "JANE_DOE": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_87654321_2502250300AM?requestguid=def456"
}
```

**Student Photos:**
```json
{
  "STU001": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_55667788_2502250320AM?requestguid=jkl012",
  "STU002": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_99887766_2502250330AM?requestguid=mno345"
}
```

**All Photos:**
```json
{
  "staff": {
    "JOHN_SMITH": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_12345678_2502250258AM?requestguid=abc123"
  },
  "student": {
    "STU001": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_55667788_2502250320AM?requestguid=jkl012"
  },
  "duration": "0:00:05.123456"
}
```

**Single Photo (get_single_photo):**
```json
{
  "name": "John Smith",
  "displayCode": "JOHN_SMITH",
  "type": "staff",
  "photo_url": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_12345678_2502250258AM?requestguid=abc123",
  "pv": "guid_12345678_2502250258AM?requestguid=abc123",
  "download_stats": {
    "total_processed": 1,
    "downloaded": 1,
    "updated": 0,
    "skipped": 0,
    "failed": 0
  },
  "file_path": "/path/to/downloaded/photo.jpg"
}
```

### With Download (download=True)

**Staff Photos with Download:**
```json
{
  "staff_map": {
    "JOHN_SMITH": "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/guid_12345678_2502250258AM?requestguid=abc123"
  },
  "download_stats": {
    "total_processed": 1,
    "downloaded": 1,
    "updated": 0,
    "skipped": 0,
    "failed": 0
  }
}
```

## Usage Patterns

### Get URLs Only (Default)

```python
from compassphoto import CompassPhoto

compass = CompassPhoto("username", "password")

# Get URLs without downloading
staff_urls = compass.get_staff_photos()
student_urls = compass.get_student_photos()
all_urls = compass.get_all_photos()

# Use URLs for your own purposes
for code, url in staff_urls.items():
    print(f"{code}: {url}")
```

### Download Photos

```python
# Download photos and get URLs + statistics
staff_result = compass.get_staff_photos(download=True)
print(f"URLs: {staff_result['staff_map']}")
print(f"Stats: {staff_result['download_stats']}")

# Download with custom directory
student_result = compass.get_student_photos(
    download=True, 
    custom_dir="my_student_photos"
)
```

### Get Single Photo

```python
# Get a single photo by display code (searches both staff and students)
photo_info = compass.get_single_photo("ABE", download=True)
print(f"Found: {photo_info['name']} ({photo_info['type']})")
print(f"URL: {photo_info['photo_url']}")
```

### Limit Results (for testing)

```python
# Get only first 10 staff URLs
staff_urls = compass.get_staff_photos(limit=10)

# Download only first 5 student photos
student_result = compass.get_student_photos(limit=5, download=True)
```

## Convenience Functions

```python
from compass_photo import get_staff_photos, get_student_photos, get_all_photos, get_single_photo

# Get URLs only
staff_urls = get_staff_photos("username", "password", base_url="https://your-school.compass.education")
student_urls = get_student_photos("username", "password", base_url="https://your-school.compass.education")

# Download photos
staff_result = get_staff_photos("username", "password", download=True, base_url="https://your-school.compass.education")
all_result = get_all_photos("username", "password", download=True, base_url="https://your-school.compass.education")

# Get a single photo by display code
photo_info = get_single_photo("username", "password", "ABE", download=True, base_url="https://your-school.compass.education")
```

## Method Parameters

### get_staff_photos(limit=None, custom_dir=None, download=False)
- `limit`: Limit number of photos to process
- `custom_dir`: Custom directory to save photos (if download=True)
- `download`: Whether to download photos or just return URLs (default: False)

### get_student_photos(limit=None, custom_dir=None, save_debug=False, download=False)
- `limit`: Limit number of photos to process
- `custom_dir`: Custom directory to save photos (if download=True)
- `save_debug`: Save API response for debugging
- `download`: Whether to download photos or just return URLs (default: False)

### get_all_photos(staff_limit=None, student_limit=None, staff_dir=None, student_dir=None, save_debug=False, download=False)
- `staff_limit`: Limit number of staff photos
- `student_limit`: Limit number of student photos
- `staff_dir`: Custom directory for staff photos (if download=True)
- `student_dir`: Custom directory for student photos (if download=True)
- `save_debug`: Save debug files for student photos
- `download`: Whether to download photos or just return URLs (default: False)

### get_single_photo(display_code, download=False, custom_dir=None)
- `display_code`: The display code of the person (e.g., 'ABE', 'ALB0011')
- `download`: Whether to download the photo to disk (default: False)
- `custom_dir`: Custom directory to save photo (if download=True)

## Features

- **JSON Maps**: Returns clean `{"CODE": "URL"}` mappings by default
- **Optional Download**: Set `download=True` to actually download photos
- **Smart Updates**: Only downloads changed photos based on timestamps
- **Progress Tracking**: Real-time progress updates when downloading
- **Error Handling**: Robust error handling with detailed reporting
- **Flexible Usage**: Class-based, function-based, and command-line interfaces
- **Single Photo Lookup**: Find individual photos by display code across staff and students
- **Environment Configuration**: Secure credential management via environment variables
- **Ready-to-Use URLs**: URLs include authentication and are ready for downloading
- **Compass Education Integration**: Direct integration with Compass Education API endpoints

## Package Structure

```
compass_photo_puller/
├── compass_photo/
│   ├── __init__.py          # Package exports
│   └── core.py              # Main CompassPhoto class and functions
├── compass_photos/          # Downloaded photos directory
│   ├── staff/               # Staff photos
│   └── students/            # Student photos
├── compassphoto.py          # Legacy compatibility shim
├── run.py                   # Simple test script
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Package configuration
└── README.md               # This file
```
