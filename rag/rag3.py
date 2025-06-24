

import pickle

# Load FAISS index
import faiss
index = faiss.read_index("math_index.faiss")

# Load embedding model
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Load saved docs
with open("math_docs.pkl", "rb") as f:
    docs = pickle.load(f)


import json
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Load FAISS index
index = faiss.read_index("math_index.faiss")

# Load embedding model
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# Load docs (pre-saved from earlier step)
with open("math_docs.pkl", "rb") as f:
    docs = pickle.load(f)

# Load LLM (Phi-3 mini)
model_id = "microsoft/Phi-3-mini-4k-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", torch_dtype="auto")
chat = pipeline("text-generation", model=model, tokenizer=tokenizer)

# Define question-answer function
def ask_question(user_query):
    query_vec = embedding_model.encode([user_query])
    D, I = index.search(query_vec, k=3)
    retrieved_docs = [docs[i] for i in I[0]]
    context = "\n---\n".join(retrieved_docs)
    prompt = f"""Voici quelques exercices et corrections utiles :\n{context}\n\nMaintenant, réponds à la question suivante en expliquant : {user_query}"""
    result = chat(prompt, max_new_tokens=300)[0]["generated_text"]
    return result

# Test
print(ask_question("Comment résoudre 7 × 8 + 13 ?"))
