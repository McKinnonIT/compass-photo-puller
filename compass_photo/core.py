#!/usr/bin/env python3
import json
import os
import random
import re
import glob
import time
from datetime import datetime

import cloudscraper
import requests
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
        # Compass API can be slow; default 60s, override with COMPASS_REQUEST_TIMEOUT
        self.request_timeout = int(os.getenv("COMPASS_REQUEST_TIMEOUT", "60"))
        # Human-like delays (seconds): between API requests, and between each photo download
        self.request_delay = float(os.getenv("COMPASS_REQUEST_DELAY", "2"))
        self.request_delay_jitter = float(os.getenv("COMPASS_REQUEST_DELAY_JITTER", "1"))
        self.download_delay = float(os.getenv("COMPASS_DOWNLOAD_DELAY", "0.25"))
        self.download_delay_jitter = float(os.getenv("COMPASS_DOWNLOAD_DELAY_JITTER", "0.2"))
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

    def _human_delay(self, base_sec=None, jitter_sec=None):
        """Sleep for base_sec + random jitter to mimic human-like gaps between requests."""
        base = base_sec if base_sec is not None else self.request_delay
        jitter = jitter_sec if jitter_sec is not None else self.request_delay_jitter
        if base <= 0 and jitter <= 0:
            return
        sec = base + (random.uniform(0, jitter) if jitter > 0 else 0)
        if sec > 0:
            time.sleep(sec)

    def _request_with_retry(self, session, method, url, max_retries=3, retry_delays=(5, 15, 30), delay_before=True, **kwargs):
        """Run a single request with retries on 403, 429, and timeouts. Optional human-like delay before first attempt."""
        if delay_before:
            self._human_delay()
        def _status(exc):
            r = getattr(exc, "response", None)
            return r.status_code if r is not None else None
        last_error = None
        for attempt in range(max_retries):
            try:
                if method.upper() == "GET":
                    resp = session.get(url, **kwargs)
                else:
                    resp = session.post(url, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.exceptions.HTTPError as e:
                last_error = e
                status = _status(e)
                if attempt < max_retries - 1 and status in (403, 429):
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    print(f"  Request returned {status}, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    print(f"  Request failed ({type(e).__name__}), retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise
        if last_error is not None:
            raise last_error

    def _fetch_photo_with_retry(self, photo_url, max_retries=3, retry_delays=(2, 5, 10)):
        """GET a photo URL with human-like delay before and retries on failure."""
        self._human_delay(self.download_delay, self.download_delay_jitter)
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.session.get(photo_url, timeout=30)
                response.raise_for_status()
                return response
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    time.sleep(wait)
                else:
                    raise
        if last_error is not None:
            raise last_error

    def get_authenticated_session(self, max_retries=3, retry_delays=(5, 15, 30), initial_delay=3, post_delay=2):
        # Normalize base URL (no trailing slash) so login URL is never ...//login.aspx
        base_url = (self.base_url or "").rstrip("/")
        session = cloudscraper.create_scraper()
        login_url = f"{base_url}/login.aspx?sessionstate=disabled"

        # Brief wait before first request (reduces WAF/bot detection)
        if initial_delay:
            print(f"  Waiting {initial_delay}s before login page...")
            time.sleep(initial_delay)

        def _get_status(exc):
            r = getattr(exc, "response", None)
            return r.status_code if r is not None else None

        # GET login page (not auth yet - if this fails, it's access/network, not credentials)
        login_get_response = None
        for attempt in range(max_retries):
            try:
                login_get_response = session.get(login_url, timeout=self.request_timeout)
                login_get_response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                status = _get_status(e)
                if attempt < max_retries - 1 and status in (403, 429):
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    print(f"  Login page not reachable ({status}) - access/network issue, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                elif status in (403, 429):
                    raise RuntimeError(
                        f"Login page could not be loaded ({status}). "
                        "This is an access/network issue (e.g. WAF, IP block), not wrong credentials. "
                        f"Try from school network or check: {login_url}"
                    ) from e
                else:
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    print(f"  Login page request failed ({type(e).__name__}), retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise RuntimeError(
                        "Login page could not be loaded (request failed). "
                        "This is an access/network issue, not credentials. "
                        f"URL: {login_url}"
                    ) from e

        if login_get_response is None:
            raise RuntimeError("Failed to get login page after retries")

        # Wait after loading login page before POST (more human-like)
        if post_delay:
            time.sleep(post_delay)

        soup = BeautifulSoup(login_get_response.text, "html.parser")
        form = soup.find("form")
        if not form:
            raise Exception("No login form found")
        payload = {}
        for input_field in form.find_all("input"):
            name = input_field.get("name")
            value = input_field.get("value", "")
            if name:
                payload[name] = value
        payload["username"] = self.username
        payload["password"] = self.password
        login_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Referer": login_url,
            "Origin": base_url,
        }

        # POST credentials (this is actual auth; 403 here can still be access or wrong credentials)
        r = None
        for attempt in range(max_retries):
            try:
                r = session.post(login_url, data=payload, headers=login_headers, timeout=self.request_timeout)
                r.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                status = _get_status(e)
                if attempt < max_retries - 1 and status in (403, 429):
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    print(f"  Login submit returned {status}, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                    print(f"  Login submit failed ({type(e).__name__}), retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise

        if r is None:
            raise RuntimeError("Failed to complete login submit after retries")
        if not ("Home | Compass" in r.text or "productNavBar" in r.text or "Compass.mfeConfig" in r.text):
            raise Exception("Login failed - wrong credentials or no authenticated content in response")
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
        page_response = self._request_with_retry(
            session, "GET", user_new_url,
            headers=page_headers, timeout=self.request_timeout,
        )
        self._human_delay(3, 1)  # Pause before API call (human-like)
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
        staff_response = self._request_with_retry(
            session, "POST", staff_url,
            headers=staff_headers, data="{}", timeout=self.request_timeout,
        )
        return staff_response.json()

    def get_student_data(self, session, max_retries=3, retry_delays=(10, 20, 40)):
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
        page_response = self._request_with_retry(
            session, "GET", form_group_url,
            headers=page_headers, timeout=self.request_timeout,
        )
        self._human_delay(3, 1)  # Pause before large API call (human-like)
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
        students_response = self._request_with_retry(
            session, "POST", students_url,
            max_retries=max_retries, retry_delays=retry_delays,
            headers=students_headers, data=payload, timeout=self.request_timeout,
        )
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
                response = self._fetch_photo_with_retry(photo_url)
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

    def get_staff_photos(self, limit=None, custom_dir=None, download=False, use_existing_session=False):
        print("=" * 50)
        print("GETTING STAFF PHOTOS")
        print("=" * 50)
        if not use_existing_session or not getattr(self, "session", None):
            print("Authenticating with Compass...")
            self.session = self.get_authenticated_session()
        else:
            print("Using existing session.")
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

    def get_student_photos(self, limit=None, custom_dir=None, save_debug=False, download=False, use_existing_session=False):
        print("=" * 50)
        print("GETTING STUDENT PHOTOS")
        print("=" * 50)
        if not use_existing_session or not getattr(self, "session", None):
            print("Authenticating with Compass...")
            self.session = self.get_authenticated_session()
        else:
            print("Using existing session.")
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
        # Auth once, then reuse session for staff and students
        print("Authenticating with Compass...")
        self.session = self.get_authenticated_session()
        staff_results = self.get_staff_photos(limit=staff_limit, custom_dir=staff_dir, download=download, use_existing_session=True)
        self._human_delay(5, 2)  # Pause between staff and student phases (human-like)
        student_results = self.get_student_photos(limit=student_limit, custom_dir=student_dir, save_debug=save_debug, download=download, use_existing_session=True)
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

    def get_single_photo(self, display_code, download=False, custom_dir=None):
        """
        Get a single photo by display code (staff or student).
        
        Args:
            display_code (str): The display code of the person (e.g., 'ABE', 'ALB0011')
            download (bool): Whether to download the photo to disk
            custom_dir (str): Custom directory to save photo (if download=True)
        
        Returns:
            dict: Photo information including URL, name, and optionally download stats
        """
        print(f"Looking for photo for display code: {display_code}")
        
        # Get authenticated session
        self.session = self.get_authenticated_session()
        
        # First try staff
        print("Checking staff members...")
        staff_data = self.get_staff_data(self.session)
        for staff_member in staff_data.get('d', []):
            if staff_member.get('displayCode', '').upper() == display_code.upper():
                pv = staff_member.get('pv', '')
                if pv and pv.strip():
                    person_info = {
                        'name': staff_member.get('n', 'Unknown'),
                        'displayCode': staff_member.get('displayCode', 'UNKNOWN'),
                        'pv': pv.strip(),
                        'type': 'staff'
                    }
                    return self._process_single_photo(person_info, download, custom_dir or self.staff_dir)
        
        # Then try students
        print("Checking students...")
        student_data = self.get_student_data(self.session)
        student_list = student_data.get('d', []) if 'd' in student_data else (student_data if isinstance(student_data, list) else [student_data])
        
        for student in student_list:
            if student.get('displayCode', '').upper() == display_code.upper():
                pv = student.get('pv', '') or student.get('photoUrl', '') or student.get('photo', '')
                if pv and pv.strip():
                    person_info = {
                        'name': student.get('n', student.get('name', 'Unknown')),
                        'displayCode': student.get('displayCode', student.get('code', 'UNKNOWN')),
                        'pv': pv.strip(),
                        'type': 'student'
                    }
                    return self._process_single_photo(person_info, download, custom_dir or self.student_dir)
        
        # Not found
        print(f"No photo found for display code: {display_code}")
        return None

    def _process_single_photo(self, person_info, download, photos_dir):
        """Helper method to process a single photo."""
        base_url = f"{self.base_url}/download/secure/cdn/full/"
        photo_url = base_url + person_info['pv']
        
        result = {
            'name': person_info['name'],
            'displayCode': person_info['displayCode'],
            'type': person_info['type'],
            'photo_url': photo_url,
            'pv': person_info['pv']
        }
        
        if download:
            print(f"Downloading photo for {person_info['name']} ({person_info['displayCode']})...")
            os.makedirs(photos_dir, exist_ok=True)
            
            # Always download without checking existing files
            filename = self._generate_filename(person_info)
            filepath = os.path.join(photos_dir, filename)
            
            # Find and remove any existing files that start with the same display code
            existing_files = glob.glob(os.path.join(photos_dir, f"{person_info['displayCode']}_*.jpg"))
            for existing_file in existing_files:
                os.remove(existing_file)
                existing_filename = os.path.basename(existing_file)
                print(f"  Removed existing file: {existing_filename}")
            
            try:
                response = self._fetch_photo_with_retry(photo_url)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"  [OK] Downloaded: {filename}")
                
                result['download_stats'] = {
                    'total_processed': 1,
                    'downloaded': 1,
                    'updated': 0,
                    'skipped': 0,
                    'failed': 0
                }
                result['file_path'] = filepath
            except Exception as e:
                print(f"  [ERROR] Failed to download: {e}")
                result['download_stats'] = {
                    'total_processed': 1,
                    'downloaded': 0,
                    'updated': 0,
                    'skipped': 0,
                    'failed': 1
                }
        else:
            print(f"Found photo for {person_info['name']} ({person_info['displayCode']})")
            print(f"URL: {photo_url}")
        
        return result

    def _generate_filename(self, person_info):
        """Generate filename for a person's photo."""
        safe_name = "".join(c for c in person_info['displayCode'] if c.isalnum() or c in (' ', '-', '_')).strip()
        timestamp = self.extract_timestamp_from_pv(person_info['pv']) or "unknown"
        guid = person_info['pv'][:8]
        return f"{safe_name}_{guid}_{timestamp}.jpg"


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


def get_single_photo(username, password, display_code, download=False, custom_dir=None, base_url=None):
    """
    Get a single photo by display code (staff or student).
    
    Args:
        username (str): Compass username
        password (str): Compass password
        display_code (str): The display code of the person (e.g., 'ABE', 'ALB0011')
        download (bool): Whether to download the photo to disk
        custom_dir (str): Custom directory to save photo (if download=True)
        base_url (str): Compass base URL
    
    Returns:
        dict: Photo information including URL, name, and optionally download stats
    """
    compass = CompassPhoto(username, password, base_url=base_url)
    return compass.get_single_photo(display_code, download=download, custom_dir=custom_dir)
