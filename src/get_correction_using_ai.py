import requests
import time
import json
import os
import re
from dotenv import load_dotenv
import sys
from config import OUTPUT_DIR
load_dotenv()
API_KEY = os.getenv('API_KEY')

input_file = os.path.join(OUTPUT_DIR, 'math_dataset.jsonl') #math_dataset_url
output_file = os.path.join(OUTPUT_DIR, 'math_dataset_corr_ai.jsonl') #math_dataset_ai_url

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://yourapp.com",
    "X-Title": "Math Correction Script"
}

MODEL = "deepseek/deepseek-chat:free"

ANSWER_KEYWORDS = [
    'Résoudre', 
    "**Résultat**", 
    "**Réponse finale**", 
    "Résultat", 
    "Réponse finale", 
    "Calcul final", 
    "Solution", 
    "Réponse", 
    "Valeur finale", 
    "Conclusion", 
    "Résultat final", 
    "Réponse correcte", 
    "Conclusion finale", 
    "Interprétation", 
    "Vérification", 
    "Explication", 
    "Approximation", 
    "Calculé", 
    "Réponse exacte", 
    "Solution complète", 
    "Méthode", 
    "Démonstration", 
    "Estimation", 
    "Réponse obtenue",
    "Réponse définitive", 
    "Résultat obtenu", 
    "Solution correcte", 
    "Calcul détaillé", 
    "Explication détaillée", 
    "Justification", 
    "Démarche", 
    "Procédure", 
    "Réponse simplifiée", 
    "Calcul intermédiaire", 
    "Pas à pas", 
    "Équation résolue", 
    "Formule appliquée", 
    "Hypothèse", 
    "Test final", 
    "Méthode utilisée", 
    "Preuve", 
    "Calcul complet", 
    "Vérification des résultats", 
    "Analyse des résultats"
]

def get_correction(question: str) -> str:
    data = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": f"{question}\n\nCorrige chaque expression pas à pas, en français, avec les calculs détaillés."
        }]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=HEADERS, json=data)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        # STOP IMMEDIATELY on any error
        print(f"\n❌ API Error {response.status_code} → {response.text}\nStopping execution.")
        sys.exit(1)  # Immediate exit
        return None

def split_correction(raw_answer: str):
    if "---" in raw_answer :
        blocks = [block.strip() for block in raw_answer.split('---') if block.strip()]
    elif "###" in raw_answer:
        blocks = [block.strip() for block in raw_answer.split("###") if block.strip()]
    else:
        blocks = [block.strip() for block in raw_answer.split() if block.strip()]
    steps, final_answer = "", ""

    for block in blocks:
        answer=""
        for keyword in ANSWER_KEYWORDS:
            if keyword in block:
                answer = block[block.find(keyword) + len(keyword):]



        if "😊" not in block: steps += block + "\n"
        if "😊" not in answer: final_answer += answer + "\n"

    steps = steps.replace("J'espère que ces explications t'ont aidé ! 😊", "")
    steps = re.sub(r"(\*\*|\#|\(|\)|\\|\*|\[|\]|_|\\\|)", "", steps)
    final_answer = re.sub(r"(\*\*|\#|\(|\)|\\|\*|\[|\]|_|\\\|)", "", final_answer)
    return steps.strip(), final_answer.strip()

def count_lines(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r', encoding='utf-8') as f:
        return sum(1 for _ in f)

def generate_dataset(
    max_lines_per_run: int = 10,
    wait_time_between_calls: int = 2
):
    start_index = count_lines(output_file)
    print(f"▶️ Output already has {start_index} entries. Will start processing from index {start_index}.")

    processed = 0

    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'a', encoding='utf-8') as outfile:
        for idx, line in enumerate(infile):
            if idx < start_index:
                continue

            entry = json.loads(line)
            question = entry.get("question", "")
            print(f"\n🔄 Processing #{idx} → ID: {entry.get('id')}")

            correction = get_correction(question)

            explanation, answer = split_correction(correction)
            entry["raw_correction"] = correction
            entry["explanation"] = explanation
            entry["answer"] = answer

            outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")
            outfile.flush()

            processed += 1
            print(f"✅ Saved #{idx} → {entry.get('id')}")

            time.sleep(wait_time_between_calls)

            if processed >= max_lines_per_run:
                print("🔔 Reached MAX_LINES_PER_RUN. Stop for now.")
                break

    print("✅ Script completed or paused. You can rerun to continue.")

