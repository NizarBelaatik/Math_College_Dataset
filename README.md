# Dataset Math College

## Overview

The **Dataset Math College** project automates the creation of a structured dataset of mathematics exercises and their corrections for college-level students (1ère, 2ème, and 3ème année collège). The pipeline scrapes, downloads, extracts, and enhances math exercise data from PDF files sourced from Alloschool, producing a JSONL dataset suitable for educational applications or machine learning tasks.

## Project Workflow

The pipeline consists of four main steps, each handled by a dedicated script:

1. **Scraping PDF Links** (`pdf_scraper.py`):
   
   - Scrapes exercise and correction PDF links from Alloschool pages for grade levels 1AC, 2AC, and 3AC.
   - Uses Selenium and BeautifulSoup to navigate dynamic web pages and extract links.
   - Saves the scraped links in JSON files (`<grade>_questions_answers.json`) in the `BASE_DATA_DIR`.

2. **Downloading PDFs** (`pdf_downloader.py`):
   
   - Downloads exercise and correction PDFs using the scraped links.
   - Organizes PDFs into grade-specific directories (`exercice` and `correction`) under `BASE_PDF_DOWNLOAD_DIR`.
   - Cleans filenames to remove unnecessary suffixes (e.g., language codes, "non-corriges") for consistency.

3. **Extracting Data from PDFs** (`pdf_text_extractor.py`):
   
   - Extracts text from PDFs using `pdfplumber`.
   - Identifies exercises and corrections using regex patterns.
   - Infers metadata (subject, chapter, difficulty) from filenames and content.
   - Produces an initial JSONL dataset (`math_dataset.jsonl`) with fields like `id`, `niveau`, `chapitre`, `matiere`, `question`, `correction`, `type_exercice`, `difficulte`, and `source`.

4. **Enhancing Corrections with AI** (`get_correction_using_ai.py`):
   
   - Addresses missing or incomplete corrections in the initial dataset.
   - Uses the DeepSeek Chat API (`deepseek/deepseek-chat:free` via OpenRouter) to generate detailed corrections.
   - Cleans API responses to remove Markdown formatting and splits them into:
     - `raw_correction`: The full, unaltered API response.
     - `explanation`: Cleaned step-by-step explanation.
     - `answer`: Extracted final answers.
   - Saves the enhanced dataset to `math_dataset_corr_ai.jsonl`.

## Final Dataset Structure

The final dataset (`math_dataset_corr_ai.jsonl`) includes the following fields for each entry:

- `id`: Unique identifier for the exercise (e.g., `1AC_CALCU_001_Les_opérations_sur_les_nombres_décimaux_exercice_1`).
- `niveau`: Education level (e.g., `1ère année collège`).
- `chapitre`: Chapter or topic (e.g., `Calcul littéral`).
- `matiere`: Subject (e.g., `Algèbre`).
- `question`: The exercise text.
- `reponse_attendue`: Placeholder for expected response (currently empty).
- `correction`: Original correction from the PDF (if available).
- `type_exercice`: Type of exercise (e.g., `Résolution`).
- `difficulte`: Difficulty level (e.g., `Moyen`).
- `source`: Source PDF filename.
- `raw_correction`: Full, unaltered response from the DeepSeek API.
- `explanation`: Cleaned step-by-step explanation from the API response.
- `answer`: Extracted final answers from the API response.

### Example Dataset Entry

