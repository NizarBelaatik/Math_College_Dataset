import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

# Setup Chrome in headless mode
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# Load the page
url = 'https://www.alloschool.com/course/mathematiques-2eme-annee-college#!'
driver.get(url)
time.sleep(3)

# Parse with BeautifulSoup
soup = BeautifulSoup(driver.page_source, 'html.parser')
lessons_data = []

# Loop through all lessons
lessons = soup.select('ul.ul-timeline > li.lesson')

for lesson in lessons:
    # Check for red icon
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

    valid_links = []
    valid_links_cours=[]
    
    elements_ul_list = elements_ul.select('li.element')
    for el in elements_ul_list:
            a_tag = el.select_one('a')
            if a_tag:
                href = a_tag.get('href', '')
                if href.startswith("http"):
                    valid_links_cours.append(href)
                    break

    for el in elements_ul_list:
        if 'Exercices' in el.text: 
            a_tag = el.select_one('a')
            if a_tag:
                href = a_tag.get('href', '')
                if href.startswith("http"):
                    valid_links.append(href)
                if len(valid_links) == 2:
                    break

    # Only store if both exercice and correction are found
    if len(valid_links) == 2:
        lessons_data.append({
            "lesson_name": lesson_title,
            "cours":valid_links_cours[0],
            #"exercice": valid_links_exercice[0],
            "exercice": valid_links[0],
            "correction": valid_links[1]
        })

# Save the output
#with open('lessons_exercises.json', 'w', encoding='utf-8') as f:
#    json.dump(lessons_data, f, ensure_ascii=False, indent=4)

driver.quit()
