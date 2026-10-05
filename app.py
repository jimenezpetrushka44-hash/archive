from flask import Flask, render_template, request, jsonify
from recommender import recommend_song

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Send a valid JSON object."}), 400

    message = data.get("message")

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Please write how you feel."}), 400

    try:
        result = recommend_song(message.strip())
        return jsonify(result)
    except Exception:
        app.logger.exception("Recommendation failed")
        return jsonify({
            "error": "I couldn't find songs right now. Please try again."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)