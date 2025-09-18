#!/usr/bin/env python3
"""
CompassPhoto - A unified module for downloading photos from Compass Education.

Usage:
    from compassphoto import CompassPhoto
    
    # Initialize with credentials
    compass = CompassPhoto(username="your_username", password="your_password")
    
    # Download photos
    compass.get_staff_photos()
    compass.get_student_photos()
    compass.get_all_photos()
"""

import json
import os
import requests
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re
import glob
from dotenv import load_dotenv
from datetime import datetime


class CompassPhoto:
    """Unified class for downloading photos from Compass Education"""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize CompassPhoto with credentials.
        
        Args:
            username (str): Compass username. If None, loads from environment.
            password (str): Compass password. If None, loads from environment.
        """
        if username is None or password is None:
            load_dotenv()
            self.username = os.getenv("COMPASS_USERNAME")
            self.password = os.getenv("COMPASS_PASSWORD")
        else:
            self.username = username
            self.password = password
        
        if not self.username or not self.password:
            raise ValueError("Username and password must be provided or set in environment variables")
        
        # Default directories
        self.staff_dir = "compass_photos/staff"
        self.student_dir = "compass_photos/students"
        
        # Create directories
        os.makedirs(self.staff_dir, exist_ok=True)
        os.makedirs(self.student_dir, exist_ok=True)
    
    def extract_timestamp_from_pv(self, pv_string):
        """Extract timestamp from pv string like 'guid_2502250258AM?requestguid=...'"""
        if not pv_string:
            return None
        
        # Look for pattern like "2502250258AM" in the pv string
        timestamp_match = re.search(r'_(\d{10}[AP]M)', pv_string)
        if timestamp_match:
            return timestamp_match.group(1)
        return None

    def should_update_photo(self, photos_dir, display_code, current_pv):
        """Check if photo should be updated based on timestamp in pv"""
        current_timestamp = self.extract_timestamp_from_pv(current_pv)
        if not current_timestamp:
            return True, None  # No timestamp, download anyway
        
        # Find existing files for this person
        pattern = os.path.join(photos_dir, f"{display_code}_*.jpg")
        existing_files = glob.glob(pattern)
        
        if not existing_files:
            return True, None  # No existing file
        
        # Check if any existing file has the same timestamp
        for existing_file in existing_files:
            filename = os.path.basename(existing_file)
            # Extract timestamp from filename like "DISPLAYCODE_guid_timestamp.jpg"
            if current_timestamp in filename:
                return False, existing_file  # Same timestamp, no update needed
        
        # Different timestamp, need to update
        return True, existing_files[0] if existing_files else None

    def get_authenticated_session(self):
        """Create an authenticated session with Compass"""
        base_url = "https://mckinnonsc-vic.compass.education"
        session = cloudscraper.create_scraper()
        
        # Get login page first
        login_url = f"{base_url}/login.aspx?sessionstate=disabled"
        login_get_response = session.get(login_url, timeout=15)
        login_get_response.raise_for_status()
        
        # Parse the login form to extract required fields
        soup = BeautifulSoup(login_get_response.text, 'html.parser')
        form = soup.find('form')
        
        if not form:
            raise Exception("No login form found")
        
        # Extract all form fields
        payload = {}
        for input_field in form.find_all('input'):
            name = input_field.get('name')
            value = input_field.get('value', '')
            if name:
                payload[name] = value
        
        # Set the username and password
        payload['username'] = self.username
        payload['password'] = self.password
        
        login_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Referer": login_url,
            "Origin": base_url
        }

        # Submit login
        r = session.post(login_url, data=payload, headers=login_headers, timeout=15)
        r.raise_for_status()
        
        # Check if login was successful
        if not ("Home | Compass" in r.text or "productNavBar" in r.text or "Compass.mfeConfig" in r.text):
            raise Exception("Login failed - no authenticated content found")
        
        return session
    
    def get_staff_data(self, session):
        """Get staff data from Compass API"""
        base_url = "https://mckinnonsc-vic.compass.education"
        
        # Navigate to UserNew page to get fresh tokens
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
        
        # Wait for page to load
        time.sleep(3)
        
        # Make GetStaff request with fresh session
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
        """Get student data from Compass API"""
        base_url = "https://mckinnonsc-vic.compass.education"
        
        # Navigate to FormGroup page to get fresh tokens
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
        
        # Wait for page to load
        time.sleep(3)
        
        # Make GetAllStudentsBasic request with fresh session
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
        
        # The payload appears to be 31 bytes based on your headers
        payload = '{"includePhotos": true}'  # This is likely what triggers photo URLs
        
        students_response = session.post(students_url, headers=students_headers, data=payload, timeout=15)
        students_response.raise_for_status()
        
        return students_response.json()
    
    def download_photos(self, people_with_photos, photos_dir, people_type="photos", limit=None):
        """Generic method to download photos for a list of people"""
        base_url = "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/"
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
                
                # Create safe filename with timestamp
                safe_name = "".join(c for c in person['displayCode'] if c.isalnum() or c in (' ', '-', '_')).strip()
                timestamp = self.extract_timestamp_from_pv(person['pv']) or "unknown"
                guid = person['pv'][:8]  # First 8 chars of GUID
                filename = f"{safe_name}_{guid}_{timestamp}.jpg"
                filepath = os.path.join(photos_dir, filename)
                
                # Check if we need to update this photo
                should_update, existing_file = self.should_update_photo(photos_dir, safe_name, person['pv'])
                
                if not should_update:
                    print(f"[{i+1}/{total_photos}] Skipping {person['displayCode']}: up to date ({timestamp})")
                    skipped += 1
                    continue
                
                if existing_file:
                    print(f"[{i+1}/{total_photos}] Updating {person['name']} ({person['displayCode']}) - photo changed")
                    # Remove old file
                    os.remove(existing_file)
                    action_type = "updated"
                else:
                    print(f"[{i+1}/{total_photos}] Downloading {person['name']} ({person['displayCode']}) - new photo")
                    action_type = "downloaded"
                
                # Download the image
                response = session.get(photo_url, timeout=30)
                response.raise_for_status()
                
                # Save the image
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                if action_type == "updated":
                    updated += 1
                else:
                    downloaded += 1
                print(f"  [OK] Saved as {filename}")
                
                # Progress update every 25 downloads
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
        """
        Get staff profile photos.
        
        Args:
            limit (int, optional): Limit number of photos to process
            custom_dir (str, optional): Custom directory to save photos (if download=True)
            download (bool): Whether to download photos or just return URLs (default: False)
            
        Returns:
            dict: JSON map of {"CODE": "URL"} or download statistics if download=True
        """
        print("=" * 50)
        print("GETTING STAFF PHOTOS")
        print("=" * 50)
        
        # Get authenticated session
        print("Authenticating with Compass...")
        self.session = self.get_authenticated_session()
        
        # Get staff data
        print("Getting staff data...")
        data = self.get_staff_data(self.session)
        
        # Extract staff with photos
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
        
        # Apply limit if specified
        if limit:
            staff_with_photos = staff_with_photos[:limit]
        
        # Create JSON map of CODE -> URL
        base_url = "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/"
        staff_map = {}
        for staff in staff_with_photos:
            staff_map[staff['displayCode']] = base_url + staff['pv']
        
        # If download is requested, download the photos
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
        """
        Get student profile photos.
        
        Args:
            limit (int, optional): Limit number of photos to process
            custom_dir (str, optional): Custom directory to save photos (if download=True)
            save_debug (bool): Save API response for debugging
            download (bool): Whether to download photos or just return URLs (default: False)
            
        Returns:
            dict: JSON map of {"CODE": "URL"} or download statistics if download=True
        """
        print("=" * 50)
        print("GETTING STUDENT PHOTOS")
        print("=" * 50)
        
        # Get authenticated session
        print("Authenticating with Compass...")
        self.session = self.get_authenticated_session()
        
        # Get student data
        print("Getting student data...")
        data = self.get_student_data(self.session)
        
        # Save debug files if requested
        if save_debug:
            with open('students_response.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(data))
            with open('students_response_pretty.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Extract students with photos
        students_with_photos = []
        
        # Check if it's similar structure to staff data
        if 'd' in data:
            student_list = data['d']
        else:
            student_list = data if isinstance(data, list) else [data]
        
        for student in student_list:
            # Look for photo-related fields
            pv = student.get('pv', '') or student.get('photoUrl', '') or student.get('photo', '')
            
            if pv and pv.strip():
                students_with_photos.append({
                    'name': student.get('n', student.get('name', 'Unknown')),
                    'displayCode': student.get('displayCode', student.get('code', 'UNKNOWN')),
                    'pv': pv.strip()
                })
        
        print(f"Found {len(students_with_photos)} students with profile photos")
        
        # Apply limit if specified
        if limit:
            students_with_photos = students_with_photos[:limit]
        
        # Create JSON map of CODE -> URL
        base_url = "https://mckinnonsc-vic.compass.education/download/secure/cdn/full/"
        student_map = {}
        for student in students_with_photos:
            student_map[student['displayCode']] = base_url + student['pv']
        
        # If download is requested, download the photos
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
        """
        Get both staff and student photos.
        
        Args:
            staff_limit (int, optional): Limit number of staff photos
            student_limit (int, optional): Limit number of student photos
            staff_dir (str, optional): Custom directory for staff photos (if download=True)
            student_dir (str, optional): Custom directory for student photos (if download=True)
            save_debug (bool): Save debug files for student photos
            download (bool): Whether to download photos or just return URLs (default: False)
            
        Returns:
            dict: Combined JSON maps and/or download statistics
        """
        print("=" * 60)
        print("    COMPASS PHOTO DOWNLOADER - ALL USERS")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        start_time = datetime.now()
        
        # Get staff photos
        staff_results = self.get_staff_photos(limit=staff_limit, custom_dir=staff_dir, download=download)
        
        # Get student photos
        student_results = self.get_student_photos(limit=student_limit, custom_dir=student_dir, save_debug=save_debug, download=download)
        
        # Print summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 50)
        print("FINAL SUMMARY")
        print("=" * 50)
        print(f"Total Duration: {duration}")
        print()
        
        # Handle different return formats based on download parameter
        if download:
            # Both results contain download statistics
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
            
            # Calculate totals for download stats
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
            # Both results are JSON maps
            print("STAFF PHOTOS:")
            if staff_results:
                print(f"  Found {len(staff_results)} staff members with photos")
            
            print("\nSTUDENT PHOTOS:")
            if student_results:
                print(f"  Found {len(student_results)} students with photos")
            
            print(f"\nTotal photos found: {len(staff_results) + len(student_results)}")
        
        print(f"\nCompleted at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        return {
            'staff': staff_results,
            'student': student_results,
            'duration': duration
        }


# Convenience functions for direct usage
def get_staff_photos(username, password, limit=None, custom_dir=None, download=False):
    """Convenience function to get staff photos"""
    compass = CompassPhoto(username, password)
    return compass.get_staff_photos(limit=limit, custom_dir=custom_dir, download=download)


def get_student_photos(username, password, limit=None, custom_dir=None, save_debug=False, download=False):
    """Convenience function to get student photos"""
    compass = CompassPhoto(username, password)
    return compass.get_student_photos(limit=limit, custom_dir=custom_dir, save_debug=save_debug, download=download)


def get_all_photos(username, password, staff_limit=None, student_limit=None, 
                  staff_dir=None, student_dir=None, save_debug=False, download=False):
    """Convenience function to get all photos"""
    compass = CompassPhoto(username, password)
    return compass.get_all_photos(staff_limit=staff_limit, student_limit=student_limit,
                                 staff_dir=staff_dir, student_dir=student_dir, save_debug=save_debug, download=download)


if __name__ == "__main__":
    # Example usage when run directly
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python compassphoto.py <username> <password> [staff|student|all] [download]")
        print("  download: optional, set to 'true' to download photos, defaults to false (URLs only)")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "all"
    download = len(sys.argv) > 4 and sys.argv[4].lower() == 'true'
    
    compass = CompassPhoto(username, password)
    
    if mode == "staff":
        result = compass.get_staff_photos(download=download)
        if not download:
            print(f"Staff photo URLs: {result}")
    elif mode == "student":
        result = compass.get_student_photos(download=download)
        if not download:
            print(f"Student photo URLs: {result}")
    else:
        result = compass.get_all_photos(download=download)
        if not download:
            print(f"All photo URLs: {result}")
