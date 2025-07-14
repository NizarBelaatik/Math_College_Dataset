import os
import sys
from config import BASE_SCRAPED_LINKS_DIR , BASE_PDF_DOWNLOAD_DIR , OUTPUT_DIR 
# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pdf_scraper import scrape_alloschool_links
from pdf_downloader import download_alloschool_pdfs

from pdf_text_extractor import create_dataset_from_pdfs, PDF_ROOT_DIR as EXTRACTOR_PDF_ROOT_DIR, FULL_OUTPUT_FILE as EXTRACTOR_OUTPUT_FILE
from get_correction_using_ai import generate_dataset

# Define the grade levels and their corresponding Alloschool URLs
GRADE_LEVELS = {
    '1AC': 'https://www.alloschool.com/course/mathematiques-1ere-annee-college#!',
    '2AC': 'https://www.alloschool.com/course/mathematiques-2eme-annee-college#!',
    '3AC': 'https://www.alloschool.com/course/mathematiques-3eme-annee-college#!',
}

def scrap_download():
    # Step 1 & 2: Process each grade level
    for grade_folder_name, url in GRADE_LEVELS.items():
        print(f"\n--- Processing Grade Level: {grade_folder_name} ---")
        
        # Scrape links
        print("Scraping PDF links...")
        scrape_alloschool_links(url, grade_folder_name)
        
        # Download PDFs
        print("Downloading PDFs...")
        download_alloschool_pdfs(grade_folder_name)
        
        
def main():
    print("--- Starting the Multi-Grade Math PDF Data Pipeline ---")
    # Ensure output directories exist
    os.makedirs(BASE_SCRAPED_LINKS_DIR, exist_ok=True)
    os.makedirs(BASE_PDF_DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1 & 2: Process each grade level
    scrap_download()
    

    # Step 3: Create dataset 
    print("\n--- Creating unified dataset ---")
    create_dataset_from_pdfs(EXTRACTOR_PDF_ROOT_DIR, EXTRACTOR_OUTPUT_FILE)

    # Step 4: Recreate dataset using AI 
    print("\n--- Creating dataset using AI ---")
    generate_dataset(max_lines_per_run=50,wait_time_between_calls=2)
    
    

if __name__ == "__main__":
    main()