import requests
import json
import os
from flask import Flask, render_template, request, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["OUTPUT_FOLDER"] = "outputs"

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Make sure apis.json exists
if not os.path.exists("apis.json"):
    with open("apis.json", "w") as f:
        json.dump([], f)

uploaded_content = ""


@app.route("/")
def index():
    with open("apis.json", "r") as f:
        apis = json.load(f)
    return render_template("index.html", apis=apis)


@app.route("/upload", methods=["POST"])
def upload_file():
    global uploaded_content
    file = request.files["file"]

    if not file:
        return "No file uploaded."

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        uploaded_content = f.read()

    return "Dataset uploaded successfully!"


@app.route("/add_api", methods=["POST"])
def add_api():
    api_name = request.form["api_name"]
    api_url = request.form["api_url"]
    api_token = request.form["api_token"]
    model_name = request.form["model_name"]

    new_api = {
        "name": api_name,
        "url": api_url,
        "token": api_token,
        "model": model_name
    }

    with open("apis.json", "r") as f:
        apis = json.load(f)

    apis.append(new_api)

    with open("apis.json", "w") as f:
        json.dump(apis, f, indent=2)

    return "API Added Successfully!"


@app.route("/generate", methods=["POST"])
def generate():
    try:
        selected_api_name = request.form.get("selected_api")
        prompt = request.form.get("prompt")

        if not selected_api_name:
            return "No API selected."

        # Load APIs
        with open("apis.json", "r") as f:
            apis = json.load(f)

        selected_api = next((api for api in apis if api["name"] == selected_api_name), None)

        if not selected_api:
            return "Selected API not found."

        headers = {
            "Authorization": f"Bearer {os.getenv('HF_TOKEN')}",
            "Content-Type": "application/json"
        }

        global uploaded_content

        full_prompt = f"""
You are a professional instruction dataset generator.

Dataset:
{uploaded_content}

Task:
{prompt}

Return ONLY valid JSON list:
[
  {{"instruction":"...","output":"..."}}
]
"""

        # OpenAI-compatible chat format (required for Zephyr router)
        payload = {
    "inputs": full_prompt,
    "parameters": {
        "max_new_tokens": 300,
        "temperature": 0.7
    }
}


        response = requests.post(
            selected_api["url"],
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            return f"API Error: {response.text}"

        result = response.json()

        output_path = os.path.join(app.config["OUTPUT_FOLDER"], "output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return json.dumps(result, indent=2)

    except Exception as e:
        return f"System Error: {str(e)}"


@app.route("/download")
def download():
    return send_file("outputs/output.json", as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
