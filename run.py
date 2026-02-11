#!/usr/bin/env python3
"""Test script: get ALL staff and student photo URLs (no limits)."""

import json
import os
from datetime import datetime

import requests
from compass_photo import CompassPhoto

HC_PING_URL = "https://hc-ping.com/1e44f4d1-6408-4162-9e11-460b917e020c"


def main():
    # Uses COMPASS_USERNAME, COMPASS_PASSWORD, COMPASS_BASE_URL from .env
    # PHOTOS_DIR: single folder for all photos (default: photos). Set to your path when deploying.
    photos_dir = os.environ.get("PHOTOS_DIR", "photos")

    compass = CompassPhoto()

    print(f"Fetching and downloading ALL photos to {photos_dir}/...")
    start_time = datetime.now()

    # Auth once, then get staff and students with the same session
    print("Authenticating with Compass...")
    compass.session = compass.get_authenticated_session()

    print("Getting staff...")
    staff_results = compass.get_staff_photos(
        download=True,
        custom_dir=photos_dir,
        use_existing_session=True,
    )
    compass._human_delay(5, 2)  # Pause before student phase (human-like)
    print("Getting students...")
    student_results = compass.get_student_photos(
        download=True,
        custom_dir=photos_dir,
        use_existing_session=True,
    )

    end_time = datetime.now()
    duration = end_time - start_time

    # Build combined result (same shape as get_all_photos when download=True)
    staff_map = staff_results.get("staff_map", staff_results) if isinstance(staff_results, dict) else staff_results
    student_map = student_results.get("student_map", student_results) if isinstance(student_results, dict) else student_results
    photos = {**staff_map, **student_map}
    staff_stats = staff_results.get("download_stats", {}) if isinstance(staff_results, dict) else {}
    student_stats = student_results.get("download_stats", {}) if isinstance(student_results, dict) else {}
    download_stats = {
        "total_processed": staff_stats.get("total_processed", 0) + student_stats.get("total_processed", 0),
        "downloaded": staff_stats.get("downloaded", 0) + student_stats.get("downloaded", 0),
        "updated": staff_stats.get("updated", 0) + student_stats.get("updated", 0),
        "skipped": staff_stats.get("skipped", 0) + student_stats.get("skipped", 0),
        "failed": staff_stats.get("failed", 0) + student_stats.get("failed", 0),
    }

    total = len(photos)
    print(f"\nTotal photos: {total}")
    print(f"Duration: {duration}")
    if download_stats:
        print(f"Download stats: {download_stats}")

    if photos:
        print("\n--- Sample (first 3) ---")
        for i, (code, url) in enumerate(list(photos.items())[:3]):
            print(f"  {code}: {url[:60]}...")

    # Optional: write full result to JSON for inspection (duration may be timedelta → str for JSON)
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
