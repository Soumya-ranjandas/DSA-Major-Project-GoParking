
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN javac java_backend/*.java

ENV GOPARKING_PAYMENT_API_HOST=127.0.0.1
ENV GOPARKING_PAYMENT_API_PORT=8765
ENV GOPARKING_RAZORPAY_MODE=test

EXPOSE 10000

CMD ["sh", "-c", "cd /app/java_backend && java ParkingServer & python /app/payment_api.py & exec streamlit run /app/app.py --server.port ${PORT:-10000} --server.address 0.0.0.0"]
