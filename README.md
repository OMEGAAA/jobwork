
# Quest Board 🗡️

RPG風のタスク管理アプリ「Quest Board」です。
チームでの共有利用に対応し、クラウドデータベース（Supabase）と連携可能です。

## 特徴

- 📋 カンバンボードでタスク管理
- 🎮 経験値とレベルアップシステム
- 📅 ガントチャート（工程表）表示
- ☁️ クラウドデータベース対応（チーム共有）

## チームでの利用方法（クラウド共有）

複数人で同じクエストボードを共有するには、Supabase（無料のクラウドデータベース）の設定が必要です。

### 1. Supabaseのセットアップ

1. [Supabase](https://supabase.com/) でプロジェクトを作成。
2. **Project Settings -> Database** から接続文字列（URI）をコピー。
   - Mode: `Transaction` 推奨
   - 形式: `postgres://postgres.[ref]:[password]...`

### 2. 環境変数の設定

#### ローカルで動かす場合

`.streamlit/secrets.toml` ファイルを作成し、以下を記述：

```toml
SUPABASE_URL = "あなたの接続URL"
```

#### Streamlit Cloudでデプロイする場合

Deploy時に **Advanced Settings -> Secrets** に同じ内容を設定してください。

※ `SUPABASE_URL` が設定されていない場合は、自動的にローカルのSQLite（自分専用）が使用されます。

## インストールと実行

```bash
pip install -r requirements.txt
streamlit run app.py
```
