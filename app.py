from flask import Flask, render_template, request, send_file, Response
import os
import json
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

uploaded_content = ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    global uploaded_content

    if "file" not in request.files:
        return "No file uploaded."

    file = request.files["file"]

    if file.filename == "":
        return "No file selected."

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    # Read dataset
    if file.filename.endswith(".csv"):
        df = pd.read_csv(filepath)
        uploaded_content = df.to_string(index=False)
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            uploaded_content = f.read()

    return "✅ Dataset uploaded successfully!"


# 🔥 Local AI-like generator (no API)
def generate_local_pairs(text, max_pairs=10):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pairs = []

    for i, line in enumerate(lines[:max_pairs], start=1):
        pairs.append({
            "instruction": f"Explain the cybersecurity concept: {line}",
            "output": f"{line} is an important concept in cybersecurity. It helps protect systems, data, and users from potential threats and attacks."
        })

    if not pairs:
        pairs.append({
            "instruction": "Explain the dataset topic.",
            "output": "The dataset contains cybersecurity-related information useful for training AI models."
        })

    return pairs


@app.route("/generate", methods=["POST"])
def generate():
    global uploaded_content

    prompt = request.form.get("prompt", "").strip()

    if not uploaded_content:
        return "❌ Please upload a dataset first."

    try:
        result = generate_local_pairs(uploaded_content, max_pairs=10)
    