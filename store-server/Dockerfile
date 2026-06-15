FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY store-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared-domain /shared-domain
RUN pip install --no-cache-dir /shared-domain

COPY store-server/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