```json
{
    "id": "1AC_CALCU_001_Les_opérations_sur_les_nombres_décimaux_exercice_1",
    "niveau": "1ère année collège",
    "chapitre": "Calcul littéral",
    "matiere": "Algèbre",
    "question": "Calculer les expressions suivantes en détaillant les calculs. A = 12-(3+5) D = 5+11*4+3/3-7 G = 6/6+7*5-(5+9) B = 7*8+13 E = 5*13-8+10+12/12 H = 5+1,4+6*7-8,6 C = 12*13+8 F = 11/11+10-6+4*7 I = 6,8/6,8+7,7*(5,1+8,7)",
    "reponse_attendue": "",
    "correction": "",
    "type_exercice": "Résolution",
    "difficulte": "Moyen",
    "source": "Les_opérations_sur_les_nombres_décimaux_exercice_1.pdf",
    "raw_correction": "Voici les corrections détaillées pour chaque expression :\n\n---\n\n### **A = 12 - (3 + 5)**\n1. Calculer la parenthèse : \\(3 + 5 = 8\\).  \n2. Soustraire de 12 : \\(12 - 8 = 4\\).  \n   **Réponse : \\(A = 4\\)**\n\n---\n\n### **B = 7 × 8 + 13**\n1. Multiplier : \\(7 × 8 = 56\\).  \n2. Ajouter 13 : \\(56 + 13 = 69\\).  \n   **Réponse : \\(B = 69\\)**\n\n---\n\n### **C = 12 × 13 + 8**\n1. Multiplier : \\(12 × 13 = 156\\).  \n2. Ajouter 8 : \\(156 + 8 = 164\\).  \n   **Réponse : \\(C = 164\\)**\n\n---\n\n### **D = 5 + 11 × 4 + 3 / 3 - 7**\n1. Multiplier : \\(11 × 4 = 44\\).  \n2. Diviser : \\(3 / 3 = 1\\).  \n3. Additionner et soustraire dans l'ordre : \\(5 + 44 + 1 - 7 = 43\\).  \n   **Réponse : \\(D = 43\\)**\n\n---\n\n### **E = 5 × 13 - 8 + 10 + 12 / 12**\n1. Multiplier : \\(5 × 13 = 65\\).  \n2. Diviser : \\(12 / 12 = 1\\).  \n3. Additionner et soustraire dans l'ordre : \\(65 - 8 + 10 + 1 = 68\\).  \n   **Réponse : \\(E = 68\\)**\n\n---\n\n### **F = 11 / 11 + 10 - 6 + 4 × 7**\n1. Diviser : \\(11 / 11 = 1\\).  \n2. Multiplier : \\(4 × 7 = 28\\).  \n3. Additionner et soustraire dans l'ordre : \\(1 + 10 - 6 + 28 = 33\\).  \n   **Réponse : \\(F = 33\\)**\n\n---\n\n### **G = 6 / 6 + 7 × 5 - (5 + 9)**\n1. Diviser : \\(6 / 6 = 1\\).  \n2. Multiplier : \\(7 × 5 = 35\\).  \n3. Calculer la parenthèse : \\(5 + 9 = 14\\).  \n4. Additionner et soustraire dans l'ordre : \\(1 + 35 - 14 = 22\\).  \n   **Réponse : \\(G = 22\\)**\n\n---\n\n### **H = 5 + 1,4 + 6 × 7 - 8,6**\n1. Multiplier : \\(6 × 7 = 42\\).  \n2. Additionner et soustraire dans l'ordre : \\(5 + 1,4 + 42 - 8,6 = 39,8\\).  \n   **Réponse : \\(H = 39,8\\)**\n\n---\n\n### **I = 6,8 / 6,8 + 7,7 × (5,1 + 8,7)**\n1. Diviser : \\(6,8 / 6,8 = 1\\).  \n2. Calculer la parenthèse : \\(5,1 + 8,7 = 13,8\\).  \n3. Multiplier : \\(7,7 × 13,8 = 106,26\\).  \n4. Additionner : \\(1 + 106,26 = 107,26\\).  \n   **Réponse : \\(I = 107,26\\)**\n\n---\n\nSi vous avez d'autres questions, n'hésitez pas ! 😊",
    "explanation": "Voici les corrections détaillées pour chaque expression :\n A = 12 - 3 + 5\n1. Calculer la parenthèse : 3 + 5 = 8.  \n2. Soustraire de 12 : 12 - 8 = 4.  \n   Réponse : A = 4\n B = 7 × 8 + 13\n1. Multiplier : 7 × 8 = 56.  \n2. Ajouter 13 : 56 + 13 = 69.  \n   Réponse : B = 69\n C = 12 × 13 + 8\n1. Multiplier : 12 × 13 = 156.  \n2. Ajouter 8 : 156 + 8 = 164.  \n   Réponse : C = 164\n D = 5 + 11 × 4 + 3 / 3 - 7\n1. Multiplier : 11 × 4 = 44.  \n2. Diviser : 3 / 3 = 1.  \n3. Additionner et soustraire dans l'ordre : 5 + 44 + 1 - 7 = 43.  \n   Réponse : D = 43\n E = 5 × 13 - 8 + 10 + 12 / 12\n1. Multiplier : 5 × 13 = 65.  \n2. Diviser : 12 / 12 = 1.  \n3. Additionner et soustraire dans l'ordre : 65 - 8 + 10 + 1 = 68.  \n   Réponse : E = 68\n F = 11 / 11 + 10 - 6 + 4 × 7\n1. Diviser : 11 / 11 = 1.  \n2. Multiplier : 4 × 7 = 28.  \n3. Additionner et soustraire dans l'ordre : 1 + 10 - 6 + 28 = 33.  \n   Réponse : F = 33\n G = 6 / 6 + 7 × 5 - 5 + 9\n1. Diviser : 6 / 6 = 1.  \n2. Multiplier : 7 × 5 = 35.  \n3. Calculer la parenthèse : 5 + 9 = 14.  \n4. Additionner et soustraire dans l'ordre : 1 + 35 - 14 = 22.  \n   Réponse : G = 22\n H = 5 + 1,4 + 6 × 7 - 8,6\n1. Multiplier : 6 × 7 = 42.  \n2. Additionner et soustraire dans l'ordre : 5 + 1,4 + 42 - 8,6 = 39,8.  \n   Réponse : H = 39,8\n I = 6,8 / 6,8 + 7,7 × 5,1 + 8,7\n1. Diviser : 6,8 / 6,8 = 1.  \n2. Calculer la parenthèse : 5,1 + 8,7 = 13,8.  \n3. Multiplier : 7,7 × 13,8 = 106,26.  \n4. Additionner : 1 + 106,26 = 107,26.  \n   Réponse : I = 107,26",
    "answer": ": A = 4\n : B = 69\n : C = 164\n : D = 43\n : E = 68\n : F = 33\n : G = 22\n : H = 39,8\n : I = 107,26"
}
```

