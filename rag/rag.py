import json
import os 
OUTPUT_DIR = "../output"

dataset_location = os.path.join(OUTPUT_DIR, "math_dataset_corr_ai.jsonl")

# Load and clean your JSONL dataset
docs = []
with open(dataset_location, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        question = data.get("question", "")
        correction = data.get("explanation", "")#raw_correction
        combined = f"Question:\n{question}\n\nCorrection:\n{correction}"
        docs.append(combined)



#Embed and store documents

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Load embedding model
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Compute embeddings
embeddings = model.encode(docs, show_progress_bar=True)

# Create FAISS index
dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(np.array(embeddings))

# Save index
faiss.write_index(index, "math_index.faiss")
