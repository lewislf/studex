from flask import Flask, jsonify, request
from flask_cors import CORS

from database.database import *
from routes.user_routes import user_bp
from routes.subject_routes import subject_bp
from routes.document_routes import document_bp

app = Flask(__name__)
CORS(app)
HOST = "0.0.0.0"
SOCKET = 5000

init_db()

app.register_blueprint(user_bp)
app.register_blueprint(subject_bp)
app.register_blueprint(document_bp)

if __name__ == "__main__":
    app.run(host=HOST, port=SOCKET, debug=True)
