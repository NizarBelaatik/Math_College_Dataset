import json
import time
import requests
import os
import re
from urllib.parse import urlparse, urljoin

from config import BASE_DATA_DIR, BASE_PDF_DOWNLOAD_DIR

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

def download_pdf(url: str, filepath: str, original_name: str = None) -> bool:
    """
    Downloads a PDF from the given URL to the specified filepath.
    Uses original_name if provided, otherwise derives a clean filename from the URL.
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
    """
    Downloads question and answer PDFs for a given grade level from a JSON file.
    Saves PDFs to grade-specific subdirectories under BASE_PDF_DOWNLOAD_DIR.

    Args:
        grade_level_folder_name (str): Folder name (e.g., '1AC', '2AC') for the input JSON and output PDFs.
    """
    input_file = os.path.join(BASE_DATA_DIR, f'{grade_level_folder_name}_questions_answers.json')

    # Define grade-specific download directories
    grade_pdf_dir = os.path.join(BASE_PDF_DOWNLOAD_DIR, grade_level_folder_name)
    exercice_dir = os.path.join(grade_pdf_dir, "exercice")
    correction_dir = os.path.join(grade_pdf_dir, "correction")

    os.makedirs(exercice_dir, exist_ok=True)
    os.makedirs(correction_dir, exist_ok=True)

    print(f"\n--- Downloading PDFs for {grade_level_folder_name} ---")
    try:
        # Load the questions and answers data
        if not os.path.exists(input_file):
            print(f"Error: Input file not found at {input_file}. Please run the scraper first.")
            return

        with open(input_file, 'r', encoding='utf-8') as f:
            lessons_data = json.load(f)

        if not lessons_data:
            print(f"No data found in {input_file} to download.")
            return

        print(f"[*] Starting PDF download for {len(lessons_data)} question-answer pairs for {grade_level_folder_name}...")

        for i, lesson in enumerate(lessons_data):
            lesson_name = lesson.get('lesson_name', f"Lesson {i+1}")
            exercice_id = lesson.get('exercice', f"exercice {i+1}")
            print(f"\n--- Processing Lesson: {lesson_name} - {exercice_id} ({grade_level_folder_name}) ---")

            # Clean lesson_name for filename (replace spaces and special characters)
            clean_lesson_name = re.sub(r'[^\w\s-]', '', lesson_name).replace(' ', '_')
            clean_exercice_id = re.sub(r'[^\w\s-]', '', exercice_id).replace(' ', '_')

            files_to_download = [
                {
                    'type': 'question',
                    'url': lesson.get('question'),
                    'dir': exercice_dir,
                    'name': f"{clean_lesson_name}_{clean_exercice_id}.pdf"
                },
                {
                    'type': 'answer',
                    'url': lesson.get('answer'),
                    'dir': correction_dir,
                    'name': f"{clean_lesson_name}_{clean_exercice_id}_correction.pdf"
                }
            ]

            for file_info in files_to_download:
                file_type = file_info['type']
                target_url = file_info['url']
                target_dir = file_info['dir']
                target_name = file_info['name']

                if not target_url:
                    print(f"    [ ] No {file_type} URL found for {lesson_name} - {exercice_id}, skipping.")
                    continue

                print(f"    [*] Processing {file_type} URL: {target_url}")
                try:
                    filepath = os.path.join(target_dir, target_name)
                    download_pdf(target_url, filepath, target_name)
                except Exception as e:
                    print(f"    [-] Error processing {file_type} for {lesson_name} - {exercice_id} ({target_url}): {e}")

    except Exception as e:
        print(f"An error occurred during the PDF download process for {grade_level_folder_name}: {e}")
    finally:
        print(f"\n[*] PDF download process finished for {grade_level_folder_name}.")

if __name__ == "__main__":
    # Example usage for 2AC if run standalone
    download_alloschool_pdfs('2AC')