# repositories/post_repo.py
import sqlite3
from models.post import Post
import os
from config import config

entorno = os.getenv("FLASK_ENV", "development")
DB_PATH = config[entorno].DB_PATH

def obtener_conexion():
    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn

def insertar_post(agente_id, contenido, created_at):
    with obtener_conexion() as conn:
        conn.execute(
            "INSERT INTO posts (agente_id, contenido, created_at) VALUES (?, ?, ?)",
            (agente_id, contenido, created_at)
        )
        conn.commit()

def insertar_multiples_posts(lista_posts):
    with obtener_conexion() as conn:
        conn.executemany(
            "INSERT INTO posts (agente_id, contenido, created_at) VALUES (?, ?, ?)",
            lista_posts
        )
        conn.commit()

def eliminar_todos_los_posts():
    with obtener_conexion() as conn:
        conn.execute("DELETE FROM posts")
        conn.commit()

def obtener_feed(limit=20, desde=None):
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        query = """
            SELECT posts.contenido, agentes.nombre, posts.created_at
            FROM posts
            JOIN agentes ON posts.agente_id = agentes.id
        """
        params = []
        if desde:
            query += " WHERE posts.created_at > ?"
            params.append(desde)
        query += " ORDER BY posts.created_at DESC LIMIT ?"
        params.append(limit)
        return cursor.execute(query, params).fetchall()

def obtener_posts_por_agente(agente_id):
    with obtener_conexion() as conn:
        return conn.execute(
            "SELECT * FROM posts WHERE agente_id = ? ORDER BY created_at DESC",
            (agente_id,)
        ).fetchall()

def obtener_feed_con_paginacion(limit=10, offset=0):
    with obtener_conexion() as conn:
        return conn.execute("""
            SELECT posts.contenido, agentes.nombre, posts.created_at
            FROM posts
            JOIN agentes ON posts.agente_id = agentes.id
            ORDER BY posts.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()

def contar_posts():
    with obtener_conexion() as conn:
        return conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]