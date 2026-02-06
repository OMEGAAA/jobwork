"""
db.py - SQLiteデータベース操作モジュール
クエストとコメントのCRUD操作を提供
"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager

DATABASE = "quest_board.db"


@contextmanager
def get_connection():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """データベースとテーブルを初期化"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # クエストテーブル
        cursor.execute("""
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
        """)
        
        # 既存テーブルに列がない場合は追加
        try:
            cursor.execute("ALTER TABLE quests ADD COLUMN estimated_minutes INTEGER DEFAULT 30")
        except sqlite3.OperationalError:
            pass  # 既に列が存在する
        
        # コメントテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quest_id INTEGER NOT NULL,
                user TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
            )
        """)

        # 既存コメントテーブルに列がない場合は追加
        try:
            cursor.execute("ALTER TABLE comments ADD COLUMN file_path TEXT")
        except sqlite3.OperationalError:
            pass

        # log_typeカラム追加（マイグレーション）
        try:
            cursor.execute("ALTER TABLE comments ADD COLUMN log_type TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass
        
        # リソース（リンク・資料）テーブル
        cursor.execute("""
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
        """)
        
        # テンプレートテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quest_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 3,
                estimated_minutes INTEGER DEFAULT 30,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()


# ========== クエスト操作 ==========

def create_quest(title: str, description: str, priority: int, due_date: str, creator: str, estimated_minutes: int = 30) -> int:
    """クエストを新規作成し、IDを返す"""
    if not title or not title.strip():
        raise ValueError("タイトルは必須です")
    if not creator or not creator.strip():
        raise ValueError("作成者は必須です")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quests (title, description, priority, due_date, estimated_minutes, creator)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title.strip(), description, priority, due_date, estimated_minutes, creator.strip()))
        conn.commit()
        return cursor.lastrowid


def get_all_quests() -> list[dict]:
    """全クエストを取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quests ORDER BY priority DESC, created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_quest_by_id(quest_id: int) -> dict | None:
    """IDでクエストを取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_quests_by_status(status: str) -> list[dict]:
    """ステータスでクエストをフィルタ"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quests WHERE status = ? ORDER BY priority DESC", (status,))
        return [dict(row) for row in cursor.fetchall()]


def update_quest(quest_id: int, **kwargs) -> bool:
    """クエストを更新 (可変フィールド対応)"""
    allowed_fields = {"title", "description", "status", "priority", "due_date", "assignee", "estimated_minutes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [quest_id]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE quests SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0


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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
        conn.commit()
        return cursor.rowcount > 0


# ========== コメント操作 ==========

def add_comment(quest_id: int, user: str, content: str, file_path: str = None, log_type: str = "user") -> int:
    """コメントを追加（log_type: 'user' or 'system'）"""
    if not content or not content.strip():
        raise ValueError("コメント内容は必須です")
    if not user or not user.strip():
        # システムログの場合はユーザー名がなくても良いが、一応 "System" 等が入る想定
        if log_type == "user":
            raise ValueError("ユーザー名は必須です")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comments (quest_id, user, content, file_path, log_type)
            VALUES (?, ?, ?, ?, ?)
        """, (quest_id, user.strip(), content.strip(), file_path, log_type))
        conn.commit()
        return cursor.lastrowid


def get_comments(quest_id: int) -> list[dict]:
    """クエストのコメント一覧を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM comments WHERE quest_id = ? ORDER BY created_at ASC
        """, (quest_id,))
        return [dict(row) for row in cursor.fetchall()]


# ========== リソース操作 ==========

def create_resource(title: str, url: str, category: str, tags: str, memo: str, created_by: str) -> int:
    """リソースを新規作成"""
    if not title or not title.strip():
        raise ValueError("タイトルは必須です")
    if not url or not url.strip():
        raise ValueError("URLは必須です")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resources (title, url, category, tags, memo, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title.strip(), url.strip(), category, tags, memo, created_by))
        conn.commit()
        return cursor.lastrowid


def get_all_resources() -> list[dict]:
    """全リソースを取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources ORDER BY is_favorite DESC, view_count DESC, created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_resource_by_id(resource_id: int) -> dict | None:
    """IDでリソースを取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_resource(resource_id: int, **kwargs) -> bool:
    """リソースを更新"""
    allowed_fields = {"title", "url", "category", "tags", "memo", "is_favorite"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [resource_id]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE resources SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0


def toggle_favorite(resource_id: int) -> bool:
    """お気に入りをトグル"""
    resource = get_resource_by_id(resource_id)
    if not resource:
        return False
    new_value = 0 if resource["is_favorite"] else 1
    return update_resource(resource_id, is_favorite=new_value)


def increment_view_count(resource_id: int) -> bool:
    """閲覧回数をインクリメント"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE resources 
            SET view_count = view_count + 1, last_viewed_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (resource_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_resource(resource_id: int) -> bool:
    """リソースを削除"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        conn.commit()
        return cursor.rowcount > 0


def get_resource_categories() -> list[str]:
    """カテゴリ一覧を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM resources ORDER BY category")
        return [row[0] for row in cursor.fetchall()]


def get_resource_tags() -> list[str]:
    """タグ一覧を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tags FROM resources WHERE tags != ''")
        all_tags = set()
        for row in cursor.fetchall():
            for tag in row[0].split(","):
                tag = tag.strip()
                if tag:
                    all_tags.add(tag)
        return sorted(all_tags)


# ========== テンプレート操作 ==========

def get_templates():
    """テンプレート一覧を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quest_templates ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def create_template(title: str, description: str, priority: int, estimated_minutes: int) -> int:
    """テンプレートを新規作成"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quest_templates (title, description, priority, estimated_minutes)
            VALUES (?, ?, ?, ?)
        """, (title.strip(), description, priority, estimated_minutes))
        conn.commit()
        return cursor.lastrowid


def update_template(template_id: int, title: str, description: str, priority: int, estimated_minutes: int):
    """テンプレートを更新"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE quest_templates
            SET title = ?, description = ?, priority = ?, estimated_minutes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (title.strip(), description, priority, estimated_minutes, template_id))
        conn.commit()


def delete_template(template_id: int):
    """テンプレートを削除"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM quest_templates WHERE id = ?", (template_id,))
        conn.commit()
