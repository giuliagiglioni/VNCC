FROM python:3.10-slim

WORKDIR /app

COPY . .

ENV KMP_DUPLICATE_LIB_OK=TRUE

RUN pip install --no-cache-dir flask torch transformers faiss-cpu

EXPOSE 5000

CMD ["python", "app.py"]