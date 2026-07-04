from flask import Flask, jsonify, request

from database.database import *
from routes.user_routes import user_bp
from routes.subject_routes import subject_bp

app = Flask(__name__)
HOST = "0.0.0.0"
SOCKET = 5000

app.register_blueprint(user_bp)
app.register_blueprint(subject_bp)

if __name__ == "__main__":
    app.run(host=HOST, port=SOCKET, debug=True)
