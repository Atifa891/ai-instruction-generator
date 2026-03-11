from flask import Flask, render_template, request, send_file
import os
import json
import pandas as pd
from openai import OpenAI

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    # Read file content
    if file.filename.endswith(".csv"):
        df = pd.read_csv(filepath)
        uploaded_content = df.to_string()
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            uploaded_content = f.read()

    return "Dataset uploaded successfully."


@app.route("/generate", methods=["POST"])
def generate():
    try:
        prompt = request.form.get("prompt")

        if not prompt:
            return "No prompt provided."

        full_prompt = f"""
You are a professional instruction dataset generator.

Dataset:
{uploaded_content}

User request:
{prompt}

Generate 5 high-quality instruction-output pairs.

Return the result strictly as JSON:

[
  {{
    "instruction": "...",
    "output": "..."
  }}
]
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You generate instruction-output pairs."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7
        )

        result = response.choices[0].message.content

        output_path = os.path.join(app.config["OUTPUT_FOLDER"], "output.json")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        return result

    except Exception as e:
        return f"System Error: {str(e)}"


@app.route("/download")
def download():
    return send_file("outputs/output.json", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)