from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
HUGGIN_FACE_TOKEN="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"

# 🔒 Gated model – requires Hugging Face token
model_id = "mistralai/Mistral-7B-Instruct-v0.2"
hf_token = "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"  # Replace with your actual token

# Load tokenizer and model with authentication
tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)#use_auth_token
model = AutoModelForCausalLM.from_pretrained(model_id, token=hf_token)

# Create text generation pipeline
#pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=200)
pipe = pipeline("text2text-generation", model="google/flan-t5-base")

# Example input
context = "The mitochondria is known as the powerhouse of the cell."
question = "What is the function of mitochondria in a cell?"

prompt = f"""Context:\n{context}\n\nQuestion:\n{question}\n\nAnswer:"""

# Run generation
response = pipe(prompt)[0]["generated_text"]

# Print result
print("Answer:", response)

