from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import JSONLoader

# Step 1: Load your JSONL into documents
import json
import os 
OUTPUT_DIR = "../output"

dataset_location = os.path.join(OUTPUT_DIR, "math_dataset_corr_ai.jsonl")

docs = []
with open(dataset_location, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        docs.append(item["question"] + "\n" + item["raw_correction"])  # You can combine fields

# Step 2: Embed documents
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_texts(docs, embeddings)

# Save the index
vectorstore.save_local("math_index")
