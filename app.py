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

    try:
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(filepath)
            uploaded_content = df.to_string(index=False)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                uploaded_content = f.read()

        return "✅ Dataset uploaded successfully!"

    except Exception as e:
        return f"Upload Error: {str(e)}"


def generate_local_pairs(text: str, max_pairs: int = 10) -> list[dict]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pairs = []

    for line in lines[:max_pairs]:
        pairs.append({
            "instruction": f"Explain the cybersecurity concept: {line}",
            "output": f"{line} is an important concept in cybersecurity. It helps users understand threats, protection methods, and safe practices for securing systems and information."
        })

    if not pairs:
        pairs.append({
            "instruction": "Explain the main topic of the uploaded dataset.",
            "output": "The uploaded dataset contains cybersecurity-related information that can be transformed into instruction-output pairs for AI training."
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

        output_path = os.path.join(app.config["OUTPUT_FOLDER"], "output.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return Response(
            json.dumps(result, indent=2, ensure_ascii=False),
            content_type="application/json; charset=utf-8"
        )

    except Exception as e:
        return f"System Error: {str(e)}"


@app.route("/download")
def download():
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], "output.json")

    if not os.path.exists(output_path):
        return "❌ No output file found. Please generate data first."

    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)