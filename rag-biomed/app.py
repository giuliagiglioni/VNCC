from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModel
import torch
import faiss
import numpy as np
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

app = Flask(__name__)

model_name = "NeuML/pubmedbert-base-embeddings"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
model.eval()

index = faiss.read_index("biomed_index.faiss")
with open("docs_store.txt", "r", encoding="utf-8") as f:
    docs = [line.strip() for line in f if line.strip()]

def embed(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
    cls_embedding = cls_embedding / np.linalg.norm(cls_embedding)
    return cls_embedding.astype("float32")

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    query_text = data.get("query", "").strip()
    if not query_text:
        return jsonify({"error": "Missing or empty 'query' field"}), 400

    query_vec = embed(query_text).reshape(1, -1)

    D, I = index.search(query_vec, 1)

    similarity = float(D[0][0])

    if similarity < 0.7:
        return jsonify({
            "query": query_text,
            "result": "I'm not sure how to respond to that. Please ask a medical question.",
            "similarity": similarity
        })

    return jsonify({
        "query": query_text,
        "result": docs[I[0][0]],
        "similarity": similarity
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
