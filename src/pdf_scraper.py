import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import os
from urllib.parse import urlparse, urljoin

from config import BASE_DATA_DIR



def get_file_url(target_url, driver):
    """
    Extracts the actual download URL from a given page using Selenium.

    Args:
        target_url (str): The URL of the page containing the download link.
        driver (webdriver):  The Selenium webdriver instance.

    Returns:
        str: The actual download URL, or None if not found.
    """
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
                actual_download_url = urljoin(target_url, actual_download_url)  # Use target_url instead of driver.current_url
        return actual_download_url
    except Exception as e:
        print("Error in get_file_url:", e)
        return None


def scrape_alloschool_links(url: str, output_folder_name: str):
    """
    Scrapes lesson, exercise, and correction PDF links from the specified Alloschool URL.
    Saves links to a grade-specific JSON file within the BASE_DATA_DIR.

    Args:
        url (str): The URL of the Alloschool page to scrape.
        output_folder_name (str): The name of the folder (e.g., '1AC', '2AC')
                                  which will be used for the output JSON file.
    """
    output_file = os.path.join(BASE_DATA_DIR, f'{output_folder_name}_lessons_exercises.json')
    os.makedirs(BASE_DATA_DIR, exist_ok=True)

    # Setup Chrome in headless mode - Initialize driver only once
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    lessons_data = []

    print(f"\n--- Scraping for {output_folder_name} from {url} ---")
    try:
        print(f"[*] Visiting URL: {url}")
        driver.get(url)
        time.sleep(3)  # Give time for the page to load dynamic content

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Loop through all lessons
        lessons = soup.select('ul.ul-timeline > li.lesson')
        print(f"[*] Found {len(lessons)} potential lessons on the page.")

        for lesson in lessons:
            # Check for red icon indicating available content
            icon = lesson.select_one('div.icon[style*="background-color:#c62828"]')
            if not icon:
                continue

            # Get lesson title from <div class="t-h"> > <h2>
            title_tag = lesson.select_one('div.t-h > h2')
            lesson_title = title_tag.get_text(strip=True) if title_tag else "Unknown"

            # Get all <a> elements inside <ul class="section-elements">
            elements_ul = lesson.select_one('ul.section-elements')
            if not elements_ul:
                continue

            cours_link = None
            exercice_link = None
            correction_link = None

            elements_ul_list = elements_ul.select('li.element')

            # Find the course link
            for el in elements_ul_list:
                a_tag = el.select_one('a')
                if a_tag and 'Cours' in el.text:
                    href = a_tag.get('href', '')
                    if href.startswith("http"):
                        cours_link = href
                        break

            # Find exercise and correction links
            temp_links = []
            for el in elements_ul_list:
                a_tag = el.select_one('a')
                if a_tag:
                    href = a_tag.get('href', '')
                    if href.startswith("http"):
                        if 'Exercices' in el.text:
                            # Prioritize link with 'Exercices' text if it's the first encountered
                            if not exercice_link:
                                exercice_link = href
                            else: # If a second link with 'Exercices' text appears, it's likely the correction
                                correction_link = href
                        elif 'Correction' in el.text and not correction_link: # Explicit correction
                             correction_link = href
                        
                        # Fallback for pages where "Exercices" and "Correction" are just links without explicit text
                        # Accumulate all links in the relevant section and then assign
                        if 'Exercices' in el.text or 'Correction' in el.text or 'Fiche' in el.text or 'Solution' in el.text:
                            temp_links.append((href, el.text)) # Store (link, text) to analyze

            # More robust assignment from temp_links
            found_exercice = False
            found_correction = False
            for href, text_content in temp_links:
                text_content_lower = text_content.lower()
                if "exercice" in text_content_lower and not found_exercice:
                    exercice_link = href
                    found_exercice = True
                elif ("correction" in text_content_lower or "corrigé" in text_content_lower or "solution" in text_content_lower) and not found_correction:
                    correction_link = href
                    found_correction = True
                
                if found_exercice and found_correction:
                    break
            
            # If still not found, a final fallback based on order
            if not exercice_link and not correction_link and len(temp_links) >= 2:
                exercice_link = temp_links[0][0]
                correction_link = temp_links[1][0]


            if cours_link and exercice_link and correction_link:
                cours_pdf_link = get_file_url(cours_link, driver)
                exercice_pdf_link = get_file_url(exercice_link, driver)
                correction_pdf_link = get_file_url(correction_link, driver)

                lessons_data.append({
                    "lesson_name": lesson_title,
                    "cours": cours_pdf_link,
                    "exercice": exercice_pdf_link,
                    "correction": correction_pdf_link
                })
                
                
                print(f"    [+] Found all links for: {lesson_title}")
            else:
                print(f"    [-] Could not find all links for: {lesson_title}. "
                      f"Cours: {cours_link}, Exercice: {exercice_link}, Correction: {correction_link}")

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    finally:
        driver.quit()  # Ensure the driver is closed

    # Save the output
    if lessons_data:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(lessons_data, f, ensure_ascii=False, indent=4)
        print(f"[*] Successfully saved {len(lessons_data)} lesson link sets to '{output_file}'")
    else:
        print(f"[*] No lesson links found to save to '{output_file}'.")

if __name__ == "__main__":
    # Example usage for 2AC if run standalone
    scrape_alloschool_links(
        'https://www.alloschool.com/course/mathematiques-2eme-annee-college#!',
        '2AC'
    )