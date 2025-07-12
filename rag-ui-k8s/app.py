from flask import Flask, request, render_template
import requests

app = Flask(__name__)

RAG_ENDPOINT = "http://rag-service:80/query"

@app.route("/", methods=["GET", "POST"])
def index():
    answer = None
    query = None

    if request.method == "POST":
        query = request.form.get("query")
        try:
            response = requests.post(RAG_ENDPOINT, json={"query": query}, timeout=5)
            data = response.json()
            answer = data.get("result", "No answer found.")
        except Exception as e:
            answer = f"Errore nella richiesta al RAG: {e}"

    return render_template("index.html", answer=answer, query=query)