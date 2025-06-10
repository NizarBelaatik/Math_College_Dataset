import os
import re
import json
import pdfplumber
from typing import Dict, List, Tuple, Optional
from config import OUTPUT_DIR, PDF_ROOT_DIR, BASE_DATA_DIR
#import openai  # For AI explanations (you'll need to install and configure this)

#openai.api_key = "sk-1234567890abcdef1234567890abcdef12345678"
from openai import OpenAI
client = OpenAI(api_key="")


EXTRACTED_TEXTS_DIR = os.path.join(OUTPUT_DIR, "extracted_texts")
FULL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "math_dataset.jsonl")
EXPLANATION_CACHE_FILE = os.path.join(OUTPUT_DIR, "explanations_cache.json")

# Create directories if they don't exist
os.makedirs(EXTRACTED_TEXTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- Configuration ----------
# Configure these based on your needs
MAX_EXERCISE_LENGTH = 2000  # Characters
MAX_CORRECTION_LENGTH = 3000  # Characters
MIN_EXERCISE_LENGTH = 50  # Characters
MIN_CORRECTION_LENGTH = 30  # Characters

# ---------- Text Extraction Functions ----------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Enhanced PDF text extraction with better formatting preservation."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Use both text extraction and table extraction
                page_text = page.extract_text() or ""
                tables = page.extract_tables()
                
                # Add table content if found
                for table in tables:
                    for row in table:
                        page_text += " | ".join(str(cell) for cell in row if cell) + "\n"
                
                if page_text:
                    # Clean up the text while preserving some structure
                    page_text = re.sub(r'\s+', ' ', page_text.strip())
                    # Replace special mathematical characters
                    replacements = {
                        '−': '-', '×': '*', '÷': '/', 
                        '²': '^2', '³': '^3', '√': 'sqrt',
                        '≈': '≈', '≤': '<=', '≥': '>=', '≠': '!=',
                        'π': 'pi', '°': ' deg', '∠': 'angle ',
                        '→': '->', '⇒': '=>', '≡': '≡'
                    }
                    for orig, repl in replacements.items():
                        page_text = page_text.replace(orig, repl)
                    
                    # Preserve question numbers and important markers
                    page_text = re.sub(r'(\d+)\s*([°\)\.])', r'\1\2 ', page_text)  # Fix spacing after numbers
                    text += page_text + "\n\n"
    except Exception as e:
        print(f"[ERROR] Could not extract text from {pdf_path}: {e}")
        return ""
    return text

# ---------- Content Extraction Improvements ----------

def clean_content(content: str) -> str:
    """Clean and normalize exercise or correction content."""
    if not content:
        return ""
    
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content.strip())
    
    # Normalize mathematical expressions
    content = re.sub(r'(\d)\s*([+\-*/^=])\s*(\d)', r'\1 \2 \3', content)  # Add spaces around operators
    
    # Remove common headers/footers
    content = re.sub(r'(page|pagina|página)\s*\d+\s*(of|de)\s*\d+', '', content, flags=re.IGNORECASE)
    content = re.sub(r'©.*$', '', content)
    
    return content

