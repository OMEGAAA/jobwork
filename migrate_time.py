import sqlite3
import shutil
import os
from datetime import datetime

# 作業ディレクトリを明示的に指定（絶対パス）
TARGET_DIR = r"C:/Users/PC_User/OneDrive/デスクトップ/quest_board"
if os.path.exists(TARGET_DIR):
    try:
        os.chdir(TARGET_DIR)
        print(f"Changed working directory to: {os.getcwd()}")
    except Exception as e:
        print(f"Failed to change directory: {e}")
        exit(1)
else:
    print(f"Directory not found: {TARGET_DIR}")
    exit(1)

DB_NAME = "quest_board.db"
# バックアップファイル名（タイムスタンプ付き）
BACKUP_NAME = f"quest_board_backup_{int(datetime.now().timestamp())}.db"

def migrate():
    if not os.path.exists(DB_NAME):
        print(f"Database file '{DB_NAME}' not found in {os.getcwd()}")
        return

    # バックアップ作成
    try:
        shutil.copy(DB_NAME, BACKUP_NAME)
        print(f"Backup created: {BACKUP_NAME}")
    except Exception as e:
        print(f"Backup failed: {e}")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 変換対象
    targets = {
        "quests": ["created_at", "updated_at"],
        "comments": ["created_at"],
        "resources": ["created_at", "updated_at", "last_viewed_at"],
        "quest_templates": ["created_at", "updated_at"]
    }

    try:
        updated_count = 0
        for table, cols in targets.items():
            # テーブル存在確認
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                continue

            for col in cols:
                # カラム存在確認
                try:
                    cursor.execute(f"SELECT {col} FROM {table} LIMIT 1")
                except sqlite3.OperationalError:
                    continue

                print(f"Migrating {table}.{col}...")
                # UTC -> JST (+9 hours)
                # 既にJST(未来)になっているデータは除外できないが、
                # 今回の修正後に作られたデータ以外はUTCとみなす。
                sql = f"UPDATE {table} SET {col} = datetime({col}, '+9 hours') WHERE {col} IS NOT NULL"
                cursor.execute(sql)
                updated_count += 1
        
        conn.commit()
        print(f"Migration completed. Updated columns in {updated_count} text/tables.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
