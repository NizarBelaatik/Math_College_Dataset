import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import requests
import os
import re
from urllib.parse import urlparse, urljoin

from config import BASE_DATA_DIR , BASE_PDF_DOWNLOAD_DIR


def get_filename_from_url(url: str) -> str:
    """
    Extracts a clean filename from a URL, removing language codes and 'non-corriges'.
    Example: http://example.com/path/to/document-fr.pdf?param=value -> document.pdf
    """
    path = urlparse(url).path
    filename = os.path.basename(path)

    # Remove language codes like '-fr', '-en', etc.
    filename = re.sub(r'-\w{2}(?=\.)', '', filename)

    # Remove 'non-corriges' from the filename
    filename = filename.replace('-non-corriges', '')

    return filename.split("?")[0]  # Remove query parameters


# In pdf_downloader.py, modify the download_pdf function:
def download_pdf(url: str, filepath: str, original_name: str = None) -> bool:
    """Downloads a PDF from a URL and saves it to a specified filepath,
    attempting to create a cleaner filename.
    """
    if not url:
        print(f"Skipping download: URL is empty.")
        return False

    # Use original_name if provided, otherwise extract and clean from URL
    if original_name:
        filename = original_name
    else:
        filename = get_filename_from_url(url)

        # Further cleaning: remove "correction" or "exercices" and their separators
        filename = filename.replace('-correction', '')
        filename = filename.replace('-exercices', '')
        filename = filename.replace('_correction', '')
        filename = filename.replace('_exercices', '')

        # Remove duplicate separators if any
        filename = filename.replace('__', '_')
        filename = filename.replace('--', '-')

        # Remove trailing hyphens or underscores
        filename = filename.rstrip('-_')

        # Ensure the filename still has the .pdf extension
        if not filename.endswith('.pdf'):
            filename += '.pdf'

    full_path = os.path.join(os.path.dirname(filepath), filename)

    if os.path.exists(full_path):
        print(f"File already exists, skipping: {full_path}")
        return True

    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[*] Downloaded {url} to {full_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[-] Error downloading {url}: {e}")
        return False
    except Exception as e:
        print(f"[-] An unexpected error occurred downloading {url}: {e}")
        return False


def download_alloschool_pdfs(grade_level_folder_name: str):

    input_file = os.path.join(BASE_DATA_DIR, f'{grade_level_folder_name}_lessons_exercises.json')

    # Define grade-specific download directories
    grade_pdf_dir = os.path.join(BASE_PDF_DOWNLOAD_DIR, grade_level_folder_name)
    cours_dir = os.path.join(grade_pdf_dir, "cours")
    exercice_dir = os.path.join(grade_pdf_dir, "exercice")
    correction_dir = os.path.join(grade_pdf_dir, "correction")

    os.makedirs(cours_dir, exist_ok=True)
    os.makedirs(exercice_dir, exist_ok=True)
    os.makedirs(correction_dir, exist_ok=True)

    # Setup Chrome in headless mode for initial page parsing
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    print(f"\n--- Downloading PDFs for {grade_level_folder_name} ---")
    try:
        # Load the lessons data
        if not os.path.exists(input_file):
            print(f"Error: Input file not found at {input_file}. Please run the scraper first.")
            return

        with open(input_file, 'r', encoding='utf-8') as f:
            lessons_data = json.load(f)

        if not lessons_data:
            print(f"No lesson data found in {input_file} to download.")
            return

        print(f"[*] Starting PDF download for {len(lessons_data)} lessons for {grade_level_folder_name}...")

        for i, lesson in enumerate(lessons_data):
            lesson_name = lesson.get('lesson_name', f"Lesson {i+1}")
            print(f"\n--- Processing Lesson: {lesson_name} ({grade_level_folder_name}) ---")

            files_to_download = {
                'cours': {'url': lesson.get('cours'), 'dir': cours_dir},
                'exercice': {'url': lesson.get('exercice'), 'dir': exercice_dir},
                'correction': {'url': lesson.get('correction'), 'dir': correction_dir},
            }

            for file_type, info in files_to_download.items():
                target_url = info['url']
                target_dir = info['dir']

                if not target_url:
                    print(f"    [ ] No {file_type} URL found for {lesson_name}, skipping.")
                    continue

                print(f"    [*] Visiting {file_type} page: {target_url}")
                try:
                    driver.get(target_url)
                    time.sleep(3)  # Give time for page to load

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    download_button = soup.select_one('a.btn.btn-lg.btn-primary')

                    actual_download_url = None
                    if download_button:
                        actual_download_url = download_button.get('href')

                    if actual_download_url:
                        if not actual_download_url.startswith('http'):
                            actual_download_url = urljoin(driver.current_url, actual_download_url)

                        filename = get_filename_from_url(actual_download_url)
                        filepath = os.path.join(target_dir, filename)
                        print(f"        [*] Found actual download link: {actual_download_url}")
                        download_pdf(actual_download_url, filepath)
                    else:
                        print(f"        [-] No download button found for {file_type} at {target_url}")

                except Exception as e:
                    print(f"    [-] Error processing {file_type} for {lesson_name} ({target_url}): {e}")

    except Exception as e:
        print(f"An error occurred during the PDF download process for {grade_level_folder_name}: {e}")
    finally:
        driver.quit()
        print(f"\n[*] PDF download process finished for {grade_level_folder_name}.")

if __name__ == "__main__":
    # Example usage for 2AC if run standalone
    download_alloschool_pdfs('2AC')
