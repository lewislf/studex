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

app = Flask(__name__)
CORS(app)
HOST = "0.0.0.0"
SOCKET = 5000

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
    app.run(host=HOST, port=SOCKET, debug=True)
