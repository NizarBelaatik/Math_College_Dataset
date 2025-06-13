import requests
import time
import json
import os
from dotenv import load_dotenv
import re 
API_KEY = os.getenv('API_KEY')

MAX_LINES=5

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://yourapp.com",
    "X-Title": "Math Correction Script"
}
MODEL = "deepseek/deepseek-chat:free"

# Input/output file paths
input_file = "math_dataset.jsonl"
output_file = "corrected_math_dataset.jsonl"


# Function to get correction from DeepSeek
def get_correction(question: str) -> str:
    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"{question}\n\nCorrige chaque expression pas à pas, en français, avec les calculs détaillés."
            }
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=HEADERS, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Erreur {response.status_code}: {response.text}"

# Function to remove any emoji or non-alphanumeric characters
#def clean_string(input_string): return re.sub(r'[^\w\s]', '', input_string)


def split_correction(raw_answer: str):
    blocks = [block.strip() for block in raw_answer.split('---') if block.strip()]
    results = []
    steps=""
    final_answer=""
    for block in blocks:
    
        if "**Résultat**"  in block:
            answer = block[r.find("**Résultat**") + len("**Résultat**") + 2:]
        elif "**Réponse finale**"  in block:
            answer = block[block.find("**Réponse finale**") + len("**Réponse finale**") + 2:]
        else:
            answer = block[block.find("Résultat") + len("Résultat") + 2:]

        answer = answer.replace("** :","") and answer.replace("le","")
        #steps+=block+"\n"
        #final_answer+=answer+"\n"
        if "😊" not in block: steps+=block+"\n"
        if "😊" not in answer: final_answer+=answer+"\n"
            
    steps = steps.replace("J'espère que ces explications t'ont aidé ! 😊","")
    steps=re.sub(r"(\*\*|\#|\(|\)|\\|\*|\[|\]|_|\\\|)", "", steps)
    final_answer=re.sub(r"(\*\*|\#|\(|\)|\\|\*|\[|\]|_|\\\|)", "", final_answer)
    return steps ,final_answer
    
# Process each JSONL entry
with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
    for idx, line in enumerate(infile):
        if idx >= MAX_LINES:
            break

        entry = json.loads(line)
        question = entry.get("question", "")
        print(f"\n🔄 Processing: {idx}  \n{entry['id']}")

        correction = get_correction(question)
        entry["raw_answer"],entry["explanation"],entry["answer"] = correction, split_correction(correction)

        outfile.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"✅ Correction added to {entry['id']}")
        time.sleep(1.5)  # Avoid hitting rate limits

print(f"\n🎉 Done! Processed {MAX_LINES} entries. Output saved to: {output_file}")