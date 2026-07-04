import hashlib
import hmac
import os
import sqlite3
from pathlib import Path
from typing import Any
from cryptography.fernet import Fernet
import numpy as np
from datetime import date

from user import Usuario
from materia import Materia
from resumo import Resumo
from baralho import Baralho

DB_PATH = Path("users.db")
KEY_PATH = Path("db_key.key")

def _get_or_create_key(key_path: Path = KEY_PATH) -> bytes:
    """
    Get or create the encription key for the database. 
    The key is used to encrypt the user names and stored in a db_key.key file.
    """
    
    # Check if the key already exists
    if key_path.exists():
        key = key_path.read_bytes()
        
        return key

    # Else, it creates the key
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    os.chmod(key_path, 0o600)

    return key


def _encrypt_passwd(passwd: str, key: bytes) -> bytes:
    """
    Encrypt the user passwd with Fernet symetric encryption.
    """
    cipher = Fernet(key)
    
    return cipher.encrypt(passwd.encode("utf-8"))


def _decrypt_passwd(payload: bytes, key: bytes) -> str:
    """
    Decrypt the user passwd with Fernet symetric encryption.
    """
    cipher = Fernet(key)

    return cipher.decrypt(payload).decode("utf-8")

def _open_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Open a connection to the SQLite database.

    Enable foreign key (i.e. a column (or group of columns) in one table that references the primary key of another table.)
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn

def init_db(db_path: Path = DB_PATH, key_path: Path = KEY_PATH) -> None:
    """
    Create the database and tables if they do not exist
        - users: stores the user_id, name, email and encrypted password.
        - subjects: stores all subjects
        - summaries: stores all summaries of the database
    """
    _get_or_create_key(key_path)

    with _open_connection(db_path) as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                passwd_encrypted BLOB NOT NULL 
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                desc TEXT NOT NULL,
                creation_date DATETIME,
                domain INTEGER NOT NULL, 

                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                creation_date DATETIME,

                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                acuracia INTEGER NOT NULL,
                creation_date DATETIME,
                novos INTEGER NOT NULL,
                aprendendo INTEGER NOT NULL,
                review INTEGER NOT NULL,

                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            """
        )


    return None


def save_user_db(name: str, passwd: str, email: str, db_path: Path = DB_PATH, key_path: Path = KEY_PATH) -> int | None:
    """
    Register a new user in the database. 
    
    Returns the user_id of the new entry.
    """
    key = _get_or_create_key(key_path)
    encrypted_passwd = _encrypt_passwd(passwd, key)
    
    with _open_connection(db_path) as conn:
        cur = conn.cursor()

        cur.execute("BEGIN")
        ins = """
            INSERT INTO users (name, email, passwd_encrypted) 
            VALUES (?, ?, ?)
        """

        cur.execute(ins, (name, email, encrypted_passwd))

        user_id = cur.lastrowid

        conn.commit()
        return user_id


def get_users_db(
    name: str,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a user with the name

    Returns the list of users with the same name
    """

    with _open_connection(db_path) as conn:
        rows = conn.execute("""SELECT id, name, email, passwd_encrypted 
                                    FROM users 
                                    WHERE name LIKE ?""", (f"%{name}%",)).fetchall()  
        
        if rows is None:
            return None

        users = []
        for user_id, name, email, hash_passwd in rows:
            users.append(Usuario(name, email, hash_passwd, user_id))
        
        return users

def get_user_db(
    user_id: int,
    db_path: Path = DB_PATH,
) -> Usuario | None:
    """
    Try to search a user with id

    Returns the user, if it exists
    """

    with _open_connection(db_path) as conn:
        row = conn.execute("""SELECT id, name, email, passwd_encrypted 
                                    FROM users 
                                    WHERE id = ?""", (user_id,)).fetchone()  
        
        if row is None:
            return None

        user = None
        user_id, name, email, hash_passwd = row
        user = Usuario(name, email, hash_passwd, user_id)
        
        return user


