import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer
import os 
OUTPUT_DIR = "../output"

dataset_location = os.path.join(OUTPUT_DIR, "math_dataset_corr_ai.jsonl")
# Load and prepare docs from JSONL
docs = []
with open(dataset_location, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        question = data.get("question", "")
        correction = data.get("raw_correction", "")
        combined = f"Question:\n{question}\n\nCorrection:\n{correction}"
        docs.append(combined)

# Save docs to a .pkl file
with open("math_docs.pkl", "wb") as f:
    pickle.dump(docs, f)

# Load embedding model
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Create embeddings
embeddings = embedding_model.encode(docs, show_progress_bar=True)

# Save FAISS index
dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(embeddings)
faiss.write_index(index, "math_index.faiss")

print("✅ Saved: math_index.faiss and math_docs.pkl")
