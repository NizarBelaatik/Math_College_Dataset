import os
import re
import json
import pdfplumber # This is the main library for PDF text extraction

from config import PDF_ROOT_DIR , OUTPUT_DIR



EXTRACTED_TEXTS_DIR = os.path.join(OUTPUT_DIR, "extracted_texts")
FULL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "math_dataset.jsonl")

# Grade levels to categorize PDFs (can be expanded)
NIVEAUX = ["1ère année collège", "2ème année collège", "3ème année collège"]

os.makedirs(EXTRACTED_TEXTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------- Utilities ----------

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from a PDF file.

    Args:
        pdf_path (str): The path to the PDF file.

    Returns:
        str: The extracted text, with common formatting issues cleaned.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    # Replace multiple spaces/newlines with a single space, strip whitespace
                    page_text = re.sub(r'\s+', ' ', page_text.strip())
                    # Common character replacements
                    page_text = page_text.replace('−', '-').replace('²', '^2').replace('√', 'sqrt')
                    text += page_text + "\n"
    except Exception as e:
        print(f"[ERROR] Could not extract text from {pdf_path}: {e}")
        return ""
    return text


def detect_niveau(folder_path: str) -> str:
    """
    Infers the grade level based on the folder path.
    Assumes folder names like '1AC', '2AC', '3AC' will be present in the path.

    Args:
        folder_path (str): The path of the folder containing the PDF.

    Returns:
        str: The detected grade level, or "Non spécifié" if not found.
    """
    folder = folder_path.lower()
    if '3ac' in folder or '3ème' in folder:
        return "3ème année collège"
    elif '2ac' in folder or '2ème' in folder:
        return "2ème année collège"
    elif '1ac' in folder or '1ère' in folder:
        return "1ère année collège"
    return "Non spécifié" # Default or if not detected


# Update the extract_exercises function:
def extract_exercises(text: str) -> dict:
    """
    Extracts exercises from a given text using multiple regex patterns.
    """
    exercises = {}
    
    # Pattern 1: "Exercice N" followed by content
    pattern1 = r'(?:Exercice|EXERCICE)\s*(\d+)[\.\s]*(.*?)(?=(?:Exercice|EXERCICE)\s*\d+|$)'
    # Pattern 2: "N°N" format
    pattern2 = r'(?:N°|Numéro)\s*(\d+)[\.\s]*(.*?)(?=(?:N°|Numéro)\s*\d+|$)'
    
    for pattern in [pattern1, pattern2]:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            ex_num = int(match.group(1))
            ex_content = match.group(2).strip()
            if ex_content and ex_content not in exercises.values():
                exercises[ex_num] = ex_content
                
    return exercises

# Update the extract_corrections function:
def extract_corrections(text: str) -> dict:
    """
    Extracts corrections with multiple patterns for better matching.
    """
    corrections = {}
    
    patterns = [
        r"(?:Corrigé|CORRIGE|Solution)\s*(?:de l[''’]|d[ue]\s*)?(?:exercice|exo|EXERCICE)\s*(\d+)[\.\s]*(.*?)(?=(?:Corrigé|CORRIGE|Solution)\s*(?:de l[''’]|d[ue]\s*)?(?:exercice|exo|EXERCICE)\s*\d+|$)",
        r"(?:Exercice|EXERCICE)\s*(\d+)[\.\s]*(?:Corrigé|CORRIGE|Solution)[\.\s]*(.*?)(?=(?:Exercice|EXERCICE)\s*\d+|$)",
        r"(\d+)[\)\.]\s*(?:Corrigé|CORRIGE|Solution)[\.\s]*(.*?)(?=\d+[\)\.]|$)"
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            try:
                ex_num = int(match.group(1))
                correction = match.group(2).strip()
                if correction and (ex_num not in corrections or len(correction) > len(corrections.get(ex_num, ""))):
                    corrections[ex_num] = correction
            except (ValueError, IndexError):
                continue
                
    return corrections



def extract_corrections2(text: str) -> dict:
    corrections = {}
    
    # Pattern 1: Explicit "Corrigé (de l'|du)? Exercice N"
    pattern1 = r"(?:Corrigé|CORRIGE)\s*(?:de l['’]|d[ue]\s*)?exercice\s*(\d+)\s*(.*?)(?=(?:Corrigé|CORRIGE)\s*(?:de l['’]|d[ue]\s*)?exercice\s*\d+|$)"
    matches = list(re.finditer(pattern1, text, re.DOTALL | re.IGNORECASE))
    
    if matches:
        for match in matches:
            try:
                ex_num = int(match.group(1))
                correction = match.group(2).strip()
                if correction:
                    corrections[ex_num] = correction
            except ValueError:
                # Skip if number parsing fails
                continue
    else:
        # Fallback Pattern 2: Numbered corrections (e.g., "1) ... 2) ...")
        # This is less reliable but can catch cases without explicit "Corrigé Exercice" headers.
        fallback_pattern = r"(\d+)\)\s*(.*?)(?=\d+\)|$)"
        for match in re.finditer(fallback_pattern, text, re.DOTALL):
            try:
                ex_num = int(match.group(1))
                correction = match.group(2).strip()
                if correction and len(correction) > 10: # Simple check to avoid very short accidental matches
                    corrections[ex_num] = correction
            except ValueError:
                continue

    return corrections


def infer_matiere_chapitre(pdf_name: str, text: str) -> tuple[str, str]:
    """
    Infers the subject and chapter based on PDF filename and content.

    Args:
        pdf_name (str): The base filename of the PDF.
        text (str): The extracted text from the PDF.

    Returns:
        tuple[str, str]: A tuple containing the inferred subject and chapter.
    """
    pdf_name_lower = pdf_name.lower()
    text_lower = text.lower()

    # Define keywords for common math topics
    keywords_chapitre = {
        "thales": "Théorème de Thalès",
        "ordre": "Ordre et Opérations",
        "operations": "Ordre et Opérations",
        "equation": "Équations",
        "fonctions": "Fonctions",
        "fraction": "Fractions",
        "puissance": "Puissances",
        "racine": "Racines carrées",
        "proportionnalite": "Proportionnalité",
        "statistique": "Statistiques",
        "probabilite": "Probabilités",
        "geometrie": "Géométrie",
        "pythagore": "Théorème de Pythagore",
        "trigonometrie": "Trigonométrie",
        "arithmetique": "Arithmétique",
        "calcul": "Calcul littéral",
        "developpement": "Développement et Factorisation"
    }

    # Check for specific chapters in name or text
    for keyword, chapter_name in keywords_chapitre.items():
        if keyword in pdf_name_lower or keyword in text_lower:
            # Simple matiere inference based on chapter
            if chapter_name in ["Théorème de Thalès", "Théorème de Pythagore", "Trigonométrie", "Géométrie"]:
                return "Géométrie", chapter_name
            elif chapter_name in ["Ordre et Opérations", "Équations", "Fonctions", "Calcul littéral", "Développement et Factorisation"]:
                return "Algèbre", chapter_name
            elif chapter_name in ["Fractions", "Puissances", "Racines carrées", "Arithmétique"]:
                return "Arithmétique", chapter_name
            elif chapter_name in ["Proportionnalité", "Statistiques", "Probabilités"]:
                return "Statistiques et Probabilités", chapter_name
            return "Mathématiques", chapter_name # Default if not explicitly categorized

    # Broader subject inference if no specific chapter detected
    if "géométrie" in pdf_name_lower or "géométrie" in text_lower:
        return "Géométrie", "Non spécifié"
    if "algèbre" in pdf_name_lower or "algèbre" in text_lower or any(k in text_lower for k in ["équation", "fonction", "calcul"]):
        return "Algèbre", "Non spécifié"
    if "arithmétique" in pdf_name_lower or "arithmétique" in text_lower or any(k in text_lower for k in ["nombre", "fraction", "puissance"]):
        return "Arithmétique", "Non spécifié"
    
    return "Mathématiques", "Non spécifié" # Default if nothing matches


# ---------- Main Processing ----------

# In pdf_text_extractor.py, update the create_dataset_from_pdfs function:
def create_dataset_from_pdfs(pdf_root_dir: str, output_file: str):
    dataset = []
    
    # Walk through all directories to find exercise and correction PDFs
    exercise_files = []
    correction_files = []
    
    for root, _, files in os.walk(pdf_root_dir):
        for f in files:
            if f.lower().endswith('.pdf'):
                full_path = os.path.join(root, f)
                if 'exercice' in root.lower():
                    exercise_files.append((f, full_path))
                elif 'correction' in root.lower():
                    correction_files.append((f, full_path))
    
    # Create a mapping for correction files
    correction_map = {}
    for corr_name, corr_path in correction_files:
        # Normalize names for matching
        base_name = os.path.splitext(corr_name)[0]
        norm_name = re.sub(r'[-_\s]*(corrige|correction|cor|solution|c)[-_\s]*', '', base_name, flags=re.IGNORECASE)
        correction_map[norm_name.lower()] = corr_path
    
    print(f"Found {len(exercise_files)} exercise files and {len(correction_files)} correction files")
    
    for ex_name, ex_path in exercise_files:
        print(f"\nProcessing: {ex_path}")
        
        # Get base name without extension and correction indicators
        ex_base = os.path.splitext(ex_name)[0]
        norm_ex_name = re.sub(r'[-_\s]*(ex|exercice|exercices|exo)[-_\s]*', '', ex_base, flags=re.IGNORECASE)
        
        # Find matching correction
        corr_path = correction_map.get(norm_ex_name.lower())
        
        if not corr_path:
            # Try alternative matching patterns
            for corr_norm_name, path in correction_map.items():
                if norm_ex_name.lower() in corr_norm_name or corr_norm_name in norm_ex_name.lower():
                    corr_path = path
                    break
        
        # Process the exercise PDF
        ex_text = extract_text_from_pdf(ex_path)
        if not ex_text:
            print(f"  [!] Could not extract text from {ex_name}")
            continue
            
        exercises = extract_exercises(ex_text)
        if not exercises:
            print(f"  [!] No exercises found in {ex_name}")
            continue
            
        # Process correction PDF if found
        corrections = {}
        if corr_path:
            corr_text = extract_text_from_pdf(corr_path)
            if corr_text:
                corrections = extract_corrections(corr_text)
            else:
                print(f"  [!] Could not extract text from correction {os.path.basename(corr_path)}")
        else:
            print(f"  [!] No matching correction found for {ex_name}")
            
        # Create dataset entries
        matiere, chapitre = infer_matiere_chapitre(ex_name, ex_text)
        niveau = detect_niveau(os.path.dirname(ex_path))
        
        for ex_num, question in exercises.items():
            correction = corrections.get(ex_num, "")
            
            # Create unique ID
            chap_id = re.sub(r'[^a-zA-Z0-9]+', '', chapitre)[:5].upper()
            unique_id = f"{niveau[:1]}AC_{chap_id}_{ex_num:03d}_{ex_base}"
            
            dataset.append({
                "id": unique_id,
                "niveau": niveau,
                "chapitre": chapitre,
                "matiere": matiere,
                "question": question,
                "reponse_attendue": "",
                "correction": correction,
                "type_exercice": "Résolution",
                "difficulte": "Moyen",
                "source": ex_name
            })
    
    # Save the dataset
    if dataset:
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in dataset:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"\nSuccessfully saved {len(dataset)} exercises to {output_file}")
    else:
        print("\nNo exercises were extracted from the PDFs")

if __name__ == "__main__":
    create_dataset_from_pdfs(PDF_ROOT_DIR, FULL_OUTPUT_FILE)