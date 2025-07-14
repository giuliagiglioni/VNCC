# Accesso a un RAG tramite un servizio Kubernetes

## Descrizione del progetto

Questo progetto consiste nell’esposizione di un servizio **RAG (Retrieval-Augmented Generation)** di tipo biomedicale all’interno di un cluster Kubernetes, rendendolo accessibile tramite un'interfaccia web.  

Il sistema è composto da due componenti principali:

1.  **Backend RAG**: un servizio Flask che carica e indicizza un dataset di documenti biomedicali tramite embedding generati con PubMedBERT. Gli embedding sono indicizzati con FAISS per una ricerca efficiente. Il backend espone un endpoint API /query che riceve domande e restituisce risposte basate sui documenti più rilevanti.

2.  **Frontend Web**: un’interfaccia Flask con pagina HTML che permette agli utenti di inserire domande e visualizzare le risposte ottenute dal backend. Il frontend invia richieste al backend tramite chiamate HTTP.



L’obiettivo non è tanto analizzare il modello RAG, quanto mostrare come containerizzare e rendere accessibile un servizio su un cluster Kubernetes distribuito (1 master + 1 worker), con un focus sull’architettura, il deployment e l’accesso esterno.

---


## Architettura del cluster

Il cluster Kubernetes è costituito da due macchine virtuali su cui è installato Xubuntu 24. 
Le due macchine virtuali sono connesse ad una rete con NAT gestita da VirtualBox. 

Per quanto riguarda i nodi Kubernetes, una VM ospita il nodo master e l’altra il nodo worker:
* **master** (`192.168.43.10`)
* **worker** (`192.168.43.11`)


![Figura 1 – Architettura del cluster Kubernetes](img/cluster-architettura.jpg)

---



## Struttura del sistema

```
.
├── rag-biomed/
│   ├── app.py     
│   ├── documents.txt           
│   ├── build_index.py           
│   ├── biomed_index.faiss     
│   ├── docs_store.txt        
│   └── Dockerfile
│
├── rag-k8s/
│   ├── deployment.yaml
│   └── service.yaml
│
├── rag-ui-k8s/
│   ├── app.py
│   ├── requirements.txt
│   ├── rag-flask-ui-deployment.yaml
│   ├── rag-flask-ui-service.yaml
│   ├── Dockerfile
│   └── templates/        
│       └── index.html

```

---

## Implementazione RAG

### Dataset

Il dataset `documents.txt`contiene circa 160 frasi cliniche e scientifiche di alta qualità relative all'**apparato cardiovascolare**.

### Costruzione indice

Il file `build_index.py` carica **PubMedBERT**, un modello BERT pre-addestrato su articoli biomedici, legge il dataset e genera embedding. 
Costruisce quindi un indice FAISS e lo salva su `biomed_index.faiss`.
Salva anche tutti i documenti in `docs_store.txt` per mantenerli allineati con l’indice FAISS.
L’indice FAISS e i documenti originali sono salvati su disco per un rapido caricamento.

Comando per generare l’indice FAISS:

```bash
python build_index.py
```

### Backend RAG
Il backend Flask `app.py` espone un endpoint /query che riceve query testuali, calcola embedding, effettua ricerca nell’indice FAISS e restituisce il documento più rilevante come risposta.

Comando per avviare il backend RAG:
```bash
python app.py
```

### Dockerizzazione
Creazione e pubblicazione **immagine Docker** del RAG.

`rag-biomed/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . .

ENV KMP_DUPLICATE_LIB_OK=TRUE

RUN pip install --no-cache-dir flask torch transformers faiss-cpu

EXPOSE 5000

CMD ["python", "app.py"]
```

Eseguire i comandi:
```bash
docker build -t giuliagiglioni/rag-biomed:latest .
```
```bash
docker push giuliagiglioni/rag-biomed:latest
```


### Kubernetes
Creazione **Deployment** e **Service** per il RAG.

`rag-k8s/deployment.yaml`:

```yaml	
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag
  template:
    metadata:
      labels:
        app: rag
    spec:
      containers:
      - name: rag-container
        image: giuliagiglioni/rag-biomed:latest
        ports:
        - containerPort: 5000
```

`rag-k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-service
spec:
  selector:
    app: rag
  type: NodePort
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
```

Eseguire i comandi:
```bash
kubectl apply -f deployment.yaml
```
```bash
kubectl apply -f service.yaml
```

Per testare:
```bash
kubectl get pods
```
```bash
kubectl get svc
```

---

## Implementazione interfaccia RAG 

L’interfaccia utente è stata implementata in Flask con un template HTML basato su Bootstrap per un aspetto semplice e pulito.