def extract_exercises(text: str) -> Dict[int, str]:
    """Enhanced exercise extraction with better pattern matching."""
    exercises = {}
    
    patterns = [
        # Improved pattern 1: "Exercice N" with optional title
        r'(?:Exercice|EXERCICE|Problème|PROBLEME)\s*(\d+)[\s\.:-]*(.*?)(?=(?:Exercice|EXERCICE|Problème|PROBLEME)\s*\d+|\Z)',
        # Pattern 2: "N°N" format with optional title
        r'(?:N°|Numéro|No)\s*(\d+)[\s\.:-]*(.*?)(?=(?:N°|Numéro|No)\s*\d+|\Z)',
        # Pattern 3: Numbered items with various delimiters
        r'(\d+)[\)\.]\s*(.*?)(?=\d+[\)\.]|\Z)',
        # Pattern 4: Q1, Q2 format
        r'Q\s*(\d+)[\s\.:-]*(.*?)(?=Q\s*\d+|\Z)'
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            try:
                ex_num = int(match.group(1))
                ex_content = clean_content(match.group(2))
                
                # Validate exercise content
                if (ex_content and len(ex_content) >= MIN_EXERCISE_LENGTH and 
                    len(ex_content) <= MAX_EXERCISE_LENGTH and
                    ex_num not in exercises):
                    exercises[ex_num] = ex_content
            except (ValueError, IndexError):
                continue
                
    return exercises

def extract_corrections(text: str) -> Dict[int, str]:
    """Enhanced correction extraction with better pattern matching."""
    corrections = {}
    
    patterns = [
        # Explicit correction markers with flexible spacing
        r"(?:Corrigé|CORRIGÉ|Correction|CORRECTION|Solution|SOLUTION|Réponse|REPONSE)\s*(?:de l['\"]?|du|de)?\s*(?:exercice|exo|EXERCICE|EXO|problème|PROBLEME)?\s*(\d+)[\s\.:-]*(.*?)(?=(?:Corrigé|CORRIGÉ|Correction|CORRECTION|Solution|SOLUTION|Réponse|REPONSE)\s*(?:de l['\"]?|du|de)?\s*(?:exercice|exo|EXERCICE|EXO|problème|PROBLEME)?\s*\d+|\Z)",
        # Exercise followed by correction
        r"(?:Exercice|EXERCICE|Problème|PROBLEME)\s*(\d+)[\s\.:-]*(?:.*?)(?:Corrigé|CORRIGÉ|Correction|CORRECTION|Solution|SOLUTION|Réponse|REPONSE)[\s\.:-]*(.*?)(?=(?:Exercice|EXERCICE|Problème|PROBLEME)\s*\d+|\Z)",
        # Numbered corrections with various formats
        r"(\d+)[\)\.]\s*(?:Corrigé|CORRIGÉ|Correction|CORRECTION|Solution|SOLUTION|Réponse|REPONSE)[\s\.:-]*(.*?)(?=\d+[\)\.]|\Z)",
        # Solution: pattern
        r"Solution\s*:\s*(\d+)[\s\.:-]*(.*?)(?=Solution\s*:\s*\d+|\Z)"
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            try:
                ex_num = int(match.group(1))
                correction = clean_content(match.group(2))
                
                # Validate correction content
                if (correction and len(correction) >= MIN_CORRECTION_LENGTH and len(correction) <= MAX_CORRECTION_LENGTH and  (ex_num not in corrections or len(correction) > len(corrections.get(ex_num, "")))):
                    corrections[ex_num] = correction
            except(ValueError, IndexError):
                continue
                
    return corrections

# ---------- AI Explanation Generation ----------

class ExplanationGenerator:
    def __init__(self):
        self.cache = {}
        self.load_cache()
        
    def load_cache(self):
        """Load cached explanations to avoid redundant API calls."""
        if os.path.exists(EXPLANATION_CACHE_FILE):
            try:
                with open(EXPLANATION_CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load explanation cache: {e}")
                self.cache = {}
    
    def save_cache(self):
        """Save current cache to file."""
        try:
            with open(EXPLANATION_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save explanation cache: {e}")
    
    def generate_explanation(self, question: str, correction: str, language: str = "fr") -> str:
        """
        Generate step-by-step explanation using AI.
        Returns cached explanation if available, otherwise calls API.
        """
        cache_key = f"{question[:200]}_{correction[:200]}".replace(" ", "_")
        
        # Return cached explanation if available
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Prepare prompt based on available information
        if correction:
            prompt = (
                f"Voici un exercice de mathématiques avec sa correction. "
                f"Fournissez une explication étape par étape en {language} qui montre comment arriver à la solution.\n\n"
                f"Exercice: {question}\n\n"
                f"Correction: {correction}\n\n"
                f"Explication étape par étape:\n1. "
            )
        else:
            prompt = (
                f"Voici un exercice de mathématiques. Fournissez une explication étape par étape "
                f"en {language} qui montre comment résoudre ce problème.\n\n"
                f"Exercice: {question}\n\n"
                f"Explication étape par étape:\n1. "
            )
        
        try:
            # Call OpenAI API (or other AI service)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Vous êtes un tuteur en mathématiques qui fournit des explications claires et détaillées."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            explanation = response.choices[0].message.content.strip()
            
            # Cache the explanation
            self.cache[cache_key] = explanation
            self.save_cache()
            
            return explanation
        except Exception as e:
            print(f"Error generating AI explanation: {e}")
            return "Explication non disponible pour le moment."
    
    def generate_multilingual_explanation(self, question: str, correction: str) -> Dict[str, str]:
        """Generate explanations in multiple languages."""
        languages = {
            "fr": "Français"
        }
        
        explanations = {}
        for code, name in languages.items():
            explanations[code] = self.generate_explanation(question, correction, code)
        
        return explanations

# ---------- Enhanced Metadata Extraction ----------

def infer_metadata(pdf_name: str, text: str) -> Tuple[str, str, str, List[str]]:
    """
    Enhanced metadata inference with more subjects and tags.
    Returns: (matiere, chapitre, difficulte, tags)
    """
    pdf_name_lower = pdf_name.lower()
    text_lower = text.lower()
    
    # Expanded subject and chapter mapping
    subject_chapter_map = {
        "thales": ("Géométrie", "Théorème de Thalès", ["géométrie", "théorème", "triangles"]),
        "pythagore": ("Géométrie", "Théorème de Pythagore", ["géométrie", "théorème", "triangle rectangle"]),
        "trigonometrie": ("Géométrie", "Trigonométrie", ["géométrie", "trigonométrie", "cosinus", "sinus", "tangente"]),
        "geometrie": ("Géométrie", "Géométrie plane", ["géométrie", "angles", "figures"]),
        "espace": ("Géométrie", "Géométrie dans l'espace", ["géométrie", "espace", "solides"]),
        "racine": ("Algèbre", "Racines carrées", ["algèbre", "racine", "radical"]),
        "equation": ("Algèbre", "Équations", ["algèbre", "équation", "résolution"]),
        "inequation": ("Algèbre", "Inéquations", ["algèbre", "inéquation", "inégalité"]),
        "fonction": ("Algèbre", "Fonctions", ["algèbre", "fonction", "graphique"]),
        "calcul": ("Algèbre", "Calcul littéral", ["algèbre", "calcul", "expression"]),
        "developpement": ("Algèbre", "Développement", ["algèbre", "développement", "expression"]),
        "factorisation": ("Algèbre", "Factorisation", ["algèbre", "factorisation", "expression"]),
        "identite": ("Algèbre", "Identités remarquables", ["algèbre", "identité", "formule"]),
        "fraction": ("Arithmétique", "Fractions", ["arithmétique", "fraction", "nombre"]),
        "puissance": ("Arithmétique", "Puissances", ["arithmétique", "puissance", "exposant"]),
        "arithmetique": ("Arithmétique", "Arithmétique", ["arithmétique", "nombre", "calcul"]),
        "statistique": ("Statistiques", "Statistiques", ["statistique", "donnée", "moyenne"]),
        "probabilite": ("Probabilités", "Probabilités", ["probabilité", "chance", "événement"]),
        "pourcentage": ("Arithmétique", "Pourcentages", ["arithmétique", "pourcentage", "proportion"]),
        "relative": ("Arithmétique", "Nombres relatifs", ["arithmétique", "nombre relatif", "signe"]),
        "symetrie": ("Géométrie", "Symétrie", ["géométrie", "symétrie", "transformation"])
    }
    
    # Enhanced difficulty detection
    difficulty_map = {
        "facile": ["facile", "simple", "basique", "débutant"],
        "difficile": ["difficile", "complexe", "avancé", "brevet", "olympiade", "championnat"],
        "moyen": ["moyen", "intermédiaire", "standard", "classique"]
    }
    
    # Default values
    matiere = "Mathématiques"
    chapitre = "Non spécifié"
    difficulte = "Moyen"
    tags = ["mathématiques"]
    
    # Detect subject and chapter
    for keyword, (subj, chap, kw_tags) in subject_chapter_map.items():
        if keyword in pdf_name_lower or keyword in text_lower:
            matiere = subj
            chapitre = chap
            tags.extend(kw_tags)
            break
    
    # Detect difficulty
    for level, keywords in difficulty_map.items():
        if any(kw in pdf_name_lower or kw in text_lower for kw in keywords):
            difficulte = level
            break
    
    # Add additional tags from text
    additional_tags = {
        "calculatrice": "calculatrice",
        "graphique": "graphique",
        "démonstration": "démonstration",
        "algèbre": "algèbre",
        "géométrie": "géométrie"
    }
    
    for kw, tag in additional_tags.items():
        if kw in text_lower and tag not in tags:
            tags.append(tag)
    
    return matiere, chapitre, difficulte, list(set(tags))  # Remove duplicates


# ------------------- files matching
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

def find_matching_files(root_dir: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Find matching exercise and correction files based on directory structure.
    Returns list of tuples: (exercise_path, correction_path, niveau)
    """
    file_pairs = []
    
    for niveau_dir in ["1AC", "2AC", "3AC"]:
        niveau_path = os.path.join(root_dir, niveau_dir)
        if not os.path.exists(niveau_path):
            print(f"Skipping {niveau_dir}: Directory not found at {niveau_path}")
            continue
            
        niveau = detect_niveau(niveau_dir)
        
        ex_dir = os.path.join(niveau_path, "exercice")
        corr_dir = os.path.join(niveau_path, "correction")
        
        if not os.path.exists(ex_dir):
            print(f"Exercise directory not found for {niveau_dir} at {ex_dir}")
            continue
        
        # Process exercise files
        for ex_file in os.listdir(ex_dir):
            if ex_file.endswith('.pdf'):
                ex_path = os.path.join(ex_dir, ex_file)
                corr_path = None
                
                # Look for matching correction
                if os.path.exists(corr_dir):
                    # Try exact match first
                    corr_file = ex_file
                    corr_path = os.path.join(corr_dir, corr_file)
                    
                    if not os.path.exists(corr_path):
                        # Try variations
                        base_name = os.path.splitext(ex_file)[0]
                        corr_candidates = [
                            f for f in os.listdir(corr_dir)
                            if f.lower().startswith(base_name.lower()) and f.endswith('.pdf')
                        ]
                        if corr_candidates:
                            corr_path = os.path.join(corr_dir, corr_candidates[0])
                
                file_pairs.append((ex_path, corr_path, niveau))
    
    return file_pairs

# ... (keep the rest of your existing functions)

# ---------- Main Processing with AI Enhancements ----------

def create_dataset_from_pdfs(pdf_root_dir: str, output_file: str):
    """Enhanced main function with AI explanations."""
    dataset = []
    explanation_gen = ExplanationGenerator()
    
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
        matiere, chapitre, difficulte, tags = infer_metadata(ex_name, ex_text)
        
        # Create dataset entries
        for ex_num, question in exercises.items():
            correction = corrections.get(ex_num, "")
            
            # Generate AI explanation
            explanation = explanation_gen.generate_explanation(question, correction)
            multilingual_explanations = explanation_gen.generate_multilingual_explanation(question, correction)
            
            # Create unique ID
            chap_id = re.sub(r'[^a-zA-Z0-9]+', '', chapitre)[:5].upper()
            unique_id = f"{niveau[:1]}AC_{chap_id}_{ex_num:03d}_{os.path.splitext(ex_name)[0]}"
            print({
                "id": unique_id,
                "niveau": niveau,
                "chapitre": chapitre,
                "matiere": matiere,
                "question": question,
                "reponse_attendue": "",  # Can be filled manually later
                "correction": correction,
                "explication": explanation,
                "explications": multilingual_explanations,
                "type_exercice": "Résolution",
                "difficulte": difficulte,
                "tags": tags,
                "source": ex_name,
                "metadata": {
                    "has_correction": bool(correction),
                    "question_length": len(question),
                    "correction_length": len(correction) if correction else 0
                }
            })
            dataset.append({
                "id": unique_id,
                "niveau": niveau,
                "chapitre": chapitre,
                "matiere": matiere,
                "question": question,
                "reponse_attendue": "",  # Can be filled manually later
                "correction": correction,
                "explication": explanation,
                "explications": multilingual_explanations,
                "type_exercice": "Résolution",
                "difficulte": difficulte,
                "tags": tags,
                "source": ex_name,
                "metadata": {
                    "has_correction": bool(correction),
                    "question_length": len(question),
                    "correction_length": len(correction) if correction else 0
                }
            })
    
    # Save the dataset
    if dataset:
        with open(output_file, 'w', encoding='utf-8') as f:
            for entry in dataset:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"\nSuccessfully saved {len(dataset)} exercises to {output_file}")
        
        # Also save explanations cache
        explanation_gen.save_cache()
    else:
        print("\nNo exercises were extracted from the PDFs")

if __name__ == "__main__":
    create_dataset_from_pdfs(PDF_ROOT_DIR, FULL_OUTPUT_FILE)