## Directory Structure

```
├── config.py                     # Configuration file for directory paths
├── pdf_scraper.py                # Script to scrape PDF links
├── pdf_downloader.py             # Script to download PDFs
├── pdf_text_extractor.py         # Script to extract data from PDFs
├── get_correction_using_ai.py    # Script to generate corrections using AI
├── main.py                       # Main script to orchestrate the pipeline
├── data/                         # Directory for JSON data (BASE_DATA_DIR)
├── pdfs/                         # Directory for downloaded PDFs (BASE_PDF_DOWNLOAD_DIR)
└── output/                       # Directory for output datasets (OUTPUT_DIR)
    ├── math_dataset.jsonl        # Initial extracted dataset
    └── math_dataset_corr_ai.jsonl # Final dataset with AI-enhanced corrections
```

## Prerequisites

- **Python 3.8+**
- **Dependencies**:
  - Install required packages: `pip install -r requirements.txt`
  - Required libraries: `pdfplumber`, `requests`, `selenium`, `beautifulsoup4`, `python-dotenv`
- **Selenium WebDriver**:
  - Requires ChromeDriver compatible with your Chrome browser version.
- **API Key**:
  - An API key for OpenRouter (stored in a `.env` file as `API_KEY`).

## Setup

1. Clone the repository:
   
   ```bash
   git clone <repository-url>
   cd dataset-math-college
   ```
2. Create a virtual environment and install dependencies:
   
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up the `.env` file:
   
   ```bash
   echo "API_KEY=your_openrouter_api_key" > .env
   ```
4. Ensure ChromeDriver is installed and accessible in your PATH.

## Usage

Run the main script to execute the entire pipeline:

```bash
python main.py
```

The pipeline will:

1. Scrape PDF links for all grade levels (1AC, 2AC, 3AC).
2. Download the corresponding exercise and correction PDFs.
3. Extract exercises and metadata into `math_dataset.jsonl`.
4. Generate AI-enhanced corrections and save to `math_dataset_corr_ai.jsonl`.

To process a specific grade level or step, modify `main.py` or run individual scripts:

```bash
python pdf_scraper.py
python pdf_downloader.py
python pdf_text_extractor.py
python get_correction_using_ai.py
```

## Notes

- The pipeline handles large datasets with a `max_lines_per_run` limit in `get_correction_using_ai.py` to manage API usage (default: 50 lines per run).
- A `wait_time_between_calls` (default: 2 seconds) is used to avoid overwhelming the API.
- The dataset is structured with unique IDs and comprehensive metadata for use in educational tools or machine learning.
- The AI correction step ensures all exercises have detailed explanations and answers, even if the original PDFs lacked corrections.
- The cleaning process in `get_correction_using_ai.py` removes Markdown artifacts (e.g., `**`, `#`, `\`) to produce clean `explanation` and `answer` fields.
