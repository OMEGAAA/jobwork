"""
db.py - SQLiteデータベース操作モジュール
クエストとコメントのCRUD操作を提供
"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from zoneinfo import ZoneInfo

# 日本時間のタイムゾーン
JST = ZoneInfo("Asia/Tokyo")


def get_jst_now() -> str:
    """日本時間の現在時刻をISO形式で返す"""
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

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
        
        # 繰り返し設定用カラム追加
        try:
            cursor.execute("ALTER TABLE quests ADD COLUMN recurrence_type TEXT DEFAULT 'none'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE quests ADD COLUMN recurrence_end_date TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE quests ADD COLUMN parent_quest_id INTEGER")
        except sqlite3.OperationalError:
            pass
        # 曜日選択用カラム（0=月曜〜6=日曜、カンマ区切りで保存。例: "0,2,4" = 月水金）
        try:
            cursor.execute("ALTER TABLE quests ADD COLUMN recurrence_weekdays TEXT")
        except sqlite3.OperationalError:
            pass
        
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quests (title, description, priority, due_date, estimated_minutes, creator, 
                               recurrence_type, recurrence_end_date, parent_quest_id, recurrence_weekdays,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title.strip(), description, priority, due_date, estimated_minutes, creator.strip(),
              recurrence_type, recurrence_end_date, parent_quest_id, recurrence_weekdays, now, now))
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
    allowed_fields = {"title", "description", "status", "priority", "due_date", "assignee", "estimated_minutes", "recurrence_type", "recurrence_end_date", "recurrence_weekdays"}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    updates["updated_at"] = get_jst_now()
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
    
    now = get_jst_now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comments (quest_id, user, content, file_path, log_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (quest_id, user.strip(), content.strip(), file_path, log_type, now))
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


def get_all_logs(limit: int = 100) -> list[dict]:
    """全操作ログを取得（クエスト情報付き）"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, q.title as quest_title
            FROM comments c
            LEFT JOIN quests q ON c.quest_id = q.id
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


# ========== リソース操作 ==========

def create_resource(title: str, url: str, category: str, tags: str, memo: str, created_by: str) -> int:
    """リソースを新規作成"""
    if not title or not title.strip():
        raise ValueError("タイトルは必須です")
    if not url or not url.strip():
        raise ValueError("URLは必須です")
    
    now = get_jst_now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO resources (title, url, category, tags, memo, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title.strip(), url.strip(), category, tags, memo, created_by, now, now))
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
    
    updates["updated_at"] = get_jst_now()
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
            SET view_count = view_count + 1, last_viewed_at = ? 
            WHERE id = ?
        """, (get_jst_now(), resource_id))
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
    now = get_jst_now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quest_templates (title, description, priority, estimated_minutes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title.strip(), description, priority, estimated_minutes, now, now))
        conn.commit()
        return cursor.lastrowid


def update_template(template_id: int, title: str, description: str, priority: int, estimated_minutes: int):
    """テンプレートを更新"""
    now = get_jst_now()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE quest_templates
            SET title = ?, description = ?, priority = ?, estimated_minutes = ?, updated_at = ?
            WHERE id = ?
        """, (title.strip(), description, priority, estimated_minutes, now, template_id))
        conn.commit()


def delete_template(template_id: int):
    """テンプレートを削除"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM quest_templates WHERE id = ?", (template_id,))
        conn.commit()


# ========== 繰り返しクエスト操作 ==========

def process_recurring_quests():
    """完了した繰り返しクエストから次のクエストを自動生成"""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    
    jst = ZoneInfo("Asia/Tokyo")
    today = datetime.now(jst).date()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        # 完了済みで繰り返し設定があるクエストを取得
        cursor.execute("""
            SELECT * FROM quests 
            WHERE status = 'Done' 
            AND recurrence_type != 'none' 
            AND recurrence_type IS NOT NULL
        """)
        recurring_quests = [dict(row) for row in cursor.fetchall()]
    
    for quest in recurring_quests:
        recurrence_type = quest.get("recurrence_type", "none")
        recurrence_end_date = quest.get("recurrence_end_date")
        recurrence_weekdays = quest.get("recurrence_weekdays")  # 曜日設定（例: "0,2,4" = 月水金）
        
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
                # 曜日指定がある場合、次の該当曜日を探す
                weekdays = [int(d.strip()) for d in recurrence_weekdays.split(",") if d.strip().isdigit()]
                if weekdays:
                    # 今日の翌日から次の該当曜日を探す
                    search_date = base_date + timedelta(days=1)
                    for _ in range(7):  # 最大7日間探索
                        if search_date.weekday() in weekdays:
                            next_due = search_date
                            break
                        search_date += timedelta(days=1)
                    if next_due is None:
                        next_due = base_date + timedelta(weeks=1)
                else:
                    next_due = base_date + timedelta(weeks=1)
            else:
                # 曜日指定がない場合は単純に1週間後
                next_due = base_date + timedelta(weeks=1)
                
        elif recurrence_type == "monthly":
            # 月を加算（簡易実装）
            month = base_date.month + 1
            year = base_date.year
            if month > 12:
                month = 1
                year += 1
            day = min(base_date.day, 28)  # 安全のため28日まで
            next_due = base_date.replace(year=year, month=month, day=day)
        
        if next_due is None:
            continue
            
        # 繰り返し終了日より後の場合はスキップ
        if recurrence_end_date:
            try:
                end_date = datetime.strptime(recurrence_end_date, "%Y-%m-%d").date()
                if next_due > end_date:
                    # 繰り返し設定を解除
                    update_quest(quest["id"], recurrence_type="none")
                    continue
            except:
                pass
        
        # 同じ親から既に生成されたクエストがあるかチェック
        parent_id = quest.get("parent_quest_id") or quest["id"]
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM quests 
                WHERE parent_quest_id = ? AND due_date = ?
            """, (parent_id, next_due.isoformat()))
            if cursor.fetchone()[0] > 0:
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
            recurrence_weekdays=recurrence_weekdays  # 曜日設定を引き継ぐ
        )
        
        # 元のクエストの繰り返し設定を解除（次回はコピー先から繰り返す）
        update_quest(quest["id"], recurrence_type="none")


def get_quests_with_recurrence() -> list[dict]:
    """繰り返し設定があるクエスト一覧を取得"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM quests 
            WHERE recurrence_type != 'none' 
            AND recurrence_type IS NOT NULL
            ORDER BY created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

