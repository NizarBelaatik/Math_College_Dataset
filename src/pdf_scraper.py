import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urlparse, urljoin
import re

from config import BASE_SCRAPED_LINKS_DIR

def get_file_url(target_url, driver):
    try:
        driver.get(target_url)
        time.sleep(2)  # Give time for page to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        download_button = soup.select_one('a.btn.btn-lg.btn-primary')
        actual_download_url = None
        if download_button:
            actual_download_url = download_button.get('href')
        if actual_download_url:
            if not actual_download_url.startswith('http'):
                actual_download_url = urljoin(target_url, actual_download_url)
        return actual_download_url
    except Exception as e:
        print(f"Error in get_file_url: {target_url} - {e}")
        return None

def scrape_alloschool_links(url: str, output_folder_name: str):
    """
    Scrapes exercise and correction PDF links from Alloschool URL, handling multiple pairs.
    Saves links to a grade-specific JSON file within BASE_SCRAPED_LINKS_DIR as a question-answer dataset.

    Args:
        url (str): The URL of the Alloschool page to scrape.
        output_folder_name (str): Folder name (e.g., '1AC', '2AC') for the output JSON file.
    """
    output_file = os.path.join(BASE_SCRAPED_LINKS_DIR, f'{output_folder_name}_questions_answers.json')
    os.makedirs(BASE_SCRAPED_LINKS_DIR, exist_ok=True)

    # Setup Chrome in headless mode
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    dataset = []

    print(f"\n--- Scraping for {output_folder_name} from {url} ---")
    try:
        driver.get(url)
        time.sleep(3)  # Wait for dynamic content
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all lessons
        lessons = soup.select('ul.ul-timeline > li.lesson')
        print(f"[*] Found {len(lessons)} potential lessons.")

        for lesson in lessons:
            # Skip if no content (red icon check)
            icon = lesson.select_one('div.icon[style*="background-color:#c62828"]')
            if not icon:
                continue

            # Get lesson title
            title_tag = lesson.select_one('div.t-h > h2')
            lesson_title = title_tag.get_text(strip=True) if title_tag else "Unknown"

            # Get all elements in the lesson
            elements_ul = lesson.select_one('ul.section-elements')
            if not elements_ul:
                continue

            elements = elements_ul.select('li.element')
            exercise_correction_pairs = []

            # Collect all potential exercise and correction links
            for el in elements:
                a_tag = el.select_one('a')
                if not a_tag:
                    continue
                href = a_tag.get('href', '')
                if not href.startswith('http'):
                    continue
                text = el.get_text(strip=True).lower()

                # Skip course links
                if 'cours' in text:
                    continue

                # Store link with its text
                exercise_correction_pairs.append((href, text))

            # Pair exercises with corrections
            paired_entries = []
            used_indices = set()
            for i, (href, text) in enumerate(exercise_correction_pairs):
                if i in used_indices:
                    continue
                text_lower = text.lower()

                # Check if this is an exercise
                is_exercise = (
                    'exercice' in text_lower or
                    'non corrigé' in text_lower or
                    'série d\'exercices' in text_lower or
                    'construction' in text_lower or
                    'construire' in text_lower or
                    'axes de symétrie' in text_lower
                ) and not (
                    'corrigé' in text_lower or
                    'correction' in text_lower or
                    'solution' in text_lower
                )

                if is_exercise:
                    # Look for corresponding correction
                    correction_href = None
                    correction_text = None
                    for j, (next_href, next_text) in enumerate(exercise_correction_pairs):
                        if j <= i or j in used_indices:
                            continue
                        next_text_lower = next_text.lower()
                        is_correction = (
                            'corrigé' in next_text_lower or
                            'correction' in next_text_lower or
                            'solution' in next_text_lower
                        )
                        # Ensure correction matches exercise (e.g., same series number)
                        if is_correction:
                            # Extract series number if present
                            exercise_series = re.search(r'(série\s*d\'exercices\s*\d+)|(\d+)', text_lower)
                            correction_series = re.search(r'(corrigé\s*série\s*d\'exercices\s*\d+)|(\d+)', next_text_lower)
                            if exercise_series and correction_series:
                                if exercise_series.group(0) in correction_series.group(0):
                                    correction_href = next_href
                                    correction_text = next_text
                                    used_indices.add(j)
                                    break
                            elif text_lower.replace('exercices', '').strip() in next_text_lower.replace('corrigé', '').strip():
                                correction_href = next_href
                                correction_text = next_text
                                used_indices.add(j)
                                break
                            elif 'corrigé' in next_text_lower and not exercise_series:
                                correction_href = next_href
                                correction_text = next_text
                                used_indices.add(j)
                                break

                    if correction_href:
                        paired_entries.append({
                            'exercise_href': href,
                            'exercise_text': text,
                            'correction_href': correction_href,
                            'correction_text': correction_text
                        })
                        used_indices.add(i)

            # Process each pair
            for idx, pair in enumerate(paired_entries, 1):
                exercise_pdf = get_file_url(pair['exercise_href'], driver)
                correction_pdf = get_file_url(pair['correction_href'], driver)

                if exercise_pdf and correction_pdf:
                    # Create unique lesson name
                    unique_lesson_name = f"{lesson_title} - Exercice {idx}" if len(paired_entries) > 1 else lesson_title
                    dataset.append({
                        'lesson_name': lesson_title,
                        'exercice':f"exercice {idx}",
                        'question': exercise_pdf,
                        'answer': correction_pdf
                    })
                    print(f"    [+] Paired: {unique_lesson_name} (Q: {pair['exercise_text']}, A: {pair['correction_text']})")
                else:
                    print(f"    [-] Failed to get PDFs for: {lesson_title} (Ex: {pair['exercise_text']})")

    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

    # Save dataset
    if dataset:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)
        print(f"[*] Saved {len(dataset)} question-answer pairs to '{output_file}'")
    else:
        print(f"[*] No pairs found to save to '{output_file}'.")

if __name__ == "__main__":
    scrape_alloschool_links(
        'https://www.alloschool.com/course/mathematiques-2eme-annee-college#!',
        '2AC'
    )