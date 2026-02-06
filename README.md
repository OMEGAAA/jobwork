# 🗡️ Quest Board

ゲームのクエスト受注のようにタスクを管理するWebアプリケーション

## 機能

- **簡易ログイン**: 表示名を入力するだけで利用開始
- **クエスト管理**: 作成、受注、ステータス更新、担当変更
- **カンバンボード**: Backlog / In Progress / Review / Done の4列表示
- **コメント機能**: 作業ログとして進捗を記録

## セットアップ

### 1. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. アプリケーションの起動

```bash
streamlit run app.py
```

ブラウザで <http://localhost:8501> が開きます。

## 使い方

1. サイドバーで「冒険者名」を入力
2. **クエストボード**: 全クエストをカンバン形式で確認
3. **クエスト作成**: 新しいタスクを発行
4. **クエスト詳細**: 受注・ステータス変更・コメント追加

## ファイル構成

```
quest_board/
├── app.py           # メインアプリケーション
├── db.py            # データベース操作
├── requirements.txt # 依存ライブラリ
├── README.md        # このファイル
└── quest_board.db   # SQLiteデータベース（自動生成）
```

## 技術スタック

- Python 3.10+
- Streamlit
- SQLite
