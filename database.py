import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.gutyrssxtpuxndflkceq:Erin83390454@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
)

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn