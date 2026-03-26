from flask import Flask, render_template, request, send_file
import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
APIS_FILE = "apis.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def load_apis():
    if os.path.exists(APIS_FILE):
        with open(APIS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ✅ FIXED DATASET READER (VERY IMPORTANT)
def read_dataset_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content[:3000]  # limit size

    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return content[:3000]

    elif ext == ".csv":
        df = pd.read_csv(file_path)

        # ✅ LIMIT DATA (VERY IMPORTANT)
        df = df.head(20)

        if len(df.columns) > 5:
            df = df.iloc[:, :5]

        return df.to_string(index=False)

    else:
        raise ValueError("Unsupported file format (.txt, .json, .csv only)")


@app.route("/")
def home():
    apis = load_apis()
    return render_template("index.html", apis=apis)


@app.route("/generate", methods=["POST"])
def generate():
    apis = load_apis()

    user_prompt = request.form.get("prompt", "").strip()
    selected_api_name = request.form.get("selected_api", "").strip()
    uploaded_file = request.files.get("dataset_file")

    if not user_prompt:
        return render_template("index.html", apis=apis, result="Please enter a prompt.")

    if not selected_api_name:
        return render_template("index.html", apis=apis, result="Please select an API.")

    if not uploaded_file or uploaded_file.filename == "":
        return render_template("index.html", apis=apis, result="Please upload a dataset file.")

    dataset_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
    uploaded_file.save(dataset_path)

    try:
        dataset_content = read_dataset_file(dataset_path)
    except Exception as e:
        return render_template("index.html", apis=apis, result=f"Dataset error: {str(e)}")

    selected_api = None
    for api in apis:
        if api["name"] == selected_api_name:
            selected_api = api
            break

    if not selected_api:
        return render_template("index.html", apis=apis, result="API not found.")

    api_url = selected_api["url"]
    token_env_name = selected_api["token_env"]
    api_token = os.getenv(token_env_name)

    if not api_token:
        return render_template(
            "index.html",
            apis=apis,
            result=f"API token not found. Add {token_env_name} in .env or Render."
        )

    # ✅ SHORT PROMPT (VERY IMPORTANT)
    full_prompt = f"""
Dataset sample:
{dataset_content}

User request:
{user_prompt}

Generate ONLY 3 instruction-output pairs in JSON format.
Each must include:
- instruction
- input
- output
Keep answer short.
"""

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [
            {"role": "system", "content": "You are an AI instruction generator."},
            {"role": "user", "content": full_prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.3
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()

        generated_text = data["choices"][0]["message"]["content"]

        output_data = {
            "dataset_file": uploaded_file.filename,
            "generated_instructions": generated_text
        }

        output_path = os.path.join(OUTPUT_FOLDER, "output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)

        return render_template("index.html", apis=apis, result=generated_text)

    except requests.exceptions.HTTPError as e:
        return render_template("index.html", apis=apis, result=f"HTTP Error: {str(e)}")

    except Exception as e:
        return render_template("index.html", apis=apis, result=f"System Error: {str(e)}")


@app.route("/download")
def download():
    output_path = os.path.join(OUTPUT_FOLDER, "output.json")

    if os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)

    return "No output file found."


if __name__ == "__main__":
    app.run(debug=True)