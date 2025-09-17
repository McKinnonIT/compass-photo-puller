# CompassPhoto Module

A unified Python module for downloading photos from Compass Education.

## Quick Start

```python
from compassphoto import CompassPhoto

# Initialize with credentials
compass = CompassPhoto(username="your_username", password="your_password")

# Download photos
compass.get_staff_photos()
compass.get_student_photos()
compass.get_all_photos()
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (optional):
```bash
export COMPASS_USERNAME="your_username"
export COMPASS_PASSWORD="your_password"
```

## Usage

### Class-Based Usage

```python
from compassphoto import CompassPhoto

# Initialize with credentials
compass = CompassPhoto(username="your_username", password="your_password")

# Download staff photos
staff_results = compass.get_staff_photos()

# Download student photos
student_results = compass.get_student_photos()

# Download all photos
all_results = compass.get_all_photos()
```

### Convenience Functions

```python
from compassphoto import get_staff_photos, get_student_photos, get_all_photos

# Download staff photos
staff_results = get_staff_photos("username", "password")

# Download student photos
student_results = get_student_photos("username", "password")

# Download all photos
all_results = get_all_photos("username", "password")
```

### Command Line Usage

```bash
# Download all photos
python compassphoto.py username password all

# Download only staff photos
python compassphoto.py username password staff

# Download only student photos
python compassphoto.py username password student
```

## API Reference

### CompassPhoto Class

#### `__init__(username=None, password=None)`
Initialize with credentials. If None, loads from environment variables.

#### `get_staff_photos(limit=None, custom_dir=None)`
Download staff profile photos.

**Parameters:**
- `limit` (int, optional): Limit number of photos to download
- `custom_dir` (str, optional): Custom directory to save photos

**Returns:** dict with download statistics

#### `get_student_photos(limit=None, custom_dir=None, save_debug=False)`
Download student profile photos.

**Parameters:**
- `limit` (int, optional): Limit number of photos to download
- `custom_dir` (str, optional): Custom directory to save photos
- `save_debug` (bool): Save API response for debugging

**Returns:** dict with download statistics

#### `get_all_photos(staff_limit=None, student_limit=None, staff_dir=None, student_dir=None, save_debug=False)`
Download both staff and student photos.

**Parameters:**
- `staff_limit` (int, optional): Limit number of staff photos
- `student_limit` (int, optional): Limit number of student photos
- `staff_dir` (str, optional): Custom directory for staff photos
- `student_dir` (str, optional): Custom directory for student photos
- `save_debug` (bool): Save debug files for student photos

**Returns:** dict with combined statistics

### Convenience Functions

#### `get_staff_photos(username, password, limit=None, custom_dir=None)`
Convenience function to download staff photos.

#### `get_student_photos(username, password, limit=None, custom_dir=None, save_debug=False)`
Convenience function to download student photos.

#### `get_all_photos(username, password, staff_limit=None, student_limit=None, staff_dir=None, student_dir=None, save_debug=False)`
Convenience function to download all photos.

## Return Values

All methods return a dictionary with download statistics:

```python
{
    'total_processed': 100,
    'downloaded': 85,
    'updated': 10,
    'skipped': 5,
    'failed': 0
}
```

For `get_all_photos()`, returns:
```python
{
    'staff': { ... },      # Staff statistics
    'student': { ... },    # Student statistics
    'duration': timedelta  # Total duration
}
```

## Examples

### Basic Usage

```python
from compassphoto import CompassPhoto

# Using environment variables
compass = CompassPhoto()
compass.get_all_photos()

# Using direct credentials
compass = CompassPhoto("username", "password")
compass.get_staff_photos(limit=10)
```

### Advanced Usage

```python
from compassphoto import CompassPhoto

compass = CompassPhoto("username", "password")

# Download with custom directories
compass.get_all_photos(
    staff_dir="staff_photos_2024",
    student_dir="student_photos_2024",
    staff_limit=50,
    student_limit=100
)

# Download with debug files
compass.get_student_photos(save_debug=True)
```

### Using Convenience Functions

```python
from compassphoto import get_all_photos

# One-liner to download everything
results = get_all_photos("username", "password")
print(f"Downloaded {results['staff']['downloaded']} staff photos")
print(f"Downloaded {results['student']['downloaded']} student photos")
```

## File Naming

Photos are saved with the following naming convention:
```
{displayCode}_{guid}_{timestamp}.jpg
```

Example: `JOHN_SMITH_12345678_2502250258AM.jpg`

## Error Handling

- Invalid credentials raise `ValueError`
- Network errors are caught and reported
- Failed downloads are counted and reported
- Progress is shown every 25 downloads

## Features

- **Unified Interface**: Single module for all photo downloads
- **Flexible Authentication**: Environment variables or direct credentials
- **Custom Directories**: Specify where to save photos
- **Progress Tracking**: Real-time progress updates
- **Smart Updates**: Only downloads changed photos based on timestamps
- **Error Handling**: Robust error handling with detailed reporting
- **Multiple Interfaces**: Class-based, function-based, and command-line usage
