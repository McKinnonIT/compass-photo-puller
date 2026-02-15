#!/usr/bin/env python3
"""Test script: get ALL staff and student photo URLs (no limits)."""

import json
import os

import requests
from compass_photo import CompassPhoto

HC_PING_URL = "https://hc-ping.com/1e44f4d1-6408-4162-9e11-460b917e020c"


def main():
    # Uses COMPASS_USERNAME, COMPASS_PASSWORD, COMPASS_BASE_URL from .env
    # PHOTOS_DIR: single folder for all photos (default: photos). Set to your path when deploying.
    photos_dir = os.environ.get("PHOTOS_DIR", "photos")

    compass = CompassPhoto()
    print(f"Fetching and downloading ALL photos to {photos_dir}/...")
    result = compass.get_all_photos(
        download=True,
        staff_dir=photos_dir,
        student_dir=photos_dir,
    )

    duration = result.get("duration", "N/A")
    photos = result.get("photos", {})
    download_stats = result.get("download_stats", {})

    total = len(photos)
    print(f"\nTotal photos: {total}")
    print(f"Duration: {duration}")
    if download_stats:
        print(f"Download stats: {download_stats}")

    if photos:
        print("\n--- Sample (first 3) ---")
        for i, (code, url) in enumerate(list(photos.items())[:3]):
            print(f"  {code}: {url[:60]}...")

    out_path = "all_photos_urls.json"
    duration_str = str(duration) if duration is not None else "N/A"
    with open(out_path, "w") as f:
        json.dump({"photos": photos, "duration": duration_str, "download_stats": download_stats}, f, indent=2)
    print(f"\nFull URL map written to: {out_path}")
    print(f"Photos saved to: {photos_dir}/")


if __name__ == "__main__":
    main()
    try:
        requests.get(HC_PING_URL, timeout=10)
        print("Healthcheck ping sent.")
    except Exception as e:
        print(f"Healthcheck ping failed: {e}")