def delete_user_db(user_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a user by user_id. (LGPD - Right to be forgotten)
    
    Returns True if a user was deleted, False if no such user_id exists.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted


def count_people_db(db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered people in the database.
    """
    with _open_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        return int(row[0]) if row else 0

def print_all_people_db(db_path: Path = DB_PATH, key_path: Path = KEY_PATH) -> None:
    """
    Prints all registered users.
    """
    with _open_connection(db_path) as conn:
        rows = conn.execute("SELECT id, name FROM users").fetchall()
        print("Registered people:")
        for user_id, name in rows:
            print(f"ID: {user_id}, Name: {name}")



### SUBJECT ###

def save_subject_db(user_id: int, name: str, desc: str, domain: int, creation_date: date, db_path: Path = DB_PATH, key_path: Path = KEY_PATH) -> int | None:
    """
    Register a new subject in the database. 
    
    Returns the subject_id of the new entry.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()

        cur.execute("BEGIN")
        ins = """
            INSERT INTO subjects (user_id, name, desc, creation_date, domain) 
            VALUES (?, ?, ?, ?, ?)
        """

        cur.execute(ins, (user_id, name, desc, creation_date, domain))

        subject_id = cur.lastrowid

        conn.commit()
        return subject_id


def get_subjects_db(
    name: str,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a subject with the name

    Returns the list of subjects with the same name
    """

    with _open_connection(db_path) as conn:
        rows = conn.execute("""SELECT id, user_id, name, desc, creation_date, domain 
                                    FROM subjects 
                                    WHERE name LIKE ?""", (f"%{name}%",)).fetchall()  
        
        if rows is None:
            return None

        subjects = []
        for subject_id, user_id, name, desc, creation_date, domain in rows:
            subjects.append(Materia(user_id, name, desc, domain, creation_date, subject_id))
        
        return subjects

def get_subject_db(
    subject_id: int,
    db_path: Path = DB_PATH,
) -> Materia | None:
    """
    Try to search a subject with id

    Returns the subject, if it exists
    """

    with _open_connection(db_path) as conn:
        row = conn.execute("""SELECT id, user_id, name, desc, creation_date, domain 
                                    FROM subjects 
                                    WHERE id = ?""", (subject_id,)).fetchone()  
        
        if row is None:
            return None

        subject = None
        subject_id, user_id, name, desc, creation_date, domain = row
        subject = Materia(user_id, name, desc, domain, creation_date, subject_id)
        
        return subject


def delete_subject_db(subject_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a subject by subject_id. (LGPD - Right to be forgotten)
    
    Returns True if a subject was deleted, False if no such subject_id exists.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute("DELETE FROM subjects WHERE id = ?", (int(subject_id),))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted

def count_subjects_db(user_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered subjects in the database with given user_id.
    """
    with _open_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM subjects WHERE user_id = ?", (user_id,),).fetchone()
        return int(row[0]) if row else 0


### SUMMARY ###

def save_summary_db(subject_id: int, titulo: str, conteudo: str, creation_date: date, db_path: Path = DB_PATH) -> int | None:
    """
    Register a new summary in the database. 
    
    Returns the summary_id of the new entry.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()

        cur.execute("BEGIN")
        ins = """
            INSERT INTO summaries (subject_id, titulo, conteudo, creation_date) 
            VALUES (?, ?, ?, ?)
        """

        cur.execute(ins, (subject_id, titulo, conteudo, creation_date))

        summary_id = cur.lastrowid

        conn.commit()
        return summary_id


def get_summaries_db(
    titulo: str,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a summary with the name

    Returns the list of summarys with the same name
    """

    with _open_connection(db_path) as conn:
        rows = conn.execute("""SELECT id, subject_id, titulo, conteudo, creation_date
                                    FROM summaries 
                                    WHERE titulo LIKE ?""", (f"%{titulo}%",)).fetchall()  
        
        if rows is None:
            return None

        summaries = []
        for summary_id, subject_id, titulo, conteudo, creation_date in rows:
            summaries.append(Resumo(subject_id, titulo, conteudo, creation_date, summary_id))
        
        return summaries

def get_summary_db(
    summary_id: int,
    db_path: Path = DB_PATH,
) -> Resumo | None:
    """
    Try to search a summary with id

    Returns the summary, if it exists
    """

    with _open_connection(db_path) as conn:
        row = conn.execute("""SELECT id, subject_id, titulo, conteudo, creation_date
                                    FROM summaries 
                                    WHERE id = ?""", (summary_id,)).fetchone()  
        
        if row is None:
            return None

        summary = None
        summary_id, subject_id, titulo, conteudo, creation_date = row
        summary = Resumo(subject_id, titulo, conteudo, creation_date, summary_id)
        
        return summary


def delete_summary_db(summary_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a summary by summary_id. (LGPD - Right to be forgotten)
    
    Returns True if a summary was deleted, False if no such summary_id exists.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute("DELETE FROM summaries WHERE id = ?", (int(summary_id),))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted

def count_summaries_db(subject_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered summaries in the database with given subject_id.
    """
    with _open_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM summaries WHERE subject_id = ?", (subject_id,),).fetchone()
        return int(row[0]) if row else 0

### DECK ###

def save_deck_db(subject_id: int, titulo: str, acuracia: int, novos: int, aprendendo: int, review: int, creation_date: date, db_path: Path = DB_PATH) -> int | None:
    """
    Register a new deck in the database. 
    
    Returns the deck_id of the new entry.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()

        cur.execute("BEGIN")
        ins = """
            INSERT INTO decks (subject_id, titulo, acuracia, novos, aprendendo, review, creation_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        cur.execute(ins, (subject_id, titulo, acuracia, novos, aprendendo, review, creation_date))

        deck_id = cur.lastrowid

        conn.commit()
        return deck_id


def get_decks_db(
    titulo: str,
    db_path: Path = DB_PATH,
) -> list | None:
    """
    Try to search a deck with the name

    Returns the list of decks with the same name
    """

    with _open_connection(db_path) as conn:
        rows = conn.execute("""SELECT id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date
                                    FROM decks 
                                    WHERE titulo LIKE ?""", (f"%{titulo}%",)).fetchall()  
        
        if rows is None:
            return None

        decks = []
        for deck_id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date in rows:
            decks.append(Baralho(subject_id, titulo, acuracia, novos, aprendendo, review, creation_date, deck_id))
        
        return decks

def get_deck_db(
    deck_id: int,
    db_path: Path = DB_PATH,
) -> Resumo | None:
    """
    Try to search a deck with id

    Returns the deck, if it exists
    """

    with _open_connection(db_path) as conn:
        row = conn.execute("""SELECT id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date
                                    FROM decks 
                                    WHERE id = ?""", (deck_id,)).fetchone()  
        
        if row is None:
            return None

        deck = None
        deck_id, subject_id, titulo, acuracia, novos, aprendendo, review, creation_date = row
        deck = Baralho(subject_id, titulo, acuracia, novos, aprendendo, review, creation_date, deck_id)
        
        return deck


def delete_deck_db(deck_id: int, db_path: Path = DB_PATH) -> bool:
    """
    Atomic deletion of a deck by deck_id. (LGPD - Right to be forgotten)
    
    Returns True if a deck was deleted, False if no such deck_id exists.
    """
    with _open_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute("BEGIN")
        cur.execute("DELETE FROM decks WHERE id = ?", (int(deck_id),))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted

def count_deck_db(subject_id: int, db_path: Path = DB_PATH) -> int:
    """
    Returns the total number of registered deck in the database with given subject_id.
    """
    with _open_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM decks WHERE subject_id = ?", (subject_id,),).fetchone()
        return int(row[0]) if row else 0
