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
        correction = data.get("raw_correction", "")
        combined = f"Question:\n{question}\n\nCorrection:\n{correction}"
        docs.append(combined)



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



from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

model_id = "microsoft/phi-3-mini-4k-instruct"

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype="auto"
)

# Create generation pipeline
chat = pipeline("text-generation", model=model, tokenizer=tokenizer)




index = faiss.read_index("math_index.faiss")

# Load embedding model again
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

def ask_question(user_query):
    # Embed user question
    query_vec = embedding_model.encode([user_query])

    # Search for top 3 similar docs
    D, I = index.search(query_vec, k=3)
    retrieved_docs = [docs[i] for i in I[0]]

    # Build context
    context = "\n---\n".join(retrieved_docs)

    # Prompt for the model
    prompt = f"""Voici quelques exercices et corrections utiles :\n{context}\n\nMaintenant, réponds à la question suivante en expliquant : {user_query}"""

    # Generate response
    result = chat(prompt, max_new_tokens=300)[0]["generated_text"]
    return result

# Example:
print(ask_question("Comment résoudre 7 × 8 + 13 ?"))
