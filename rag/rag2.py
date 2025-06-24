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
