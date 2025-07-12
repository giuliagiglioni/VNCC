from transformers import AutoTokenizer, AutoModel
import torch
import faiss
import numpy as np

model_name = "NeuML/pubmedbert-base-embeddings"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
model.eval()

with open("documents.txt", "r", encoding="utf-8") as f:
    docs = [line.strip() for line in f if line.strip()]

def embed(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
    return cls_embedding

print("Generating embeddings for {len(docs)} documents...")
vectors = np.array([embed(doc) for doc in docs]).astype("float32")
norms = np.linalg.norm(vectors, axis=1, keepdims=True)
vectors = vectors / norms

index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)
faiss.write_index(index, "biomed_index.faiss")

with open("docs_store.txt", "w", encoding="utf-8") as f:
    for doc in docs:
        f.write(doc + "\n")

print("Index created and saved successfully!")
print("- biomed_index.faiss")
print("- docs_store.txt")