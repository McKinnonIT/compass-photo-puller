#!/usr/bin/env python3
import json
import os
import time
import re
import glob
from datetime import datetime

import cloudscraper
from bs4 import BeautifulSoup


class CompassPhoto:
    """Unified class for downloading photos from Compass Education"""
    
    def __init__(self, username: str = None, password: str = None, base_url: str = None):
        from dotenv import load_dotenv
        load_dotenv()
        self.username = username or os.getenv("COMPASS_USERNAME")
        self.password = password or os.getenv("COMPASS_PASSWORD")
        self.base_url = base_url or os.getenv("COMPASS_BASE_URL")
        if not self.username or not self.password:
            raise ValueError("Username and password must be provided or set in environment variables")
        if not self.base_url:
            raise ValueError("Base URL must be provided or set in environment variable COMPASS_BASE_URL")
        self.staff_dir = "compass_photos/staff"
        self.student_dir = "compass_photos/students"
        os.makedirs(self.staff_dir, exist_ok=True)
        os.makedirs(self.student_dir, exist_ok=True)

    def extract_timestamp_from_pv(self, pv_string):
        if not pv_string:
            return None
        timestamp_match = re.search(r'_(\d{10}[AP]M)', pv_string)
        if timestamp_match:
            return timestamp_match.group(1)
        return None

    def should_update_photo(self, photos_dir, display_code, current_pv):
        current_timestamp = self.extract_timestamp_from_pv(current_pv)
        if not current_timestamp:
            return True, None
        pattern = os.path.join(photos_dir, f"{display_code}_*.jpg")
        existing_files = glob.glob(pattern)
        if not existing_files:
            return True, None
        for existing_file in existing_files:
            filename = os.path.basename(existing_file)
            if current_timestamp in filename:
                return False, existing_file
        return True, existing_files[0] if existing_files else None

    def get_authenticated_session(self):
        base_url = self.base_url
        session = cloudscraper.create_scraper()
        login_url = f"{base_url}/login.aspx?sessionstate=disabled"
        login_get_response = session.get(login_url, timeout=15)
        login_get_response.raise_for_status()
        soup = BeautifulSoup(login_get_response.text, 'html.parser')
        form = soup.find('form')
        if not form:
            raise Exception("No login form found")
        payload = {}
        for input_field in form.find_all('input'):
            name = input_field.get('name')
            value = input_field.get('value', '')
            if name:
                payload[name] = value
        payload['username'] = self.username
        payload['password'] = self.password
        login_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Referer": login_url,
            "Origin": base_url
        }
        r = session.post(login_url, data=payload, headers=login_headers, timeout=15)
        r.raise_for_status()
        if not ("Home | Compass" in r.text or "productNavBar" in r.text or "Compass.mfeConfig" in r.text):
            raise Exception("Login failed - no authenticated content found")
        return session

    def get_staff_data(self, session):
        base_url = self.base_url
        user_new_url = f"{base_url}/Records/UserNew.aspx"
        page_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        page_response = session.get(user_new_url, headers=page_headers, timeout=15)
        page_response.raise_for_status()
        time.sleep(3)
        staff_url = f"{base_url}/Services/ChronicleV2.svc/GetStaff"
        staff_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd", 
            "Accept-Language": "en-GB,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": base_url,
            "Referer": f"{base_url}/Records/UserNew.aspx?",
            "Sec-CH-UA": '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors", 
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36",
            "Priority": "u=1, i"
        }
        staff_response = session.post(staff_url, headers=staff_headers, data="{}", timeout=15)
        staff_response.raise_for_status()
        return staff_response.json()

    def get_student_data(self, session):
        base_url = self.base_url
        form_group_url = f"{base_url}/Records/FormGroup.aspx?id=07A"
        page_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-CH-UA": '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1"
        }
        page_response = session.get(form_group_url, headers=page_headers, timeout=15)
        page_response.raise_for_status()
        time.sleep(3)
        students_url = f"{base_url}/Services/User.svc/GetAllStudentsBasic?sessionstate=readonly"
        students_headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-GB,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": base_url,
            "Referer": form_group_url,
            "Sec-CH-UA": '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"macOS"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Priority": "u=1, i"
        }
        payload = '{"includePhotos": true}'
        students_response = session.post(students_url, headers=students_headers, data=payload, timeout=15)
        students_response.raise_for_status()
        return students_response.json()

    def download_photos(self, people_with_photos, photos_dir, people_type="photos", limit=None):
        base_url = f"{self.base_url}/download/secure/cdn/full/"
        downloaded = 0
        updated = 0
        skipped = 0
        failed = 0
        photos_to_download = people_with_photos[:limit] if limit else people_with_photos
        total_photos = len(photos_to_download)
        print(f"Starting download of {total_photos} {people_type}...")
        for i, person in enumerate(photos_to_download):
            try:
                photo_url = base_url + person['pv']
                safe_name = "".join(c for c in person['displayCode'] if c.isalnum() or c in (' ', '-', '_')).strip()
                timestamp = self.extract_timestamp_from_pv(person['pv']) or "unknown"
                guid = person['pv'][:8]
                filename = f"{safe_name}_{guid}_{timestamp}.jpg"
                filepath = os.path.join(photos_dir, filename)
                should_update, existing_file = self.should_update_photo(photos_dir, safe_name, person['pv'])
                if not should_update:
                    print(f"[{i+1}/{total_photos}] Skipping {person['displayCode']}: up to date ({timestamp})")
                    skipped += 1
                    continue
                if existing_file:
                    print(f"[{i+1}/{total_photos}] Updating {person['name']} ({person['displayCode']}) - photo changed")
                    os.remove(existing_file)
                    action_type = "updated"
                else:
                    print(f"[{i+1}/{total_photos}] Downloading {person['name']} ({person['displayCode']}) - new photo")
                    action_type = "downloaded"
                response = self.session.get(photo_url, timeout=30)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                if action_type == "updated":
                    updated += 1
                else:
                    downloaded += 1
                print(f"  [OK] Saved as {filename}")
                if (i + 1) % 25 == 0:
                    total_processed = downloaded + updated
                    print(f"Progress: {i+1}/{total_photos} ({(i+1)/total_photos*100:.1f}%) - {total_processed} processed")
            except Exception as e:
                failed += 1
                print(f"  [ERROR] Failed to download {person['name']}: {e}")
        print(f"\n=== {people_type.upper()} DOWNLOAD COMPLETE ===")
        print(f"Total processed: {total_photos}")
        print(f"New downloads: {downloaded}")
        print(f"Updated photos: {updated}")
        print(f"Skipped (up-to-date): {skipped}")
        print(f"Failed: {failed}")
        print(f"Photos saved to: {photos_dir}/")
        return {
            'total_processed': total_photos,
            'downloaded': downloaded,
            'updated': updated,
            'skipped': skipped,
            'failed': failed
        }

    def get_staff_photos(self, limit=None, custom_dir=None, download=False):
        print("=" * 50)
        print("GETTING STAFF PHOTOS")
        print("=" * 50)
        print("Authenticating with Compass...")
        self.session = self.get_authenticated_session()
        print("Getting staff data...")
        data = self.get_staff_data(self.session)
        staff_with_photos = []
        for staff_member in data.get('d', []):
            pv = staff_member.get('pv', '')
            if pv and pv.strip():
                staff_with_photos.append({
                    'name': staff_member.get('n', 'Unknown'),
                    'displayCode': staff_member.get('displayCode', 'UNKNOWN'),
                    'pv': pv.strip()
                })
        print(f"Found {len(staff_with_photos)} staff members with profile photos")
        if limit:
            staff_with_photos = staff_with_photos[:limit]
        base_url = f"{self.base_url}/download/secure/cdn/full/"
        staff_map = {}
        for staff in staff_with_photos:
            staff_map[staff['displayCode']] = base_url + staff['pv']
        if download:
            photos_dir = custom_dir or self.staff_dir
            os.makedirs(photos_dir, exist_ok=True)
            download_stats = self.download_photos(staff_with_photos, photos_dir, "staff photos", limit)
            return {
                'staff_map': staff_map,
                'download_stats': download_stats
            }
        return staff_map

    def get_student_photos(self, limit=None, custom_dir=None, save_debug=False, download=False):
        print("=" * 50)
        print("GETTING STUDENT PHOTOS")
        print("=" * 50)
        print("Authenticating with Compass...")
        self.session = self.get_authenticated_session()
        print("Getting student data...")
        data = self.get_student_data(self.session)
        if save_debug:
            with open('students_response.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(data))
            with open('students_response_pretty.json', 'w', encoding='utf-8') as f:
                import json as _json
                _json.dump(data, f, indent=2, ensure_ascii=False)
        students_with_photos = []
        if 'd' in data:
            student_list = data['d']
        else:
            student_list = data if isinstance(data, list) else [data]
        for student in student_list:
            pv = student.get('pv', '') or student.get('photoUrl', '') or student.get('photo', '')
            if pv and pv.strip():
                students_with_photos.append({
                    'name': student.get('n', student.get('name', 'Unknown')),
                    'displayCode': student.get('displayCode', student.get('code', 'UNKNOWN')),
                    'pv': pv.strip()
                })
        print(f"Found {len(students_with_photos)} students with profile photos")
        if limit:
            students_with_photos = students_with_photos[:limit]
        base_url = f"{self.base_url}/download/secure/cdn/full/"
        student_map = {}
        for student in students_with_photos:
            student_map[student['displayCode']] = base_url + student['pv']
        if download:
            photos_dir = custom_dir or self.student_dir
            os.makedirs(photos_dir, exist_ok=True)
            download_stats = self.download_photos(students_with_photos, photos_dir, "student photos", limit)
            return {
                'student_map': student_map,
                'download_stats': download_stats
            }
        return student_map

    def get_all_photos(self, staff_limit=None, student_limit=None, 
                      staff_dir=None, student_dir=None, save_debug=False, download=False):
        print("=" * 60)
        print("    COMPASS PHOTO DOWNLOADER - ALL USERS")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        start_time = datetime.now()
        staff_results = self.get_staff_photos(limit=staff_limit, custom_dir=staff_dir, download=download)
        student_results = self.get_student_photos(limit=student_limit, custom_dir=student_dir, save_debug=save_debug, download=download)
        end_time = datetime.now()
        duration = end_time - start_time
        print("\n" + "=" * 50)
        print("FINAL SUMMARY")
        print("=" * 50)
        print(f"Total Duration: {duration}")
        print()
        if download:
            print("STAFF PHOTOS:")
            if staff_results and 'download_stats' in staff_results:
                stats = staff_results['download_stats']
                print(f"  Total processed: {stats['total_processed']}")
                print(f"  New downloads: {stats['downloaded']}")
                print(f"  Updated photos: {stats['updated']}")
                print(f"  Skipped (up-to-date): {stats['skipped']}")
                print(f"  Failed: {stats['failed']}")
            print("\nSTUDENT PHOTOS:")
            if student_results and 'download_stats' in student_results:
                stats = student_results['download_stats']
                print(f"  Total processed: {stats['total_processed']}")
                print(f"  New downloads: {stats['downloaded']}")
                print(f"  Updated photos: {stats['updated']}")
                print(f"  Skipped (up-to-date): {stats['skipped']}")
                print(f"  Failed: {stats['failed']}")
            if (staff_results and 'download_stats' in staff_results and 
                student_results and 'download_stats' in student_results):
                staff_stats = staff_results['download_stats']
                student_stats = student_results['download_stats']
                total_processed = staff_stats['total_processed'] + student_stats['total_processed']
                total_downloaded = staff_stats['downloaded'] + student_stats['downloaded']
                total_updated = staff_stats['updated'] + student_stats['updated']
                total_skipped = staff_stats['skipped'] + student_stats['skipped']
                total_failed = staff_stats['failed'] + student_stats['failed']
                print("\nOVERALL TOTALS:")
                print(f"  Total processed: {total_processed}")
                print(f"  New downloads: {total_downloaded}")
                print(f"  Updated photos: {total_updated}")
                print(f"  Skipped (up-to-date): {total_skipped}")
                print(f"  Failed: {total_failed}")
        else:
            print("STAFF PHOTOS:")
            if staff_results:
                print(f"  Found {len(staff_results)} staff members with photos")
            print("\nSTUDENT PHOTOS:")
            if student_results:
                print(f"  Found {len(student_results)} students with photos")
            print(f"\nTotal photos found: {len(staff_results) + len(student_results)}")
        print(f"\nCompleted at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        combined_map = {}
        if download:
            if isinstance(staff_results, dict) and 'staff_map' in staff_results:
                combined_map.update(staff_results['staff_map'])
            if isinstance(student_results, dict) and 'student_map' in student_results:
                combined_map.update(student_results['student_map'])
            combined_stats = {
                'total_processed': 0,
                'downloaded': 0,
                'updated': 0,
                'skipped': 0,
                'failed': 0
            }
            if isinstance(staff_results, dict) and 'download_stats' in staff_results:
                staff_stats = staff_results['download_stats']
                for key in combined_stats:
                    combined_stats[key] += staff_stats.get(key, 0)
            if isinstance(student_results, dict) and 'download_stats' in student_results:
                student_stats = student_results['download_stats']
                for key in combined_stats:
                    combined_stats[key] += student_stats.get(key, 0)
            return {
                'photos': combined_map,
                'download_stats': combined_stats,
                'duration': duration
            }
        else:
            if isinstance(staff_results, dict):
                combined_map.update(staff_results)
            if isinstance(student_results, dict):
                combined_map.update(student_results)
            return combined_map


def get_staff_photos(username, password, limit=None, custom_dir=None, download=False, base_url=None):
    compass = CompassPhoto(username, password, base_url=base_url)
    return compass.get_staff_photos(limit=limit, custom_dir=custom_dir, download=download)


def get_student_photos(username, password, limit=None, custom_dir=None, save_debug=False, download=False, base_url=None):
    compass = CompassPhoto(username, password, base_url=base_url)
    return compass.get_student_photos(limit=limit, custom_dir=custom_dir, save_debug=save_debug, download=download)


def get_all_photos(username, password, staff_limit=None, student_limit=None, 
                  staff_dir=None, student_dir=None, save_debug=False, download=False, base_url=None):
    compass = CompassPhoto(username, password, base_url=base_url)
    return compass.get_all_photos(staff_limit=staff_limit, student_limit=student_limit,
                                 staff_dir=staff_dir, student_dir=student_dir, save_debug=save_debug, download=download)


