import os
import re
import json
import pdfplumber

# ---------- Configuration ----------
PDF_ROOT_DIR = "../dataset"  # Your dataset folder
OUTPUT_DIR = "../output"
EXTRACTED_TEXTS_DIR = os.path.join(OUTPUT_DIR, "extracted_texts")
FULL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "math_dataset.jsonl")
NIVEAUX = ["1ère année collège", "2ème année collège", "3ème année collège"]

os.makedirs(EXTRACTED_TEXTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------- Utilities ----------

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                page_text = re.sub(r'\s+', ' ', page_text.strip())
                page_text = page_text.replace('−', '-').replace('²', '^2').replace('√', 'sqrt')
                text += page_text + "\n"
    return text


def detect_niveau(folder_path):
    folder = folder_path.lower()
    if '3ac' in folder or '3ème' in folder:
        return "3ème année collège"
    elif '2ac' in folder or '2ème' in folder:
        return "2ème année collège"
    elif '1ac' in folder or '1ère' in folder:
        return "1ère année collège"
    return "3ème année collège"


def extract_exercises(text):
    pattern = r'(Exercice \d+)(.*?)(?=Exercice \d+|$)'
    return {int(re.search(r'\d+', m[0]).group()): m[1].strip() for m in re.findall(pattern, text, re.DOTALL)}


def extract_corrections(text):
    pattern = r"(Corrigé\s*(?:de l['’]|d[ue]\s*)?exercice\s*(\d+))(.*?)(?=Corrigé\s*(?:de l['’]|d[ue]\s*)?exercice\s*\d+|$)"
    corrections = {}
    matches = list(re.finditer(pattern, text, re.DOTALL | re.IGNORECASE))

    if matches:
        for match in matches:
            ex_num = int(match.group(2))
            correction = match.group(3).strip()
            corrections[ex_num] = correction
    else:
        # Fallback: try splitting corrections by numbering
        fallback_pattern = r"(\d+)\)\s*(.*?)(?=\d+\)|$)"
        for match in re.finditer(fallback_pattern, text, re.DOTALL):
            ex_num = int(match.group(1))
            correction = match.group(2).strip()
            corrections[ex_num] = correction

    return corrections



def infer_matiere_chapitre(pdf_name, text):
    pdf_name = pdf_name.lower()
    text = text.lower()
    if 'thales' in pdf_name or 'thalès' in text:
        return "géométrie", "Théorème de Thalès"
    elif 'ordre' in pdf_name or 'opérations' in pdf_name or 'operation' in text:
        return "algèbre", "Ordre et Opérations"
    elif 'equation' in text or 'équations' in text:
        return "algèbre", "Équations"
    elif 'fraction' in pdf_name or 'fractions' in text:
        return "arithmétique", "Produits et quotients de fractions"
    elif 'puissance' in pdf_name or 'puissances' in text:
        return "arithmétique", "Propriétés sur les puissances de 10"
    return "mathématiques", "Non spécifié"


# ---------- Main Processing ----------

def create_dataset(pdf_root_dir, output_file):
    dataset = []
    pdf_files = []

    # First collect all PDF files
    for root, _, files in os.walk(pdf_root_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append((file, os.path.join(root, file), root))

    # Pair exercise and correction files
    file_pairs = {}

    for file, path, root in pdf_files:
        base_name = file.lower()
        # Remove '-corrige' or '-correction' for pairing
        normalized_name = re.sub(r'(-)?(corrige|correction)', '', base_name)
        normalized_name = normalized_name.replace('--', '-')  # Clean double dashes if any

        if normalized_name not in file_pairs:
            file_pairs[normalized_name] = {'exercise': None, 'correction': None, 'root': root}

        if 'corrige' in base_name or 'correction' in base_name:
            file_pairs[normalized_name]['correction'] = path
        else:
            file_pairs[normalized_name]['exercise'] = path

    for ex_name, files in file_pairs.items():
        ex_path = files['exercise']
        corr_path = files['correction']

        if not ex_path:
            continue  # Skip if no exercise file found

        niveau = detect_niveau(files.get('root', ''))
        matiere, chapitre = infer_matiere_chapitre(ex_name, "")

        print(f"[PROCESSING] {ex_path}")
        try:
            ex_text = extract_text_from_pdf(ex_path)
            exercises = extract_exercises(ex_text)

            corrections = {}
            if corr_path and os.path.exists(corr_path):
                corr_text = extract_text_from_pdf(corr_path)
                corrections = extract_corrections(corr_text)

            for num, question in exercises.items():
                dataset.append({
                    "id": f"{niveau[0]}AC_{chapitre[:3].upper()}_{num:02d}",
                    "niveau": niveau,
                    "chapitre": chapitre,
                    "matiere": matiere,
                    "question": question,
                    "reponse_attendue": "",  # Optional: add logic or manual
                    "correction": corrections.get(num, ""),
                    "type_exercice": "Résolution",
                    "difficulte": "moyen",
                    "source": os.path.basename(ex_path)
                })

            # Save extracted texts
            base_name = os.path.basename(ex_path).replace('.pdf', '')
            with open(os.path.join(EXTRACTED_TEXTS_DIR, base_name + "_ex.txt"), "w", encoding="utf-8") as f:
                f.write(ex_text)
            if corr_path and os.path.exists(corr_path):
                with open(os.path.join(EXTRACTED_TEXTS_DIR, base_name + "_corr.txt"), "w", encoding="utf-8") as f:
                    f.write(corr_text)

        except Exception as e:
            print(f"[ERROR] Failed to process {ex_path}: {e}")

    if not dataset:
        print("[INFO] No exercises extracted from any PDFs.")
        return

    with open(output_file, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[SUCCESS] {len(dataset)} exercises saved to '{output_file}'")


if __name__ == "__main__":
    create_dataset(PDF_ROOT_DIR, FULL_OUTPUT_FILE)