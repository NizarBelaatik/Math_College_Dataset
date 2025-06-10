import os
import re
import json
import pdfplumber
from typing import Dict, List, Tuple, Optional
from config import  OUTPUT_DIR ,PDF_ROOT_DIR


EXTRACTED_TEXTS_DIR = os.path.join(OUTPUT_DIR, "extracted_texts")
FULL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "math_dataset.jsonl")

# Create directories if they don't exist
os.makedirs(EXTRACTED_TEXTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- Text Extraction Functions ----------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    # Clean up the text
                    page_text = re.sub(r'\s+', ' ', page_text.strip())
                    # Replace special characters
                    replacements = {
                        '−': '-', '×': '*', '÷': '/', 
                        '²': '^2', '³': '^3', '√': 'sqrt',
                        '≈': '≈', '≤': '<=', '≥': '>='
                    }
                    for orig, repl in replacements.items():
                        page_text = page_text.replace(orig, repl)
                    text += page_text + "\n"
    except Exception as e:
        print(f"[ERROR] Could not extract text from {pdf_path}: {e}")
        return ""
    return text

# ---------- Level Detection ----------

def detect_niveau(folder_path: str) -> str:
    """Detect the education level from folder path."""
    folder = folder_path.lower()
    if '3ac' in folder or '3ème' in folder or '3eme' in folder:
        return "3ème année collège"
    elif '2ac' in folder or '2ème' in folder or '2eme' in folder:
        return "2ème année collège"
    elif '1ac' in folder or '1ère' in folder or '1ere' in folder:
        return "1ère année collège"
    return "Non spécifié"

# ---------- Content Extraction ----------

def extract_exercises(text: str) -> Dict[int, str]:
    """Extract exercises from text with multiple patterns."""
    exercises = {}
    
    patterns = [
        # Pattern 1: "Exercice N" followed by content
        r'(?:Exercice|EXERCICE)\s*(\d+)[\.\s]*(.*?)(?=(?:Exercice|EXERCICE)\s*\d+|$)',
        # Pattern 2: "N°N" format
        r'(?:N°|Numéro)\s*(\d+)[\.\s]*(.*?)(?=(?:N°|Numéro)\s*\d+|$)',
        # Pattern 3: Numbered items with parentheses
        r'(\d+)\)\s*(.*?)(?=\d+\)|$)'
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            try:
                ex_num = int(match.group(1))
                ex_content = match.group(2).strip()
                if ex_content and (ex_num not in exercises or len(ex_content) > len(exercises.get(ex_num, ""))):
                    exercises[ex_num] = ex_content
            except (ValueError, IndexError):
                continue
                
    return exercises

def extract_corrections(text: str) -> Dict[int, str]:
    """Extract corrections with multiple patterns."""
    corrections = {}
    
    patterns = [
        # Explicit correction markers
        r"(?:Corrigé|CORRIGE|Solution|SOLUTION)\s*(?:de l[''']|d[ue]\s*)?(?:exercice|exo|EXERCICE)\s*(\d+)[\.\s]*(.*?)(?=(?:Corrigé|CORRIGE|Solution|SOLUTION)\s*(?:de l[''']|d[ue]\s*)?(?:exercice|exo|EXERCICE)\s*\d+|$)",
        # Exercise followed by correction
        r"(?:Exercice|EXERCICE)\s*(\d+)[\.\s]*(?:Corrigé|CORRIGE|Solution|SOLUTION)[\.\s]*(.*?)(?=(?:Exercice|EXERCICE)\s*\d+|$)",
        # Numbered corrections
        r"(\d+)[\)\.]\s*(?:Corrigé|CORRIGE|Solution|SOLUTION)[\.\s]*(.*?)(?=\d+[\)\.]|$)",
        # Simple numbered items (fallback)
        r"(\d+)\)\s*(.*?)(?=\d+\)|$)"
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

# ---------- Metadata Extraction ----------

def infer_metadata(pdf_name: str, text: str) -> Tuple[str, str, str]:
    """
    Infer subject, chapter, and difficulty based on filename and content.
    Returns: (matiere, chapitre, difficulte)
    """
    pdf_name_lower = pdf_name.lower()
    text_lower = text.lower()
    
    # Subject and chapter mapping
    subject_chapter_map = {
        "thales": ("Géométrie", "Théorème de Thalès"),
        "pythagore": ("Géométrie", "Théorème de Pythagore"),
        "trigonometrie": ("Géométrie", "Trigonométrie"),
        "geometrie": ("Géométrie", "Géométrie plane"),
        "racine": ("Algèbre", "Racines carrées"),
        "equation": ("Algèbre", "Équations"),
        "inequation": ("Algèbre", "Inéquations"),
        "fonction": ("Algèbre", "Fonctions"),
        "calcul": ("Algèbre", "Calcul littéral"),
        "developpement": ("Algèbre", "Développement et factorisation"),
        "factorisation": ("Algèbre", "Développement et factorisation"),
        "identite": ("Algèbre", "Identités remarquables"),
        "fraction": ("Arithmétique", "Fractions"),
        "puissance": ("Arithmétique", "Puissances"),
        "arithmetique": ("Arithmétique", "Arithmétique"),
        "statistique": ("Statistiques", "Statistiques"),
        "probabilite": ("Probabilités", "Probabilités")
    }
    
    # Difficulty indicators
    difficulty_map = {
        "facile": ["facile", "simple", "basique"],
        "difficile": ["difficile", "complexe", "avancé", "brevet"],
        "moyen": ["moyen", "intermédiaire", "standard"]
    }
    
    # Default values
    matiere = "Mathématiques"
    chapitre = "Non spécifié"
    difficulte = "Moyen"
    
    # Detect subject and chapter
    for keyword, (subj, chap) in subject_chapter_map.items():
        if keyword in pdf_name_lower or keyword in text_lower:
            matiere = subj
            chapitre = chap
            break
    
    # Detect difficulty
    for level, keywords in difficulty_map.items():
        if any(kw in pdf_name_lower or kw in text_lower for kw in keywords):
            difficulte = level
            break
    
    return matiere, chapitre, difficulte

# ---------- File Matching ----------

def find_matching_files(root_dir: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Find matching exercise and correction files.
    Returns list of tuples: (exercise_path, correction_path, niveau)
    """
    file_pairs = []
    
    for niveau_dir in ["1AC", "2AC", "3AC"]:
        niveau_path = os.path.join(root_dir, niveau_dir)
        if not os.path.exists(niveau_path):
            continue
            
        niveau = detect_niveau(niveau_dir)
        
        # Walk through exercise and correction directories
        ex_dir = os.path.join(niveau_path, "exercice")
        corr_dir = os.path.join(niveau_path, "correction")
        
        if not os.path.exists(ex_dir):
            continue
            
        # Get all exercise files
        for ex_file in os.listdir(ex_dir):
            if not ex_file.lower().endswith('.pdf'):
                continue
                
            ex_path = os.path.join(ex_dir, ex_file)
            corr_path = None
            
            # Try to find matching correction
            if os.path.exists(corr_dir):
                # Simple matching by filename
                base_name = os.path.splitext(ex_file)[0]
                corr_candidates = [
                    f for f in os.listdir(corr_dir) 
                    if f.lower().endswith('.pdf') and 
                    (base_name in f or f.replace("correction", "").replace("corrige", "").strip() == base_name)
                ]
                
                if corr_candidates:
                    # Take the first matching candidate
                    corr_path = os.path.join(corr_dir, corr_candidates[0])
            
            file_pairs.append((ex_path, corr_path, niveau))
    
    return file_pairs

# ---------- Main Processing ----------

def create_dataset_from_pdfs(pdf_root_dir: str, output_file: str):
    """Main function to process PDFs and create dataset."""
    dataset = []
    
    # Find all matching exercise-correction pairs
    file_pairs = find_matching_files(pdf_root_dir)
    print(f"Found {len(file_pairs)} exercise files with potential corrections")
    
    for ex_path, corr_path, niveau in file_pairs:
        ex_name = os.path.basename(ex_path)
        print(f"\nProcessing: {ex_name}")
        
        # Extract exercise text
        ex_text = extract_text_from_pdf(ex_path)
        if not ex_text:
            print(f"  [!] Could not extract text from {ex_name}")
            continue
            
        # Extract exercises
        exercises = extract_exercises(ex_text)
        if not exercises:
            print(f"  [!] No exercises found in {ex_name}")
            continue
            
        # Extract corrections if available
        corrections = {}
        if corr_path and os.path.exists(corr_path):
            corr_text = extract_text_from_pdf(corr_path)
            if corr_text:
                corrections = extract_corrections(corr_text)
                print(f"  [+] Found {len(corrections)} corrections in {os.path.basename(corr_path)}")
            else:
                print(f"  [!] Could not extract text from correction {os.path.basename(corr_path)}")
        else:
            print("  [!] No matching correction found")
            
        # Infer metadata
        matiere, chapitre, difficulte = infer_metadata(ex_name, ex_text)
        
        # Create dataset entries
        for ex_num, question in exercises.items():
            correction = corrections.get(ex_num, "")
            
            # Create unique ID
            chap_id = re.sub(r'[^a-zA-Z0-9]+', '', chapitre)[:5].upper()
            unique_id = f"{niveau[:1]}AC_{chap_id}_{ex_num:03d}_{os.path.splitext(ex_name)[0]}"
            
            dataset.append({
                "id": unique_id,
                "niveau": niveau,
                "chapitre": chapitre,
                "matiere": matiere,
                "question": question,
                "reponse_attendue": "",  # Can be filled manually later
                "correction": correction,
                "type_exercice": "Résolution",
                "difficulte": difficulte,
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