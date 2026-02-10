FROM python:3.10-slim

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY . .

ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py", "--mode", "web"]