### Frontend Web

Il file `app.py` crea una web app con Flask per interrogare il RAG.
Invia richieste HTTP POST al backend (rag-service), recupera le risposte e le mostra nella pagina `index.html`.


File `app.py`:
```python
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
```

Il file `index.html` è un template HTML per l'**interfaccia utente** di una web app Flask.
Serve a creare una pagina web interattiva per porre domande in ambito biomedicale a un RAG.

File `index.html`:
```html 
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Biomedical RAG</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">

<div class="container py-5">
  <h1 class="mb-4">🔬 Biomedical RAG Interface</h1>

  <form method="POST" class="mb-4">
    <div class="mb-3">
      <label for="query" class="form-label">Enter your biomedical question:</label>
      <input type="text" class="form-control" id="query" name="query" value="{{ query or '' }}" required>
    </div>
    <button type="submit" class="btn btn-primary">Ask</button>
  </form>

  {% if answer %}
  <div class="card">
    <div class="card-header">📘 Answer</div>
    <div class="card-body">
      <p class="card-text">{{ answer }}</p>
    </div>
  </div>
  {% endif %}
</div>

</body>
</html>
```


### Dockerizzazione
Creazione e pubblicazione **immagine Docker** dell'interfaccia.

`rag-ui-k8s/Dockerfile`:

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

EXPOSE 5000

CMD ["flask", "run"]
```

Eseguire i comandi:
```bash
docker build -t giuliagiglioni/rag-flask-ui:latest .
```
```bash
docker push giuliagiglioni/rag-flask-ui:latest
```

### Kubernetes
Creazione **Deployment** e **Service** per l'interfaccia.

`rag-ui-k8s/rag-flask-ui-deployment.yaml`:

```yaml	
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-flask-ui
spec:
  replicas: 1
  selector:
  matchLabels:
    app: rag-flask-ui
  template:
  metadata:
    labels:
    app: rag-flask-ui
  spec:
    containers:
    - name: rag-flask-ui
    image: giuliagiglioni/rag-flask-ui:latest
    ports:
    - containerPort: 5000
```

`rag-ui-k8s/rag-flask-ui-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-flask-ui
spec:
  type: LoadBalancer
  selector:
    app: rag-flask-ui
  ports:
    - port: 5000
      targetPort: 5000
```

Il servizio Kubernetes è di tipo LoadBalancer, per consentire l’accesso esterno.

Eseguire i comandi:

```bash
kubectl apply -f rag-flask-ui-deployment.yaml
```
```bash
kubectl apply -f rag-flask-ui-service.yaml
```


Per testare:

```bash
kubectl get pods
```
```bash
kubectl get svc
```

---


## Accesso al Servizio (Accesso al RAG)
Per rendere l’interfaccia accessibile anche da fuori il cluster (senza conoscere IP/porta dei nodi), è possibile usare MetalLB come LoadBalancer.

Eseguendo il comando
```bash
kubectl get svc
```
otteniamo l'indirizzo IP esterno e la relativa porta.

Nel nostro caso l'IP esterno è `192.168.43.241` e la porta è la `5000`.

L’indirizzo per **accedere all’interfaccia web del RAG** è quindi: 
```bash
http://192.168.43.241:5000
```

L'utente apre il browser all'indirizzo specificato, inserisce una domanda e ottiene la risposta.

---



## Test

L'applicazione è stata testata con successo inviando domande come:

```text
When does a heart attack occur?	
```

Il servizio ha risposto restituendo il documento biomedicale più simile semanticamente, dimostrando il corretto funzionamento sia della pipeline RAG che della distribuzione Kubernetes.

![Figura 2 – Risposta del RAG biomedicale all'interfaccia web](img/risposta-interfaccia.png)

---

## Possibili estensioni

- **Miglioramento del modello RAG**  
  Effettuare un *fine-tuning* del modello PubMedBERT su dataset più ampi o specifici per ottenere risposte più precise e contestualizzate.

- **Estensione dell'interfaccia web**  
  Aggiungere funzionalità come la **cronologia delle domande**.

- **Caching delle risposte frequenti**  
  Implementare un meccanismo di caching  per rispondere più rapidamente a domande già poste, riducendo il carico sul backend.

---

## Conclusioni

Questo progetto mostra come strutturare e rendere accessibile tramite una semplice interfaccia web un microservizio RAG all’interno di Kubernetes.
Il frontend e il backend sono completamente separati e comunicano tramite Service interni, seguendo le best practice di orchestrazione.
Il sistema è scalabile, portabile e facilmente estendibile.

---
## Autore
Giulia Giglioni


---

