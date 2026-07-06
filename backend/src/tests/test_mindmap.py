import json
from datetime import date

from database.database import (
    save_user_db,
    save_subject_db,
    save_mindmap_db,
    get_mindmap_db,
    get_mindmaps_db,
    delete_mindmap_db,
    count_mindmaps_db,
)


CONTEUDO = {
    "nodes": [{"id": "n1", "data": {"label": "TCP/IP"}}],
    "edges": [{"source": "n1", "target": "n1"}],
}


def _user_and_subject(db_path, key_path):
    user_id = save_user_db(
        "Felipe", "123456", "felipe@email.com",
        db_path=db_path, key_path=key_path,
    )
    subject_id = save_subject_db(
        user_id=user_id, name="Redes", desc="Redes de Computadores",
        domain=55, creation_date=date.today(), db_path=db_path,
    )
    return user_id, subject_id


def test_save_mindmap(temp_db):
    db_path, key_path = temp_db
    _, subject_id = _user_and_subject(db_path, key_path)

    mind_map_id = save_mindmap_db(
        subject_id=subject_id,
        titulo="Mapa TCP/IP",
        conteudo=json.dumps(CONTEUDO, ensure_ascii=False),
        creation_date=date.today(),
        db_path=db_path,
    )

    assert mind_map_id == 1

    mind_map = get_mindmap_db(mind_map_id, db_path=db_path)

    assert mind_map.titulo == "Mapa TCP/IP"
    assert mind_map.subject_id == subject_id
    # o conteudo é guardado como JSON e faz round-trip
    assert json.loads(mind_map.conteudo) == CONTEUDO


def test_delete_mindmap(temp_db):
    db_path, key_path = temp_db
    _, subject_id = _user_and_subject(db_path, key_path)

    mind_map_id = save_mindmap_db(
        subject_id=subject_id,
        titulo="Mapa POO",
        conteudo=json.dumps(CONTEUDO, ensure_ascii=False),
        creation_date=date.today(),
        db_path=db_path,
    )

    assert count_mindmaps_db(subject_id, db_path) == 1

    deleted = delete_mindmap_db(mind_map_id, db_path=db_path)

    assert deleted is True
    assert get_mindmap_db(mind_map_id, db_path=db_path) is None
    assert count_mindmaps_db(subject_id, db_path) == 0


def test_search_mindmap(temp_db):
    db_path, key_path = temp_db
    _, subject_id = _user_and_subject(db_path, key_path)

    save_mindmap_db(
        subject_id=subject_id,
        titulo="Herança",
        conteudo=json.dumps(CONTEUDO, ensure_ascii=False),
        creation_date=date.today(),
        db_path=db_path,
    )

    mind_maps = get_mindmaps_db("Her", db_path=db_path)

    assert mind_maps is not None
    assert len(mind_maps) == 1
    assert mind_maps[0].titulo == "Herança"


def test_count_mindmap(temp_db):
    db_path, key_path = temp_db
    _, subject_id = _user_and_subject(db_path, key_path)

    save_mindmap_db(
        subject_id=subject_id, titulo="Mapa 1",
        conteudo=json.dumps(CONTEUDO, ensure_ascii=False),
        creation_date=date.today(), db_path=db_path,
    )
    save_mindmap_db(
        subject_id=subject_id, titulo="Mapa 2",
        conteudo=json.dumps(CONTEUDO, ensure_ascii=False),
        creation_date=date.today(), db_path=db_path,
    )

    assert count_mindmaps_db(subject_id, db_path) == 2
