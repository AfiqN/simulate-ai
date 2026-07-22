FROM python:3.11-slim
WORKDIR /app

# Install deps one-by-one to stay within Railway's memory limit
RUN pip install --no-cache-dir httpx==0.27.2
RUN pip install --no-cache-dir rich==13.9.4
RUN pip install --no-cache-dir fastapi==0.115.6
RUN pip install --no-cache-dir "uvicorn[standard]==0.32.1"
RUN pip install --no-cache-dir aiosqlite==0.20.0
RUN pip install --no-cache-dir PyYAML==6.0.2
RUN pip install --no-cache-dir python-dotenv==1.0.1

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]
