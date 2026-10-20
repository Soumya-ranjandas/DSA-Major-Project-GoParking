
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN javac java_backend/*.java

EXPOSE 10000

CMD ["sh", "-c", "cd java_backend && java ParkingServer & exec streamlit run app.py --server.port ${PORT:-10000} --server.address 0.0.0.0"]
