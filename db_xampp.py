# db_xampp.py
import os
import re
import pymysql

# ====== XAMPP MySQL Ayarları ======
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "bonus_social_db")



def get_conn(db=None):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=db,
        autocommit=True,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_database():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
    conn.close()


def split_sql_statements(sql_text: str):
    sql_text = re.sub(r"--.*?$", "", sql_text, flags=re.MULTILINE)
    sql_text = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    parts = [p.strip() for p in sql_text.split(";")]
    return [p for p in parts if p]


def apply_ddl(ddl_sql: str):
    """
    DDL komutlarını uygular.
    - CREATE TABLE => CREATE TABLE IF NOT EXISTS (tekrar çalıştırınca hata vermesin)
    """
    ensure_database()
    conn = get_conn(DB_NAME)

    executed, errors = [], []
    stmts = split_sql_statements(ddl_sql)

    # ✅ tekrar çalıştırınca "already exists" hatası olmasın
    stmts = [
        re.sub(r"(?i)^\s*create\s+table\s+", "CREATE TABLE IF NOT EXISTS ", s)
        for s in stmts
    ]

    with conn.cursor() as cur:
        for s in stmts:
            try:
                cur.execute(s)
                executed.append(s)
            except Exception as e:
                errors.append({"statement": s, "error": str(e)})

    conn.close()
    return executed, errors


def list_tables():
    ensure_database()
    conn = get_conn(DB_NAME)
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES;")
        rows = cur.fetchall()
    conn.close()
    return [list(r.values())[0] for r in rows]


def run_select_reports(queries: list[str], max_rows=50):
    """
    Sadece SELECT raporlarını çalıştırır.
    DB’de olmayan tabloyu kullanan sorguları hata yerine 'atlandı' yapar.
    """
    ensure_database()
    existing_tables = set(t.lower() for t in list_tables())

    conn = get_conn(DB_NAME)
    results = []

    table_pattern = re.compile(r"\b(from|join)\s+`?([a-zA-Z0-9_]+)`?", re.IGNORECASE)

    with conn.cursor() as cur:
        for q in queries:
            q_strip = (q or "").strip().rstrip(";")
            if not q_strip:
                continue

            if not q_strip.lower().startswith("select"):
                results.append({"query": q_strip, "error": "Sadece SELECT çalıştırılır."})
                continue

            referenced = [m.group(2).lower() for m in table_pattern.finditer(q_strip)]
            missing = [t for t in referenced if t not in existing_tables]

            if missing:
                results.append({
                    "query": q_strip + ";",
                    "skipped": True,
                    "error": f"Bu tablolar DB'de yok: {', '.join(missing)} (rapor atlandı)"
                })
                continue

            try:
                cur.execute(q_strip + ";")
                rows = cur.fetchmany(max_rows)
                results.append({"query": q_strip + ";", "rows": rows})
            except Exception as e:
                results.append({"query": q_strip + ";", "error": str(e)})

    conn.close()
    return results


def seed_demo_data():
    """
    Eğer Users boşsa örnek veri basar.
    Bu kolon isimleri senin tablolarınla uyumlu: Username, Email, Content, CreatedAt
    """
    ensure_database()
    conn = get_conn(DB_NAME)

    with conn.cursor() as cur:
        # Users var mı?
        cur.execute("SHOW TABLES LIKE 'Users';")
        if not cur.fetchone():
            conn.close()
            return {"seeded": False, "reason": "Users tablosu yok"}

        # Users boş mu?
        cur.execute("SELECT COUNT(*) AS c FROM Users;")
        if cur.fetchone()["c"] > 0:
            conn.close()
            return {"seeded": False, "reason": "Zaten veri var"}

        # Users
        cur.execute("""
            INSERT INTO Users (Username, Email) VALUES
            ('ali', 'ali@example.com'),
            ('ayse', 'ayse@example.com'),
            ('mehmet', 'mehmet@example.com');
        """)

        # Posts
        cur.execute("SHOW TABLES LIKE 'Posts';")
        if cur.fetchone():
            cur.execute("""
                INSERT INTO Posts (UserID, Content, CreatedAt) VALUES
                (1, 'Merhaba dünya!', NOW()),
                (2, 'Bugün hava çok güzel.', NOW()),
                (3, 'SQL ve Flask projem çalışıyor.', NOW());
            """)

        # Comments
        cur.execute("SHOW TABLES LIKE 'Comments';")
        if cur.fetchone():
            cur.execute("""
                INSERT INTO Comments (PostID, UserID, Content, CreatedAt) VALUES
                (1, 2, 'Harika!', NOW()),
                (2, 1, 'Kesinlikle katılıyorum.', NOW());
            """)

        # Likes
        cur.execute("SHOW TABLES LIKE 'Likes';")
        if cur.fetchone():
            cur.execute("""
                INSERT INTO Likes (PostID, UserID, CreatedAt) VALUES
                (1, 1, NOW()),
                (1, 3, NOW());
            """)

    conn.close()
    return {"seeded": True}
