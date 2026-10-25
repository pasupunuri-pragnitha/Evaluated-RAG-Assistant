import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from app.config import settings


def get_db_connection() -> psycopg.Connection:
    """Create and return a psycopg connection with pgvector registered."""
    conn = psycopg.connect(
        settings.get_database_url(),
        row_factory=dict_row,
        autocommit=False
    )
    register_vector(conn)
    return conn
