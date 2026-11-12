import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger

from database.database import *
from routes.user_routes import user_bp
from routes.subject_routes import subject_bp
from routes.document_routes import document_bp
from routes.deck_routes import deck_bp
from routes.flashcard_routes import flashcard_bp
from routes.mindmap_routes import mindmap_bp
from routes.summary_routes import summary_bp
from routes.study_routes import study_bp
from routes.admin_routes import admin_bp
from routes.document_routes import cleanup_stale_uploads

app = Flask(__name__)

# Origens permitidas; CORS_ORIGINS (separadas por vírgula) sobrescreve o padrão.
_CORS_PADRAO = (
    "https://studex-dusky.vercel.app,"
    "http://localhost:5173,http://127.0.0.1:5173"   # Vite em desenvolvimento
)
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", _CORS_PADRAO).split(",") if o.strip()
]
CORS(app, origins=CORS_ORIGINS)
HOST = "0.0.0.0"
SOCKET = int(os.environ.get("PORT", 5000))

FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

# Mesmo limite de tamanho de upload que o client já aplica.
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024


@app.errorhandler(413)
def handle_payload_too_large(error):
    return jsonify({"error": "Arquivo excede o tamanho máximo permitido (250MB)."}), 413

# Swagger UI em http://localhost:5000/docs
swagger_template = {
    "info": {
        "title": "Studex API",
        "description": (
            "API do Studex: geração e armazenamento de materiais de estudo "
            "(resumo, mapa mental, flashcards) a partir de PDFs."
        ),
        "version": "v1",
    },
}
Swagger(
    app,
    template=swagger_template,
    config={"hide_top_bar": True, "specs_route": "/docs/"},
    merge=True,
)

app.register_blueprint(user_bp)
app.register_blueprint(subject_bp)
app.register_blueprint(document_bp)
app.register_blueprint(deck_bp)
app.register_blueprint(flashcard_bp)
app.register_blueprint(mindmap_bp)
app.register_blueprint(summary_bp)
app.register_blueprint(study_bp)
app.register_blueprint(admin_bp)

# Remove PDFs órfãos de uploads interrompidos; falha aqui não pode impedir a subida.
try:
    cleanup_stale_uploads(24)
except Exception:
    pass


@app.get("/routes")
def list_routes():
    """
    Lista todas as rotas registradas na aplicação.
    ---
    tags:
      - Meta
    responses:
      200:
        description: Lista de rotas (rule, endpoint e métodos HTTP)
    """
    rotas = [
        {
            "rule": rule.rule,
            "endpoint": rule.endpoint,
            "methods": sorted(rule.methods - {"HEAD", "OPTIONS"}),
        }
        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    ]
    return jsonify(rotas)


if __name__ == "__main__":
    init_db()
    app.run(host=HOST, port=SOCKET, debug=FLASK_DEBUG)
