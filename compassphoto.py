#!/usr/bin/env python3
"""
Compatibility shim: re-export package API for users importing compassphoto.py directly.
"""

from compass_photo import (
    CompassPhoto,
    get_staff_photos,
    get_student_photos,
    get_all_photos,
    get_single_photo,
)

__all__ = [
    "CompassPhoto",
    "get_staff_photos",
    "get_student_photos",
    "get_all_photos",
    "get_single_photo",
]
