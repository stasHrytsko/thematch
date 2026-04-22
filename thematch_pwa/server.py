#!/usr/bin/env python3
"""Local development server — serves PWA static files + all API routes."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory

app = Flask(__name__, static_folder="public", static_url_path="")

# Import route handlers (services are instantiated at module level)
from api.compatibility import compatibility
from api.user import user as user_handler
from api.history import history
from api.feedback import feedback

app.add_url_rule("/api/compatibility", view_func=compatibility, methods=["POST", "OPTIONS"])
app.add_url_rule("/api/user",          view_func=user_handler,  methods=["POST", "OPTIONS"])
app.add_url_rule("/api/history",       view_func=history,       methods=["GET",  "OPTIONS"])
app.add_url_rule("/api/feedback",      view_func=feedback,      methods=["POST", "OPTIONS"])


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    full = os.path.join(app.static_folder, path)
    if path and os.path.isfile(full):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n  TheMatch  →  http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
