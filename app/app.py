from flask import Flask, jsonify
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUESTS = Counter("app_requests_total", "Total requests", ["endpoint"])

@app.route("/")
def home():
    REQUESTS.labels(endpoint="/").inc()
    return jsonify(message="Hello from my DevOps project", version="1.0")

@app.route("/health")
def health():
    return jsonify(status="ok")

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
