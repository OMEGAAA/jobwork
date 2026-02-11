"""
db.py - データベース抽象化モジュール (SQLite / PostgreSQL対応)
クエストとコメントのCRUD操作を提供
"""
import os
import sqlite3
import streamlit as st
from datetime import datetime
from contextlib import contextmanager
from zoneinfo import ZoneInfo
import logging

# ロガー設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 日本時間のタイムゾーン
JST = ZoneInfo("Asia/Tokyo")

def get_jst_now() -> str:
    """日本時間の現在時刻をISO形式で返す"""
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

# データベース設定
# Streamlitのsecretsに設定がある場合はPostgreSQLを使用、それ以外はSQLite
DB_TYPE = "sqlite"
try:
    if "SUPABASE_URL" in st.secrets:
        try:
            import psycopg2
            import psycopg2.extras
            DB_TYPE = "postgres"
        except ImportError:
            pass
except Exception:
    # secrets.tomlがない、またはキーがない場合はSQLiteにフォールバック
    pass

DATABASE_SQLITE = "quest_board.db"

@contextmanager
def get_connection():
    """データベース接続のコンテキストマネージャー"""
    if DB_TYPE == "postgres":
        conn = psycopg2.connect(
            dsn=st.secrets["SUPABASE_URL"],
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        try:
            yield conn
        finally:
            conn.close()
    else:
        # SQLite
        conn = sqlite3.connect(DATABASE_SQLITE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

def _execute_query(query: str, params: tuple = (), return_id: bool = False):
    """
    クエリ実行ヘルパー
    - SQLite (?) と Postgres (%s) のプレースホルダの違いを吸収
    - INSERT時のID取得の違いを吸収
    """
    if DB_TYPE == "postgres":
        # Postgres用にプレースホルダを変換 (? -> %s)
        pg_query = query.replace("?", "%s")
        if return_id:
            pg_query += " RETURNING id"
        
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(pg_query, params)
                if return_id:
                    new_id = cursor.fetchone()['id']
                    conn.commit()
                    return new_id
                else:
                    conn.commit()
                    return cursor.rowcount
    else:
        # SQLite
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            if return_id:
                return cursor.lastrowid
            return cursor.rowcount

def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """SELECTクエリ実行ヘルパー（全件取得）"""
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if DB_TYPE == "postgres":
            # RealDictCursorはdictを返す
            return [dict(row) for row in cursor.fetchall()]
        else:
            # SQLite Row factory
            return [dict(row) for row in cursor.fetchall()]

def _fetch_one(query: str, params: tuple = ()) -> dict | None:
    """SELECTクエリ実行ヘルパー（1件取得）"""
    if DB_TYPE == "postgres":
        query = query.replace("?", "%s")
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

def init_db():
    """データベースとテーブルを初期化"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # テーブル作成クエリの定義（DBタイプ別）
        if DB_TYPE == "postgres":
            # PostgreSQL用DDL
            queries = [
                """
                CREATE TABLE IF NOT EXISTS quests (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'Backlog',
                    priority INTEGER DEFAULT 3,
                    due_date TEXT,
                    estimated_minutes INTEGER DEFAULT 30,
                    assignee TEXT,
                    creator TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    recurrence_type TEXT DEFAULT 'none',
                    recurrence_end_date TEXT,
                    parent_quest_id INTEGER,
                    recurrence_weekdays TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS comments (
                    id SERIAL PRIMARY KEY,
                    quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
                    "user" TEXT NOT NULL, -- userは予約語の可能性
                    content TEXT NOT NULL,
                    file_path TEXT,
                    log_type TEXT DEFAULT 'user',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT DEFAULT 'その他',
                    tags TEXT DEFAULT '',
                    memo TEXT DEFAULT '',
                    is_favorite INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    last_viewed_at TIMESTAMP WITH TIME ZONE,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS quest_templates (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER DEFAULT 3,
                    estimated_minutes INTEGER DEFAULT 30,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]
        else:
            # SQLite用DDL
            queries = [
                """
                CREATE TABLE IF NOT EXISTS quests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'Backlog',
                    priority INTEGER DEFAULT 3,
                    due_date TEXT,
                    estimated_minutes INTEGER DEFAULT 30,
                    assignee TEXT,
                    creator TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quest_id INTEGER NOT NULL,
                    user TEXT NOT NULL,
                    content TEXT NOT NULL,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    category TEXT DEFAULT 'その他',
                    tags TEXT DEFAULT '',
                    memo TEXT DEFAULT '',
                    is_favorite INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    last_viewed_at TIMESTAMP,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS quest_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER DEFAULT 3,
                    estimated_minutes INTEGER DEFAULT 30,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            ]

        for q in queries:
            cursor.execute(q)
            
        conn.commit()

        # カラム追加のマイグレーション（SQLiteのみ、既存データ維持のため）
        if DB_TYPE != "postgres":
            _migrate_sqlite(conn)

def _migrate_sqlite(conn):
    """SQLiteのマイグレーション処理"""
    cursor = conn.cursor()
    migrations = [
        "ALTER TABLE quests ADD COLUMN estimated_minutes INTEGER DEFAULT 30",
        "ALTER TABLE quests ADD COLUMN recurrence_type TEXT DEFAULT 'none'",
        "ALTER TABLE quests ADD COLUMN recurrence_end_date TEXT",
        "ALTER TABLE quests ADD COLUMN parent_quest_id INTEGER",
        "ALTER TABLE quests ADD COLUMN recurrence_weekdays TEXT",
        "ALTER TABLE comments ADD COLUMN file_path TEXT",
        "ALTER TABLE comments ADD COLUMN log_type TEXT DEFAULT 'user'"
    ]
    for query in migrations:
        try:
            cursor.execute(query)
        except sqlite3.OperationalError:
            pass
    conn.commit()

# ========== クエスト操作 ==========

def create_quest(title: str, description: str, priority: int, due_date: str, creator: str, 
                 estimated_minutes: int = 30, recurrence_type: str = "none", 
                 recurrence_end_date: str = None, parent_quest_id: int = None,
                 recurrence_weekdays: str = None) -> int:
    """クエストを新規作成し、IDを返す"""
    if not title or not title.strip():
        raise ValueError("タイトルは必須です")
    if not creator or not creator.strip():
        raise ValueError("作成者は必須です")
    
    now = get_jst_now()
    return _execute_query("""
        INSERT INTO quests (title, description, priority, due_date, estimated_minutes, creator, 
                           recurrence_type, recurrence_end_date, parent_quest_id, recurrence_weekdays,
                           created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title.strip(), description, priority, due_date, estimated_minutes, creator.strip(),
          recurrence_type, recurrence_end_date, parent_quest_id, recurrence_weekdays, now, now), return_id=True)


def get_all_quests() -> list[dict]:
    """全クエストを取得"""
    return _fetch_all("SELECT * FROM quests ORDER BY priority DESC, created_at DESC")


def get_quest_by_id(quest_id: int) -> dict | None:
    """IDでクエストを取得"""
    return _fetch_one("SELECT * FROM quests WHERE id = ?", (quest_id,))


def get_quests_by_status(status: str) -> list[dict]:
    """ステータスでクエストをフィルタ"""
    return _fetch_all("SELECT * FROM quests WHERE status = ? ORDER BY priority DESC", (status,))


def update_quest(quest_id: int, **kwargs) -> bool:
    """クエストを更新 (可変フィールド対応)"""
    allowed_fields = {"title", "description", "status", "priority", "due_date", "assignee", "estimated_minutes", "recurrence_type", "recurrence_end_date", "recurrence_weekdays"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates["updated_at"] = get_jst_now()
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [quest_id]
    
    return _execute_query(f"UPDATE quests SET {set_clause} WHERE id = ?", tuple(values)) > 0


def assign_quest(quest_id: int, assignee: str) -> bool:
    """クエストに担当者を割り当て"""
    return update_quest(quest_id, assignee=assignee if assignee else None)


def change_status(quest_id: int, status: str) -> bool:
    """クエストのステータスを変更"""
    valid_statuses = {"Backlog", "In Progress", "Review", "Done"}
    if status not in valid_statuses:
        raise ValueError(f"無効なステータス: {status}")
    return update_quest(quest_id, status=status)


def delete_quest(quest_id: int) -> bool:
    """クエストを削除"""
    return _execute_query("DELETE FROM quests WHERE id = ?", (quest_id,)) > 0


# ========== コメント操作 ==========

def add_comment(quest_id: int, user: str, content: str, file_path: str = None, log_type: str = "user") -> int:
    """コメントを追加（log_type: 'user' or 'system'）"""
    if not content or not content.strip():
        raise ValueError("コメント内容は必須です")
    if not user or not user.strip():
        if log_type == "user":
            raise ValueError("ユーザー名は必須です")
    
    now = get_jst_now()
    # Postgresのuserは予約語のため、クエリでは "user" とするか、ここではプレースホルダで処理されるのでOKだが、
    # SELECT等のカラム名に注意が必要。INSERTは列挙しているので大丈夫か確認する。
    # SQLiteもPostgresも列名はダブルクォートで囲めば安全。
    
    query = """
        INSERT INTO comments (quest_id, "user", content, file_path, log_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    return _execute_query(query, (quest_id, user.strip(), content.strip(), file_path, log_type, now), return_id=True)


def get_comments(quest_id: int) -> list[dict]:
    """クエストのコメント一覧を取得"""
    return _fetch_all("SELECT * FROM comments WHERE quest_id = ? ORDER BY created_at ASC", (quest_id,))


def get_all_logs(limit: int = 100) -> list[dict]:
    """全操作ログを取得（クエスト情報付き）"""
    return _fetch_all("""
        SELECT c.*, q.title as quest_title
        FROM comments c
        LEFT JOIN quests q ON c.quest_id = q.id
        ORDER BY c.created_at DESC
        LIMIT ?
    """, (limit,))


# ========== リソース操作 ==========

def create_resource(title: str, url: str, category: str, tags: str, memo: str, created_by: str) -> int:
    """リソースを新規作成"""
    if not title or not title.strip():
        raise ValueError("タイトルは必須です")
    if not url or not url.strip():
        raise ValueError("URLは必須です")
    
    now = get_jst_now()
    return _execute_query("""
        INSERT INTO resources (title, url, category, tags, memo, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (title.strip(), url.strip(), category, tags, memo, created_by, now, now), return_id=True)


def get_all_resources() -> list[dict]:
    """全リソースを取得"""
    return _fetch_all("SELECT * FROM resources ORDER BY is_favorite DESC, view_count DESC, created_at DESC")


def get_resource_by_id(resource_id: int) -> dict | None:
    """IDでリソースを取得"""
    return _fetch_one("SELECT * FROM resources WHERE id = ?", (resource_id,))


def update_resource(resource_id: int, **kwargs) -> bool:
    """リソースを更新"""
    allowed_fields = {"title", "url", "category", "tags", "memo", "is_favorite"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates["updated_at"] = get_jst_now()
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [resource_id]
    
    return _execute_query(f"UPDATE resources SET {set_clause} WHERE id = ?", tuple(values)) > 0


def toggle_favorite(resource_id: int) -> bool:
    """お気に入りをトグル"""
    resource = get_resource_by_id(resource_id)
    if not resource:
        return False
    new_value = 0 if resource["is_favorite"] else 1
    return update_resource(resource_id, is_favorite=new_value)


def increment_view_count(resource_id: int) -> bool:
    """閲覧回数をインクリメント"""
    return _execute_query("""
        UPDATE resources 
        SET view_count = view_count + 1, last_viewed_at = ? 
        WHERE id = ?
    """, (get_jst_now(), resource_id)) > 0


def delete_resource(resource_id: int) -> bool:
    """リソースを削除"""
    return _execute_query("DELETE FROM resources WHERE id = ?", (resource_id,)) > 0


def get_resource_categories() -> list[str]:
    """カテゴリ一覧を取得"""
    rows = _fetch_all("SELECT DISTINCT category FROM resources ORDER BY category")
    return [row['category'] for row in rows]


def get_resource_tags() -> list[str]:
    """タグ一覧を取得"""
    rows = _fetch_all("SELECT tags FROM resources WHERE tags != ''")
    all_tags = set()
    for row in rows:
        tags_str = row['tags']
        if not tags_str:
            continue
        for tag in tags_str.split(","):
            tag = tag.strip()
            if tag:
                all_tags.add(tag)
    return sorted(all_tags)


# ========== テンプレート操作 ==========

def get_templates():
    """テンプレート一覧を取得"""
    return _fetch_all("SELECT * FROM quest_templates ORDER BY created_at DESC")


def create_template(title: str, description: str, priority: int, estimated_minutes: int) -> int:
    """テンプレートを新規作成"""
    now = get_jst_now()
    return _execute_query("""
        INSERT INTO quest_templates (title, description, priority, estimated_minutes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title.strip(), description, priority, estimated_minutes, now, now), return_id=True)


def update_template(template_id: int, title: str, description: str, priority: int, estimated_minutes: int):
    """テンプレートを更新"""
    now = get_jst_now()
    _execute_query("""
        UPDATE quest_templates
        SET title = ?, description = ?, priority = ?, estimated_minutes = ?, updated_at = ?
        WHERE id = ?
    """, (title.strip(), description, priority, estimated_minutes, now, template_id))


def delete_template(template_id: int):
    """テンプレートを削除"""
    _execute_query("DELETE FROM quest_templates WHERE id = ?", (template_id,))


# ========== 繰り返しクエスト操作 ==========

def process_recurring_quests():
    """完了した繰り返しクエストから次のクエストを自動生成"""
    from datetime import timedelta
    
    today = datetime.now(JST).date()
    
    # 完了済みで繰り返し設定があるクエストを取得
    recurring_quests = _fetch_all("""
        SELECT * FROM quests 
        WHERE status = 'Done' 
        AND recurrence_type != 'none' 
        AND recurrence_type IS NOT NULL
    """)
    
    for quest in recurring_quests:
        recurrence_type = quest.get("recurrence_type", "none")
        recurrence_end_date = quest.get("recurrence_end_date")
        recurrence_weekdays = quest.get("recurrence_weekdays")  # 曜日設定
        
        # 繰り返し終了日チェック
        if recurrence_end_date:
            try:
                end_date = datetime.strptime(recurrence_end_date, "%Y-%m-%d").date()
                if today > end_date:
                    continue  # 繰り返し終了
            except:
                pass
        
        # 次の期限日を計算
        next_due = None
        base_date = today  # デフォルトは今日
        
        if quest["due_date"]:
            try:
                base_date = datetime.strptime(quest["due_date"], "%Y-%m-%d").date()
            except:
                base_date = today
        
        if recurrence_type == "daily":
            next_due = base_date + timedelta(days=1)
            
        elif recurrence_type == "weekly":
            if recurrence_weekdays:
                # 曜日指定がある場合
                weekdays = [int(d.strip()) for d in recurrence_weekdays.split(",") if d.strip().isdigit()]
                if weekdays:
                    search_date = base_date + timedelta(days=1)
                    for _ in range(7):
                        if search_date.weekday() in weekdays:
                            next_due = search_date
                            break
                        search_date += timedelta(days=1)
                    if next_due is None:
                        next_due = base_date + timedelta(weeks=1)
                else:
                    next_due = base_date + timedelta(weeks=1)
            else:
                next_due = base_date + timedelta(weeks=1)
                
        elif recurrence_type == "monthly":
            month = base_date.month + 1
            year = base_date.year
            if month > 12:
                month = 1
                year += 1
            day = min(base_date.day, 28)
            next_due = base_date.replace(year=year, month=month, day=day)
        
        if next_due is None:
            continue
            
        # 繰り返し終了日より後の場合はスキップ
        if recurrence_end_date:
            try:
                end_date = datetime.strptime(recurrence_end_date, "%Y-%m-%d").date()
                if next_due > end_date:
                    update_quest(quest["id"], recurrence_type="none")
                    continue
            except:
                pass
        
        # 同じ親から既に生成されたクエストがあるかチェック
        parent_id = quest.get("parent_quest_id") or quest["id"]
        
        # クエリパラメータは文字列比較になるためisoformat
        count_query = "SELECT COUNT(*) as count FROM quests WHERE parent_quest_id = ? AND due_date = ?"
        count_res = _fetch_one(count_query, (parent_id, next_due.isoformat()))
        if count_res and count_res['count'] > 0:
            continue  # 既に生成済み
        
        # 新しいクエストを作成
        create_quest(
            title=quest["title"],
            description=quest["description"],
            priority=quest["priority"],
            due_date=next_due.isoformat(),
            creator=quest["creator"],
            estimated_minutes=quest.get("estimated_minutes", 30),
            recurrence_type=recurrence_type,
            recurrence_end_date=recurrence_end_date,
            parent_quest_id=parent_id,
            recurrence_weekdays=recurrence_weekdays
        )
        
        # 元のクエストの繰り返し設定を解除
        update_quest(quest["id"], recurrence_type="none")

def get_quests_with_recurrence() -> list[dict]:
    """繰り返し設定があるクエスト一覧を取得"""
    return _fetch_all("""
        SELECT * FROM quests 
        WHERE recurrence_type != 'none' 
        AND recurrence_type IS NOT NULL
        ORDER BY created_at DESC
    """)
