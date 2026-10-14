import hashlib

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import llm_client

load_dotenv()
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
CACHE: dict[str, dict] = {}  # protects the free quota: same file + backend = one call


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyze")
def analyze():
    file = request.files.get("pdf")
    if file is None or not file.filename:
        return jsonify(error="Επίλεξε ένα αρχείο PDF."), 400
    data = file.read()
    if not data.startswith(b"%PDF"):
        return jsonify(error="Το αρχείο δεν είναι PDF."), 400

    private = request.form.get("private") == "1"
    key = hashlib.sha256(data).hexdigest() + (":local" if private else ":cloud")
    if key in CACHE:
        return jsonify(CACHE[key])
    try:
        material = llm_client.generate_study_material(data, private=private)
    except ValueError as err:
        return jsonify(error=f"Δεν μπόρεσα να φτιάξω υλικό: {err}"), 422
    except Exception as err:  # quota, network, missing key
        msg = str(err)
        if "429" in msg or "quota" in msg.lower():
            return jsonify(error="Όριο χρήσης (429). Περίμενε ένα λεπτό και ξαναδοκίμασε."), 429
        return jsonify(error=f"Σφάλμα μοντέλου: {msg}"), 502
    CACHE[key] = material
    return jsonify(material)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
