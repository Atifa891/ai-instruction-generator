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


def read_dataset_file(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif file_ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif file_ext == ".csv":
        df = pd.read_csv(file_path)
        return df.to_string(index=False)

    else:
        raise ValueError("Unsupported file format. Please upload .txt, .json, or .csv files.")


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
        return render_template(
            "index.html",
            apis=apis,
            result=f"Could not read the uploaded dataset: {str(e)}"
        )

    selected_api = None
    for api in apis:
        if api["name"] == selected_api_name:
            selected_api = api
            break

    if not selected_api:
        return render_template("index.html", apis=apis, result="Selected API not found.")

    api_url = selected_api["url"]
    token_env_name = selected_api["token_env"]
    api_token = os.getenv(token_env_name)

    if not api_token:
        return render_template(
            "index.html",
            apis=apis,
            result=f"API token not found. Please add {token_env_name} to your .env file or Render Environment Variables."
        )

    full_prompt = f"""
You are an AI instruction generator.

Dataset:
{dataset_content}

User request:
{user_prompt}

Task:
Generate clear, structured instructions based on the dataset and the user's request.
Return useful, understandable, and well-organized instructions.
If possible, format the final answer as JSON with instruction, input, and output fields.
"""

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "HuggingFaceH4/zephyr-7b-beta",
        "messages": [
            {
                "role": "system",
                "content": "You are an AI instruction generator. Create clear, structured instructions based on the dataset and the user's request."
            },
            {
                "role": "user",
                "content": full_prompt
            }
        ],
        "max_tokens": 400,
        "temperature": 0.7
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        generated_text = data["choices"][0]["message"]["content"]

        output_data = {
            "dataset_file": uploaded_file.filename,
            "file_type": os.path.splitext(uploaded_file.filename)[1].lower(),
            "selected_api": selected_api_name,
            "user_prompt": user_prompt,
            "generated_instructions": generated_text
        }

        output_path = os.path.join(OUTPUT_FOLDER, "output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

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