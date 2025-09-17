# CompassPhoto Module

A unified Python module for downloading staff and student profile photos from Compass Education.

## Quick Start

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

### 2. Initialize the Class with Username and Password

```python
from compassphoto import CompassPhoto

# Initialize with your credentials
compass = CompassPhoto(username="your_username", password="your_password")
```

### 3. Download Photos

```python
# Download staff photos
compass.get_staff_photos()

# Download student photos
compass.get_student_photos()

# Download all photos (staff + students)
compass.get_all_photos()
```

## Complete Example

```python
from compassphoto import CompassPhoto

# Step 1: Initialize with credentials
compass = CompassPhoto(username="your_username", password="your_password")

# Step 2: Download photos
print("Downloading staff photos...")
staff_results = compass.get_staff_photos()
print(f"Downloaded {staff_results['downloaded']} staff photos")

print("Downloading student photos...")
student_results = compass.get_student_photos()
print(f"Downloaded {student_results['downloaded']} student photos")

print("Download complete!")
```

## Alternative: Using Environment Variables

Instead of passing credentials directly, you can set environment variables:

```bash
export COMPASS_USERNAME="your_username"
export COMPASS_PASSWORD="your_password"
```

Then use the module without credentials:

```python
from compassphoto import CompassPhoto

# Uses environment variables
compass = CompassPhoto()
compass.get_all_photos()
```

## Advanced Usage

### Custom Directories

```python
compass = CompassPhoto("username", "password")

# Download to custom directories
compass.get_staff_photos(custom_dir="my_staff_photos")
compass.get_student_photos(custom_dir="my_student_photos")
```

### Limit Downloads (for testing)

```python
# Download only first 10 staff photos
compass.get_staff_photos(limit=10)

# Download only first 5 student photos
compass.get_student_photos(limit=5)
```

### Download All with Options

```python
compass.get_all_photos(
    staff_limit=50,           # Limit staff photos
    student_limit=100,        # Limit student photos
    staff_dir="staff_2024",   # Custom staff directory
    student_dir="students_2024"  # Custom student directory
)
```

## Command Line Usage

You can also run the module directly from the command line:

```bash
# Download all photos
python compassphoto.py username password all

# Download only staff photos
python compassphoto.py username password staff

# Download only student photos
python compassphoto.py username password student
```

## Return Values

All methods return download statistics:

```python
{
    'total_processed': 100,
    'downloaded': 85,
    'updated': 10,
    'skipped': 5,
    'failed': 0
}
```

## File Naming

Photos are saved as:
```
{displayCode}_{guid}_{timestamp}.jpg
```

Example: `JOHN_SMITH_12345678_2502250258AM.jpg`

## Features

- **Unified Interface**: Single module for all photo downloads
- **Smart Updates**: Only downloads changed photos based on timestamps
- **Progress Tracking**: Real-time progress updates
- **Error Handling**: Robust error handling with detailed reporting
- **Flexible**: Class-based, function-based, and command-line usage