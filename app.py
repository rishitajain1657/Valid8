from flask import Flask, jsonify, render_template, request, send_from_directory

from core.rules import evaluate_patient_triage
from core.sbar import generate_sbar_brief

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/valid8-logo.png")
def logo_asset():
    return send_from_directory(app.root_path, "Valid8 Logo.png", mimetype="image/png")


@app.route("/api/triage", methods=["POST"])
def triage():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "A JSON object body is required."}), 400

    try:
        triage_result = evaluate_patient_triage(payload)
        sbar_result = generate_sbar_brief(payload, triage_result)
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"triage": triage_result, "sbar": sbar_result})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
