"""
app.py - Streamlit クエストボード アプリケーション
ゲームのクエスト受注のようにタスクを可視化するWebアプリ
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime
import db
import os
import time

MAX_ACTIVE_QUESTS = 3  # 同時受注上限

def get_active_quest_count(username: str) -> int:
    """ユーザーが進行中のクエスト数を取得"""
    quests = db.get_all_quests()
    return len([q for q in quests if q["assignee"] == username and q["status"] == "In Progress"])

# ========== 初期化 ==========
db.init_db()

# ページ設定
st.set_page_config(
    page_title="🗡️ Quest Board",
    page_icon="🗡️",
    layout="wide"
)

# ========== カスタムCSS ==========
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Noto+Sans+JP:wght@400;700&display=swap');
    
    /* 全体のスタイル */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* サイドバー */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%);
        border-right: 2px solid #e94560;
    }
    
    [data-testid="stSidebar"] .stRadio label {
        color: #fff !important;
        font-family: 'Noto Sans JP', sans-serif;
    }
    
    /* メインヘッダー */
    h1, h2, h3 {
        font-family: 'Orbitron', 'Noto Sans JP', sans-serif !important;
        background: linear-gradient(90deg, #e94560, #ff6b6b, #ffd93d);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 30px rgba(233, 69, 96, 0.5);
    }
    
    /* カードスタイル */
    [data-testid="stExpander"], .stForm {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(233, 69, 96, 0.3) !important;
        border-radius: 15px !important;
        backdrop-filter: blur(10px);
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(135deg, #e94560 0%, #ff6b6b 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        font-family: 'Noto Sans JP', sans-serif !important;
        font-weight: bold !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(233, 69, 96, 0.4) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(233, 69, 96, 0.6) !important;
    }
    
    /* メトリクス */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif !important;
        font-size: 2rem !important;
        color: #ffd93d !important;
        text-shadow: 0 0 10px rgba(255, 217, 61, 0.5);
    }
    
    [data-testid="stMetricLabel"] {
        color: #a0a0a0 !important;
    }
    
    /* 入力フィールド */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(233, 69, 96, 0.5) !important;
        border-radius: 10px !important;
        color: #fff !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #e94560 !important;
        box-shadow: 0 0 10px rgba(233, 69, 96, 0.3) !important;
    }
    
    /* 成功・警告・情報メッセージ */
    .stSuccess {
        background: linear-gradient(135deg, rgba(0, 200, 83, 0.2), rgba(0, 200, 83, 0.1)) !important;
        border-left: 4px solid #00c853 !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, rgba(255, 152, 0, 0.2), rgba(255, 152, 0, 0.1)) !important;
        border-left: 4px solid #ff9800 !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(33, 150, 243, 0.2), rgba(33, 150, 243, 0.1)) !important;
        border-left: 4px solid #2196f3 !important;
    }
    
    /* コンテナ（カード） */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stContainer"]) {
        transition: transform 0.2s ease;
    }
    
    /* ディバイダー */
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, transparent, #e94560, transparent) !important;
    }
    
    /* スライダー */
    
    .stSlider [data-testid="stTickBarMin"], .stSlider [data-testid="stTickBarMax"] {
        color: #000 !important;
    }
    
    .stSlider [data-testid="stThumbValue"] {
        color: #000 !important;
        font-weight: bold !important;
    }
    
    /* キャプション */
    .stCaption {
        color: #888 !important;
    }
    
    /* アニメーション付きタイトル */
    @keyframes glow {
        0%, 100% { text-shadow: 0 0 20px rgba(233, 69, 96, 0.5); }
        50% { text-shadow: 0 0 40px rgba(233, 69, 96, 0.8), 0 0 60px rgba(255, 107, 107, 0.4); }
    }
    
    h1 {
        animation: glow 3s ease-in-out infinite;
    }
</style>
""", unsafe_allow_html=True)

# ========== ヘルパー関数 ==========
def priority_badge(priority: int) -> str:
    """優先度をバッジ表示用の文字列に変換"""
    stars = "⭐" * priority
    return f"{stars} ({priority})"

def status_label(status: str) -> str:
    """ステータスを日本語に変換"""
    labels = {
        "Backlog": "未着手",
        "In Progress": "進行中",
        "Review": "レビュー中",
        "Done": "完了"
    }
    return labels.get(status, status)


def calc_exp(priority: int, estimated_minutes: int = 30) -> int:
    """優先度と推定時間からEXPを計算"""
    base_exp = priority * 20  # 優先度1=20, 5=100
    time_bonus = estimated_minutes // 10  # 10分ごとに+1
    return base_exp + time_bonus

def get_user_exp(username: str) -> int:
    """ユーザーの累計EXPを計算"""
    all_quests = db.get_all_quests()
    total_exp = 0
    for q in all_quests:
        if q["status"] == "Done" and q["assignee"] == username:
            total_exp += calc_exp(q["priority"], q.get("estimated_minutes", 30))
    return total_exp

def show_exp_gain(exp: int):
    """経験値獲得演出を表示"""
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #ffd93d 0%, #ff6b6b 100%);
        border-radius: 15px;
        animation: pulse 0.5s ease-in-out;
        margin: 10px 0;
    ">
        <div style="font-size: 3rem; margin-bottom: 10px;">🌟</div>
        <div style="font-size: 2rem; font-weight: bold; color: #1a1a2e;">+{exp} EXP</div>
        <div style="color: #1a1a2e;">クエスト完了！</div>
    </div>
    <style>
        @keyframes pulse {{
            0% {{ transform: scale(0.8); opacity: 0; }}
            50% {{ transform: scale(1.1); }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}
    </style>
    """, unsafe_allow_html=True)
    st.balloons()

def status_color(status: str) -> str:
    """ステータスに応じた色を返す"""
    colors = {
        "Backlog": "gray",
        "In Progress": "blue",
        "Review": "orange",
        "Done": "green"
    }
    return colors.get(status, "gray")

def show_stamp_animation():
    """受注時のスタンプアニメーション"""
    st.markdown("""
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-15deg);
        border: 5px solid #d32f2f;
        color: #d32f2f;
        font-size: 5rem;
        font-weight: bold;
        padding: 10px 40px;
        text-transform: uppercase;
        letter-spacing: 5px;
        border-radius: 10px;
        opacity: 0;
        animation: stamp 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.9);
        box-shadow: 0 0 0 3px #d32f2f inset;
    ">
        ACCEPTED
    </div>
    <style>
        @keyframes stamp {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(3) rotate(-15deg); }
            100% { opacity: 1; transform: translate(-50%, -50%) scale(1) rotate(-15deg); }
        }
    </style>
    """, unsafe_allow_html=True)

def show_delete_stamp_animation():
    """削除時のスタンプアニメーション"""
    st.markdown("""
    <div style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-15deg);
        border: 5px solid #1565c0;
        color: #1565c0;
        font-size: 5rem;
        font-weight: bold;
        padding: 10px 40px;
        letter-spacing: 5px;
        border-radius: 10px;
        opacity: 0;
        animation: stamp 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.9);
        box-shadow: 0 0 0 3px #1565c0 inset;
    ">
        削除
    </div>
    <style>
        @keyframes stamp {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(3) rotate(-15deg); }
            100% { opacity: 1; transform: translate(-50%, -50%) scale(1) rotate(-15deg); }
        }
    </style>
    """, unsafe_allow_html=True)

def render_quest_card(quest: dict, show_actions: bool = False):
    """クエストカードを描画"""
    is_mine = quest["assignee"] == st.session_state.get("username", "")
    recurrence_type = quest.get("recurrence_type", "none")
    
    with st.container(border=True):
        # タイトルと優先度
        col1, col2 = st.columns([3, 1])
        with col1:
            title = f"🎯 {quest['title']}"
            if recurrence_type and recurrence_type != "none":
                title += " 🔄"
            if is_mine:
                title += " 👤"
            st.markdown(f"**{title}**")
        with col2:
            st.caption(priority_badge(quest["priority"]))
        
        # 担当者と期限
        assignee = quest["assignee"] or "未割当"
        due = quest["due_date"] or "期限なし"
        info_line = f"👤 {assignee} | 📅 {due}"
        if recurrence_type and recurrence_type != "none":
            rec_labels = {"daily": "毎日", "weekly": "毎週", "monthly": "毎月"}
            info_line += f" | 🔄 {rec_labels.get(recurrence_type, recurrence_type)}"
        st.caption(info_line)
        
        if show_actions:
            cols = st.columns(2)
            with cols[0]:
                if st.button("詳細", key=f"detail_{quest['id']}", use_container_width=True):
                    st.session_state.selected_quest_id = quest["id"]
                    st.session_state.current_page = "📜 詳細"
                    st.rerun()
            
            with cols[1]:
                # 未着手の場合は受注ボタンを表示
                if quest["status"] == "Backlog":
                    if st.button("✋ 受注", key=f"accept_{quest['id']}", use_container_width=True):
                        # 上限チェック
                        current_active = get_active_quest_count(st.session_state.username)
                        if current_active >= MAX_ACTIVE_QUESTS:
                            st.error(f"同時受注上限（{MAX_ACTIVE_QUESTS}件）に達しています")
                        else:
                            db.assign_quest(quest["id"], st.session_state.username)
                            db.change_status(quest["id"], "In Progress")
                            # システムログ記録
                            db.add_comment(quest["id"], "System", "クエストを受注しました", log_type="system")
                            show_stamp_animation()
                            import time
                            time.sleep(1.5)  # アニメーションを見せるため少し待機
                            st.rerun()
                
                # 進行中の場合は完了ボタンを表示
                elif quest["status"] == "In Progress" and is_mine:
                    if st.button("✅ 完了", key=f"complete_{quest['id']}", use_container_width=True):
                        db.change_status(quest["id"], "Done")
                        # システムログ記録
                        db.add_comment(quest["id"], "System", "クエストを完了しました", log_type="system")
                        # 繰り返しクエストの処理
                        db.process_recurring_quests()
                        # EXP計算と演出
                        exp = calc_exp(quest["priority"], quest.get("estimated_minutes", 30))
                        show_exp_gain(exp)
                        import time
                        time.sleep(2.0)
                        st.rerun()

# セッション状態の初期化
if "username" not in st.session_state:
    st.session_state.username = ""
if "selected_quest_id" not in st.session_state:
    st.session_state.selected_quest_id = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "📋 ボード"


# ========== サイドバー ==========
with st.sidebar:
    st.title("🗡️ Quest Board")
    st.divider()
    
    # ユーザー名入力
    username = st.text_input("冒険者名を入力", value=st.session_state.username, placeholder="あなたの名前")
    if username:
        st.session_state.username = username
        st.success(f"ようこそ、**{username}** さん！")
        
        # 累計EXP表示（ユーザー名入力後のみ）
        total_exp = get_user_exp(username)
        level = total_exp // 100 + 1  # 100EXPごとにレベルアップ
        next_level_exp = level * 100
        progress = (total_exp % 100) / 100
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1a1a3e, #0f0f23); padding: 10px; border-radius: 10px; margin-top: 10px;">
            <div style="color: #ffd93d; font-weight: bold;">⚔️ Lv.{level}</div>
            <div style="color: #fff; font-size: 0.9rem;">EXP: {total_exp} / {next_level_exp}</div>
            <div style="background: #333; border-radius: 5px; height: 8px; margin-top: 5px;">
                <div style="background: linear-gradient(90deg, #e94560, #ffd93d); width: {progress*100}%; height: 100%; border-radius: 5px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("冒険者名を入力してください")
    
    st.divider()
    
    # レビュー待ち通知
    review_quests = [q for q in db.get_all_quests() if q["status"] == "Review"]
    if review_quests:
        st.error(f"🔥 レビュー待ち: {len(review_quests)}件")
        with st.expander("確認する", expanded=False):
            for q in review_quests:
                if st.button(f"#{q['id']} {q['title']}", key=f"rev_{q['id']}"):
                    st.session_state.selected_quest_id = q["id"]
                    st.session_state.current_page = "📜 詳細"
                    st.rerun()

    # ページ選択
    # (旧設定の上書き)
    menu_options = ["📋 ボード", "📃 一覧", "📅 工程表", "✨ 作成", "📜 詳細", "📊 ダッシュボード", "📚 リソース"]
    _old_options_placeholder = """
    menu_options = ["📋 ボード", "📃 一覧", "📅 工程表", "✨ 作成", "📜 詳細", "� ログ", "�📊 ダッシュボード", "📚 リソース"]
    """
    # ボタン実装に切り替え
    st.markdown("""
        <style>
        div[data-testid="stSidebar"] button p {
            user-select: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.caption("メニュー")
    
    for option in menu_options:
        btn_type = "primary" if st.session_state.current_page == option else "secondary"
        if st.button(option, key=f"menu_{option}", type=btn_type, use_container_width=True):
            st.session_state.current_page = option
            st.rerun()
            
    page = st.session_state.current_page
    
    st.divider()
    if st.button("🔄 最新情報に更新", use_container_width=True):
        st.rerun()

# ユーザー名未入力時はブロック
if not st.session_state.username:
    st.info("👈 サイドバーから冒険者名を入力してください")
    st.stop()

# ========== ページ: クエストボード ==========
if page == "📋 ボード":
    st.header("📋 ボード")
    
    # フィルター
    col1, col2 = st.columns(2)
    with col1:
        filter_status = st.multiselect(
            "ステータスでフィルター",
            ["Backlog", "In Progress", "Review", "Done"],
            default=["Backlog", "In Progress", "Review"],
            format_func=status_label
        )
    with col2:
        filter_assignee = st.selectbox(
            "担当者でフィルター",
            ["全員", "自分のみ", "未割当のみ"]
        )
    
    # クエスト取得
    all_quests = db.get_all_quests()
    
    # フィルター適用
    filtered_quests = [q for q in all_quests if q["status"] in filter_status]
    if filter_assignee == "自分のみ":
        filtered_quests = [q for q in filtered_quests if q["assignee"] == st.session_state.username]
    elif filter_assignee == "未割当のみ":
        filtered_quests = [q for q in filtered_quests if not q["assignee"]]
    
    st.divider()
    
    # カンバン表示
    statuses = ["Backlog", "In Progress", "Review", "Done"]
    cols = st.columns(4)
    
    for i, status in enumerate(statuses):
        with cols[i]:
            st.subheader(f":{status_color(status)}[{status_label(status)}]")
            status_quests = [q for q in filtered_quests if q["status"] == status]
            
            if not status_quests:
                st.caption("クエストなし")
            else:
                for quest in status_quests:
                    render_quest_card(quest, show_actions=True)

# ========== ページ: クエスト一覧 ==========
elif page == "📃 一覧":
    st.header("📃 一覧")
    
    # フィルタオプション
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_status = st.multiselect(
            "ステータス",
            ["Backlog", "In Progress", "Review", "Done"],
            default=["Backlog", "In Progress", "Review"],
            format_func=status_label
        )
    
    with col2:
        filter_priority = st.multiselect(
            "優先度",
            [1, 2, 3, 4, 5],
            default=[1, 2, 3, 4, 5],
            format_func=lambda x: f"{'⭐' * x}"
        )
    
    with col3:
        filter_assignee = st.text_input("担当者で検索", placeholder="名前を入力...")
    
    with col4:
        sort_by = st.selectbox(
            "並び替え",
            ["優先度（高い順）", "優先度（低い順）", "期限（近い順）", "作成日（新しい順）", "作成日（古い順）"]
        )
    
    # クエスト取得
    all_quests = db.get_all_quests()
    
    # フィルタ適用
    filtered = [q for q in all_quests if q["status"] in filter_status]
    filtered = [q for q in filtered if q["priority"] in filter_priority]
    if filter_assignee:
        filtered = [q for q in filtered if filter_assignee.lower() in (q["assignee"] or "").lower()]
    
    # ソート
    if sort_by == "優先度（高い順）":
        filtered.sort(key=lambda x: x["priority"], reverse=True)
    elif sort_by == "優先度（低い順）":
        filtered.sort(key=lambda x: x["priority"])
    elif sort_by == "期限（近い順）":
        filtered.sort(key=lambda x: x["due_date"] or "9999-99-99")
    elif sort_by == "作成日（新しい順）":
        filtered.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_by == "作成日（古い順）":
        filtered.sort(key=lambda x: x["created_at"])
    
    st.divider()
    st.caption(f"📊 {len(filtered)}件のクエスト")
    
    # テーブル形式で表示
    if not filtered:
        st.info("条件に一致するクエストがありません")
    else:
        for quest in filtered:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**🎯 {quest['title']}**")

                
                with col2:
                    st.caption("優先度")
                    st.write(priority_badge(quest["priority"]))
                
                with col3:
                    st.caption("ステータス")
                    st.write(status_label(quest["status"]))
                
                with col4:
                    st.caption("担当者")
                    st.write(quest["assignee"] or "未割当")
                
                with col5:
                    if st.button("詳細", key=f"list_detail_{quest['id']}", use_container_width=True):
                        st.session_state.selected_quest_id = quest["id"]
                        st.session_state.current_page = "📜 詳細"
                        st.rerun()

# ========== ページ: 工程表 ==========
# ========== ページ: 工程表 ==========
# ========== ページ: 工程表 ==========
elif page == "📅 工程表":
    st.header("📅 クエスト工程表")
    
    # コントロール
    base_date = st.date_input("基準日", value=date.today())
    
    all_quests = db.get_all_quests()
    from datetime import datetime, timedelta
    
    # データを整形
    tasks_data = []
    
    for q in all_quests:
        # 開始日時
        try:
            created_str = q.get("created_at", "")
            if created_str:
                start_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S")
            else:
                start_dt = datetime.now()
        except:
            start_dt = datetime.now()
            
        # 終了日時
        due_date_obj = None
        if q["due_date"]: # 期限あり
            try:
                due_dt = datetime.strptime(q["due_date"], "%Y-%m-%d")
                due_date_obj = due_dt.date()
                # 期限の日の終わり(23:59:59)まで有効とする
                grid_end_dt = due_dt + timedelta(days=1) - timedelta(seconds=1)
            except:
                grid_end_dt = start_dt # エラー時は開始と同じ
        else:
            # 期限なしの場合は開始日時と同じ（点として表示されるか、表示されない）
             grid_end_dt = start_dt

        tasks_data.append({
            "id": q["id"],
            "title": q["title"],
            "assignee": q["assignee"] or "未割当",
            "status": q.get("status", "Backlog"),
            "start_dt": start_dt,
            "end_dt": grid_end_dt,
            "due_date": due_date_obj
        })

    if not tasks_data:
        st.info("データがありません")
    else:
        # グリッドの構築（30日分）
        date_cols = [base_date + timedelta(days=i) for i in range(30)]
        col_labels = [d.strftime('%m/%d') for d in date_cols]

        # データフレーム用のデータ作成
        df_index = []
        df_data = []
        
        for t in tasks_data:
            t_start = t["start_dt"]
            t_end = t["end_dt"]
            
            # グリッド期間
            g_start = datetime.combine(date_cols[0], datetime.min.time())
            g_end = datetime.combine(date_cols[-1], datetime.max.time())

            # 表示範囲判定
            if (t_start <= g_end) and (t_end >= g_start):
                # Indexに期限日(due_date)も含める
                df_index.append((t["title"], t["assignee"], t["status"], t["start_dt"], t["end_dt"], t["due_date"]))
                df_data.append(["" for _ in col_labels])

        if not df_data:
            st.warning("この期間に表示するタスクはありません")
        else:
            # IndexにIDを含める
            secure_index = pd.MultiIndex.from_tuples([(x[0], x[1], i) for i, x in enumerate(df_index)], names=["クエスト", "担当者", "id"])
            df_secure = pd.DataFrame(df_data, columns=col_labels, index=secure_index)
            
            # メタデータリスト（行番号でアクセス）
            metadata = df_index 
            
            def apply_style(row):
                idx = row.name[2]
                meta = metadata[idx] # (title, assignee, status, start, end, due_date)
                status = meta[2]
                start = meta[3]
                end = meta[4]
                due_date = meta[5]
                
                bg_color = {
                    "Backlog": "#e0e0e0", "In Progress": "#64b5f6", 
                    "Review": "#ffb74d", "Done": "#81c784"
                }.get(status, "#ffffff")
                
                styles = []
                for i, _ in enumerate(row.index):
                    grid_point = date_cols[i]
                    
                    # 期間内 (Active) か判定
                    is_active = False
                    g_date = grid_point
                    if start.date() <= g_date <= end.date():
                        is_active = True
                    
                    # 期限日 (Due) か判定
                    is_due = False
                    if due_date and grid_point == due_date:
                        is_due = True

                    # スタイル適用
                    style_str = ""
                    if is_active:
                         style_str += f'background-color: {bg_color}; '
                    
                    if is_due:
                         style_str += 'border: 2px solid #ff1744 !important; '
                    
                    styles.append(style_str)
                    
                return styles

            st.dataframe(df_secure.style.apply(apply_style, axis=1), use_container_width=True, height=500)
            st.caption("凡例: ⬜未着手 🟦進行中 🟧レビュー 🟩完了")

# ========== ページ: クエスト作成 ==========
elif page == "✨ 作成":
    st.header("✨ 新規クエスト作成")
    
    # テンプレート読み込み機能
    templates = db.get_templates()
    
    # セッションステート初期化（フォーム用）
    if "form_title" not in st.session_state: st.session_state.form_title = ""
    if "form_desc" not in st.session_state: st.session_state.form_desc = ""
    if "form_prio" not in st.session_state: st.session_state.form_prio = 3
    if "form_est" not in st.session_state: st.session_state.form_est = 30
    
    if templates:
        tpl_options = {t['title']: t for t in templates}
        c_tpl1, c_tpl2 = st.columns([3, 1])
        with c_tpl1:
            selected_tpl_name = st.selectbox("テンプレートから読み込む", ["(選択なし)"] + list(tpl_options.keys()))
        with c_tpl2:
            st.write("") # スペース調整
            st.write("")
            if selected_tpl_name != "(選択なし)" and st.button("↓ 適用", use_container_width=True):
                tpl = tpl_options[selected_tpl_name]
                st.session_state.form_title = tpl['title']
                st.session_state.form_desc = tpl['description']
                st.session_state.form_prio = tpl['priority']
                st.session_state.form_est = tpl['estimated_minutes']
                st.success(f"テンプレート「{tpl['title']}」を適用しました")
    
    with st.form("create_quest_form"):
        # value引数にsession_stateの値を設定
        title = st.text_input("クエスト名 *", value=st.session_state.form_title, placeholder="例: バグを倒せ！")
        description = st.text_area("詳細説明", value=st.session_state.form_desc, placeholder="クエストの詳細を記入...")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            priority = st.slider("優先度", 1, 5, value=st.session_state.form_prio)
        with col2:
            due_date = st.date_input("期限", value=None, min_value=date.today())
        with col3:
            estimated_minutes = st.number_input("推定時間（分）", min_value=5, max_value=480, value=st.session_state.form_est, step=5)
        
        # 繰り返し設定セクション
        st.markdown("---")
        st.markdown("**🔄 繰り返し設定**")
        rec_col1, rec_col2 = st.columns(2)
        with rec_col1:
            recurrence_options = {
                "none": "繰り返しなし",
                "daily": "毎日",
                "weekly": "毎週",
                "monthly": "毎月"
            }
            recurrence_type = st.selectbox(
                "繰り返し頻度",
                options=list(recurrence_options.keys()),
                format_func=lambda x: recurrence_options[x]
            )
        with rec_col2:
            recurrence_end_date = st.date_input(
                "繰り返し終了日（任意）",
                value=None,
                min_value=date.today(),
                help="この日を過ぎると繰り返しが終了します"
            )
        
        # 毎週の場合は曜日選択を表示
        selected_weekdays = []
        if recurrence_type == "weekly":
            st.markdown("**📅 繰り返す曜日を選択**")
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
            weekday_cols = st.columns(7)
            for i, (col, name) in enumerate(zip(weekday_cols, weekday_names)):
                with col:
                    if st.checkbox(name, key=f"weekday_{i}"):
                        selected_weekdays.append(i)
            if not selected_weekdays:
                st.warning("⚠️ 少なくとも1つの曜日を選択してください")
        
        if recurrence_type != "none":
            st.info("💡 クエストを完了すると、次の期限日で自動的に新しいクエストが作成されます")
        
        submitted = st.form_submit_button("🎉 クエストを発行", use_container_width=True)
        
        if submitted:
            if not title.strip():
                st.error("クエスト名は必須です")
            elif recurrence_type == "weekly" and not selected_weekdays:
                st.error("毎週繰り返しの場合、少なくとも1つの曜日を選択してください")
            else:
                try:
                    due_str = due_date.isoformat() if due_date else None
                    rec_end_str = recurrence_end_date.isoformat() if recurrence_end_date else None
                    # 曜日をカンマ区切りの文字列に変換
                    weekdays_str = ",".join(str(d) for d in selected_weekdays) if selected_weekdays else None
                    quest_id = db.create_quest(
                        title=title,
                        description=description,
                        priority=priority,
                        due_date=due_str,
                        estimated_minutes=estimated_minutes,
                        creator=st.session_state.username,
                        recurrence_type=recurrence_type,
                        recurrence_end_date=rec_end_str,
                        recurrence_weekdays=weekdays_str
                    )
                    if recurrence_type != "none":
                        st.success(f"🔄 繰り返しクエスト「{title}」を発行しました！ (ID: {quest_id})")
                    else:
                        st.success(f"クエスト「{title}」を発行しました！ (ID: {quest_id})")
                    st.balloons()
                    # フォームをクリア
                    st.session_state.form_title = ""
                    st.session_state.form_desc = ""
                    st.session_state.form_prio = 3
                    st.session_state.form_est = 30
                except Exception as e:
                    st.error(f"エラー: {e}")

    # テンプレート管理セクション
    st.divider()
    st.subheader("📝 テンプレート管理")
    
    with st.expander("新規テンプレートを登録", expanded=False):
        with st.form("create_template_form"):
            t_title = st.text_input("テンプレート名 (クエスト名)", placeholder="例: 定例ミーティング")
            t_desc = st.text_area("詳細説明", placeholder="テンプレートの説明...")
            c1, c2 = st.columns(2)
            with c1:
                t_prio = st.slider("優先度", 1, 5, 3, key="tpl_create_prio")
            with c2:
                t_est = st.number_input("推定時間（分）", min_value=5, max_value=480, value=30, step=5, key="tpl_create_est")
            
            if st.form_submit_button("登録"):
                if t_title:
                    db.create_template(t_title, t_desc, t_prio, t_est)
                    st.success("テンプレートを登録しました")
                    st.rerun()
                else:
                    st.error("テンプレート名は必須です")
    
    if templates:
        st.caption("登録済みテンプレート (編集・削除)")
        for tpl in templates:
            with st.expander(f"📑 {tpl['title']}"):
                with st.form(f"edit_template_{tpl['id']}"):
                    et_title = st.text_input("タイトル", value=tpl['title'])
                    et_desc = st.text_area("説明", value=tpl['description'])
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        et_prio = st.slider("優先度", 1, 5, value=tpl['priority'], key=f"tpl_prio_{tpl['id']}")
                    with ec2:
                        et_est = st.number_input("推定時間", min_value=5, max_value=480, value=tpl['estimated_minutes'], step=5, key=f"tpl_est_{tpl['id']}")
                    
                    if st.form_submit_button("更新"):
                        db.update_template(tpl['id'], et_title, et_desc, et_prio, et_est)
                        st.success("更新しました")
                        st.rerun()
                
                if st.button("🗑️ 削除", key=f"del_tpl_{tpl['id']}"):
                    db.delete_template(tpl['id'])
                    st.success("テンプレートを削除しました")
                    st.rerun()

# ========== ページ: クエスト詳細 ==========
elif page == "📜 詳細":
    st.header("📜 クエスト詳細・管理")
    
    # クエスト選択
    all_quests = db.get_all_quests()
    if not all_quests:
        st.info("クエストがありません。新規作成してください。")
        st.stop()
    
    # フィルタ切り替え
    show_done = st.checkbox("✅ 完了済みのクエストも表示する", value=False)
    
    if show_done:
        filtered_quests = all_quests
    else:
        filtered_quests = [q for q in all_quests if q["status"] != "Done"]
        # 選択中のIDが完了済みの場合の救済（リストから消えないようにする）
        if st.session_state.selected_quest_id:
            current = next((q for q in all_quests if q["id"] == st.session_state.selected_quest_id), None)
            if current and current["status"] == "Done":
                # ただし、これを入れると「未完了のみ」の意味が薄れるが、UX的には親切
                # ここではシンプルに「未完了のみ」モードなら容赦なく消す（選択解除される）挙動でいくか、
                # あるいは強制追加するか。
                # ユーザー体験を優先し、強制追加はせず、リストになければindex=0になる挙動に任せる。
                pass

    if not filtered_quests:
        if not show_done:
            st.warning("未完了のクエストはありません。完了済みを表示してください。")
        else:
            st.info("クエストがありません")
        # クエストがない場合はここで停止（ただしチェックボックスは表示済み）
        if not filtered_quests:
             st.stop()

    quest_options = {f"#{q['id']} {q['title']}": q["id"] for q in filtered_quests}
    
    # セッションから選択されたクエストがあれば使用
    default_index = 0
    if st.session_state.selected_quest_id:
        # optionsに含まれているか確認
        current_ids = [q["id"] for q in filtered_quests]
        if st.session_state.selected_quest_id in current_ids:
            # keyのリストからインデックスを探す
            option_keys = list(quest_options.keys())
            for i, key in enumerate(option_keys):
                if quest_options[key] == st.session_state.selected_quest_id:
                    default_index = i
                    break
    
    selected_label = st.selectbox(
        "クエストを選択",
        list(quest_options.keys()),
        index=default_index
    )
    quest_id = quest_options[selected_label]
    quest = db.get_quest_by_id(quest_id)
    
    if quest:
        st.divider()
        
        # クエスト情報表示
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"🎯 {quest['title']}")
            st.markdown(quest["description"] or "*説明なし*")
            
            st.caption(f"作成者: {quest['creator']} | 作成日: {quest['created_at']}")
            st.caption(f"最終更新: {quest['updated_at']}")
        
        with col2:
            st.metric("優先度", priority_badge(quest["priority"]))
            st.metric("ステータス", status_label(quest["status"]))
            st.metric("担当者", quest["assignee"] or "未割当")
            
            # 期限と残り時間
            due_display = quest["due_date"] or "なし"
            st.metric("期限", due_display)
            
            estimated = quest.get("estimated_minutes", 30)
            st.metric("推定時間", f"{estimated}分")
            
            # 繰り返し設定の表示
            recurrence_type = quest.get("recurrence_type", "none")
            if recurrence_type and recurrence_type != "none":
                rec_labels = {"daily": "毎日", "weekly": "毎週", "monthly": "毎月"}
                rec_display = rec_labels.get(recurrence_type, recurrence_type)
                
                # 曜日設定がある場合は表示
                recurrence_weekdays = quest.get("recurrence_weekdays")
                if recurrence_type == "weekly" and recurrence_weekdays:
                    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
                    weekdays = [int(d.strip()) for d in recurrence_weekdays.split(",") if d.strip().isdigit()]
                    weekday_str = "・".join([weekday_names[d] for d in weekdays if 0 <= d <= 6])
                    rec_display = f"毎週（{weekday_str}）"
                
                st.metric("🔄 繰り返し", rec_display)
                
                # 繰り返し終了日
                recurrence_end_date = quest.get("recurrence_end_date")
                if recurrence_end_date:
                    st.caption(f"繰り返し終了: {recurrence_end_date}")
        
        st.divider()
        
        # 操作パネル
        st.subheader("⚔️ アクション")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🙋 このクエストを受注", use_container_width=True):
                # 上限チェック
                current_active = get_active_quest_count(st.session_state.username)
                if current_active >= MAX_ACTIVE_QUESTS:
                    st.error(f"同時受注上限（{MAX_ACTIVE_QUESTS}件）に達しています")
                else:
                    db.assign_quest(quest_id, st.session_state.username)
                    db.change_status(quest_id, "In Progress")
                    db.add_comment(quest_id, "System", "詳細ページからクエストを受注しました", log_type="system")
                    st.success("クエストを受注しました！")
                    st.rerun()
        
        with col2:
            statuses = ["Backlog", "In Progress", "Review", "Done"]
            new_status = st.selectbox(
                "ステータス変更",
                statuses,
                index=statuses.index(quest["status"]),
                format_func=status_label
            )
            if st.button("ステータス更新", use_container_width=True):
                old_status = quest["status"]
                if new_status != old_status:
                    db.change_status(quest_id, new_status)
                    db.add_comment(quest_id, "System", f"ステータスを「{status_label(old_status)}」から「{status_label(new_status)}」に変更しました", log_type="system")
                    st.success(f"ステータスを「{status_label(new_status)}」に変更しました")
                    # 完了時にEXP獲得演出
                    if new_status == "Done" and old_status != "Done":
                        exp = calc_exp(quest["priority"], quest.get("estimated_minutes", 30))
                        show_exp_gain(exp)
                    else:
                        st.rerun()
        
        with col3:
            new_assignee = st.text_input("担当者変更", value=quest["assignee"] or "")
            if st.button("担当者更新", use_container_width=True):
                old_assignee = quest["assignee"] or "未割当"
                if new_assignee != old_assignee:
                    db.assign_quest(quest_id, new_assignee)
                    db.add_comment(quest_id, "System", f"担当者を「{old_assignee}」から「{new_assignee}」に変更しました", log_type="system")
                    st.success("担当者を更新しました")
                    st.rerun()
        
        # 詳細情報の編集
        with st.expander("📝 クエスト情報を編集", expanded=False):
            with st.form("edit_quest_form"):
                new_title = st.text_input("タイトル", value=quest["title"])
                new_desc = st.text_area("説明", value=quest["description"] or "")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    # 日付変換
                    default_date = None
                    if quest["due_date"]:
                        try:
                            default_date = datetime.strptime(quest["due_date"], "%Y-%m-%d").date()
                        except:
                            pass
                    new_due = st.date_input("期限", value=default_date)
                
                with c2:
                    new_prio = st.slider("優先度", 1, 5, quest["priority"])
                
                with c3:
                    new_mins = st.number_input("推定時間(分)", min_value=15, step=15, value=quest.get("estimated_minutes", 30))

                if st.form_submit_button("💾 更新保存"):
                     due_str = new_due.strftime("%Y-%m-%d") if new_due else None
                     # タイトルチェック
                     if not new_title.strip():
                         st.error("タイトルは必須です")
                     else:
                         db.update_quest(
                             quest_id, 
                             title=new_title, 
                             description=new_desc, 
                             due_date=due_str, 
                             priority=new_prio, 
                             estimated_minutes=new_mins
                         )
                         db.add_comment(quest_id, "System", "クエスト情報を更新しました", log_type="system")
                         st.success("クエスト情報を更新しました")
                         st.rerun()
        
        # 削除ボタン（危険操作なので別セクションに）
        with st.expander("⚠️ 危険な操作", expanded=False):
            st.warning("この操作は取り消せません")
            col1, col2 = st.columns([3, 1])
            with col1:
                confirm_text = st.text_input("削除するには「削除」と入力", key="delete_confirm")
            with col2:
                if st.button("🗑️ クエスト削除", use_container_width=True, type="primary"):
                    if confirm_text == "削除":
                        show_delete_stamp_animation() # 削除時の演出
                        db.delete_quest(quest_id)
                        st.session_state.selected_quest_id = None
                        st.success("クエストを削除しました")
                        time.sleep(2) # 演出を見せるためのウェイト
                        st.rerun()
                    else:
                        st.error("「削除」と入力してください")
        
        st.divider()
        
        # コメントセクション
        st.subheader("💬 作業ログ")
        
        comments = db.get_comments(quest_id)
        if comments:
            for comment in comments:
                log_type = comment.get("log_type", "user")
                if log_type == "system":
                    # システムログの表示（シンプルに）
                    with st.container():
                        st.caption(f"🤖 {comment['created_at'][:16]} - {comment['content']}")
                else:
                    with st.chat_message("user"):
                        st.markdown(f"**{comment['user']}** ({comment['created_at'][:16]})")
                    st.write(comment["content"])
                    
                    # 添付ファイルがある場合
                    if comment.get("file_path"):
                        file_path = comment["file_path"]
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                            
                            # ファイル名からタイムスタンプを除去して表示
                            file_name = os.path.basename(file_path)
                            if "_" in file_name:
                                original_name = file_name.split("_", 1)[1]
                            else:
                                original_name = file_name
                                
                            st.download_button(
                                label=f"📥 {original_name}",
                                data=file_data,
                                file_name=original_name,
                                key=f"dl_comment_{comment['id']}"
                            )
        else:
            st.caption("コメントはまだありません")
        
        # コメント追加
        with st.form("add_comment_form"):
            comment_content = st.text_area("コメントを追加", placeholder="作業内容や進捗を記録...")
            uploaded_file = st.file_uploader("ファイルを添付", type=None)
            
            if st.form_submit_button("💬 コメント投稿"):
                if comment_content.strip():
                    file_path = None
                    # ファイル保存処理
                    if uploaded_file:
                        try:
                            os.makedirs("uploads", exist_ok=True)
                            # ファイル名にタイムスタンプを付与してユニーク化
                            file_name = f"{int(time.time())}_{uploaded_file.name}"
                            file_path = os.path.join("uploads", file_name)
                            
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                        except Exception as e:
                            st.error(f"ファイルの保存に失敗しました: {e}")
                    
                    db.add_comment(quest_id, st.session_state.username, comment_content, file_path)
                    st.success("コメントを追加しました")
                    st.rerun()
                else:
                    st.error("コメント内容を入力してください")

# ========== ページ: ダッシュボード ==========
elif page == "📊 ダッシュボード":
    st.header("📊 ダッシュボード")
    
    all_quests = db.get_all_quests()
    
    if not all_quests:
        st.info("クエストがありません")
        st.stop()
    
    # ステータス別集計
    st.subheader("📈 ステータス別集計")
    statuses = ["Backlog", "In Progress", "Review", "Done"]
    status_counts = {s: len([q for q in all_quests if q["status"] == s]) for s in statuses}
    
    cols = st.columns(4)
    for i, status in enumerate(statuses):
        with cols[i]:
            st.metric(status_label(status), status_counts[status])
    
    st.divider()
    
    # メンバー別抱え件数
    st.subheader("👥 メンバー別抱え件数")
    
    # 担当者ごとに集計（未完了のみ）
    active_quests = [q for q in all_quests if q["status"] != "Done"]
    assignee_counts = {}
    for q in active_quests:
        assignee = q["assignee"] or "未割当"
        assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    # ソートして表示
    sorted_assignees = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)
    
    for assignee, count in sorted_assignees:
        is_me = assignee == st.session_state.username
        prefix = "👉 " if is_me else ""
        bar_length = min(count * 2, 20)
        bar = "█" * bar_length
        st.markdown(f"{prefix}**{assignee}**: {count}件 `{bar}`")
    
    st.divider()
    
    # 期限超過タスク
    st.subheader("⚠️ 期限超過タスク")
    from datetime import date
    today = date.today().isoformat()
    
    overdue = [q for q in active_quests if q["due_date"] and q["due_date"] < today]
    
    if not overdue:
        st.success("期限超過のタスクはありません 🎉")
    else:
        for q in overdue:
            assignee = q["assignee"] or "未割当"
            st.warning(f"**#{q['id']} {q['title']}** - 担当: {assignee} / 期限: {q['due_date']}")

# ========== ページ: リソース管理 ==========
elif page == "📚 リソース":
    st.header("📚 リソース")
    
    # タブで機能を分ける
    tab1, tab2 = st.tabs(["📖 リソース一覧", "➕ 新規登録"])
    
    with tab1:
        # 検索とフィルタ
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 検索（タイトル/メモ/タグ）", placeholder="キーワードを入力...")
        
        with col2:
            categories = ["すべて"] + db.get_resource_categories()
            selected_category = st.selectbox("カテゴリ", categories)
        
        with col3:
            show_favorites = st.checkbox("⭐ お気に入りのみ")
        
        # タグフィルタ
        all_tags = db.get_resource_tags()
        if all_tags:
            selected_tags = st.multiselect("タグでフィルタ", all_tags)
        else:
            selected_tags = []
        
        st.divider()
        
        # リソース取得とフィルタリング
        resources = db.get_all_resources()
        
        # フィルタ適用
        if search_query:
            query = search_query.lower()
            resources = [r for r in resources if 
                query in r["title"].lower() or 
                query in (r["memo"] or "").lower() or 
                query in (r["tags"] or "").lower()]
        
        if selected_category != "すべて":
            resources = [r for r in resources if r["category"] == selected_category]
        
        if show_favorites:
            resources = [r for r in resources if r["is_favorite"]]
        
        if selected_tags:
            resources = [r for r in resources if 
                any(tag in (r["tags"] or "").split(",") for tag in selected_tags)]
        
        # 結果表示
        st.caption(f"📊 {len(resources)}件のリソース")
        
        if not resources:
            st.info("リソースが見つかりません")
        else:
            for res in resources:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        # タイトルとお気に入り
                        fav_icon = "⭐" if res["is_favorite"] else ""
                        # リソースタイプを判定
                        is_uploaded = res["url"].startswith("[UPLOADED]")
                        is_url = res["url"].startswith("http://") or res["url"].startswith("https://")
                        
                        if is_uploaded:
                            type_icon = "📤"
                        elif is_url:
                            type_icon = "🌐"
                        else:
                            type_icon = "📁"
                        st.markdown(f"### {fav_icon} {type_icon} {res['title']}")
                        
                        # カテゴリとタグ
                        tags_display = ""
                        if res["tags"]:
                            tags_display = " ".join([f"`{t.strip()}`" for t in res["tags"].split(",") if t.strip()])
                        st.caption(f"📁 {res['category']} {tags_display}")
                        
                        # パス/URL表示
                        if is_uploaded:
                            import os
                            file_path = res["url"].replace("[UPLOADED]", "")
                            file_name = os.path.basename(file_path)
                            if "_" in file_name:
                                original_name = "_".join(file_name.split("_")[1:])
                            else:
                                original_name = file_name
                            st.caption(f"📄 {original_name}")
                        elif is_url:
                            st.caption(f"🔗 {res['url']}")
                        else:
                            st.code(res["url"], language=None)
                        
                        # メモ
                        if res["memo"]:
                            st.markdown(f"*{res['memo']}*")
                    
                    with col2:
                        st.metric("閲覧数", res["view_count"])
                        if res["last_viewed_at"]:
                            st.caption(f"最終: {res['last_viewed_at'][:10]}")
                    
                    with col3:
                        # リソースのタイプを判定
                        is_uploaded = res["url"].startswith("[UPLOADED]")
                        is_url = res["url"].startswith("http://") or res["url"].startswith("https://")
                        
                        if is_uploaded:
                            # アップロードファイル: ダウンロードボタン
                            file_path = res["url"].replace("[UPLOADED]", "")
                            import os
                            if os.path.exists(file_path):
                                with open(file_path, "rb") as f:
                                    file_data = f.read()
                                file_name = os.path.basename(file_path)
                                # タイムスタンプを除去した元のファイル名
                                if "_" in file_name:
                                    original_name = "_".join(file_name.split("_")[1:])
                                else:
                                    original_name = file_name
                                st.download_button(
                                    "📥 ダウンロード",
                                    data=file_data,
                                    file_name=original_name,
                                    key=f"dl_{res['id']}",
                                    use_container_width=True
                                )
                                # 閲覧カウント
                                db.increment_view_count(res["id"])
                            else:
                                st.error("ファイルが見つかりません")
                        elif is_url:
                            # Web URL: リンクを表示
                            if st.button("🔗 開く", key=f"open_{res['id']}", use_container_width=True):
                                db.increment_view_count(res["id"])
                                st.markdown(f"[🌐 サイトを開く]({res['url']})")
                        else:
                            # ローカルパス: エクスプローラーで開くコマンドを表示
                            if st.button("📂 開く", key=f"open_{res['id']}", use_container_width=True):
                                db.increment_view_count(res["id"])
                                import subprocess
                                try:
                                    subprocess.Popen(f'explorer "{res["url"]}"')
                                    st.success("エクスプローラーで開きました")
                                except Exception as e:
                                    st.error(f"開けませんでした: {e}")
                        
                        # お気に入りトグル
                        fav_label = "★ 解除" if res["is_favorite"] else "☆ 追加"
                        if st.button(fav_label, key=f"fav_{res['id']}", use_container_width=True):
                            db.toggle_favorite(res["id"])
                            st.rerun()
                        
                        # 削除
                        if st.button("🗑️", key=f"del_{res['id']}", use_container_width=True):
                            db.delete_resource(res["id"])
                            st.success("削除しました")
                            st.rerun()
    
    with tab2:
        st.subheader("➕ 新規リソース登録")
        
        with st.form("add_resource_form"):
            title = st.text_input("タイトル *", placeholder="例: プロジェクト資料フォルダ")
            
            # リソースタイプ選択
            resource_type = st.radio(
                "リソースタイプ",
                ["🌐 Webサイト（URL）", "📁 ローカルフォルダ/ファイル"],
                horizontal=True
            )
            
            if resource_type == "🌐 Webサイト（URL）":
                url = st.text_input("URL *", placeholder="https://...")
            else:
                url = st.text_input("パス *", placeholder=r"C:\Users\...\Documents\プロジェクト")
                st.caption("💡 エクスプローラーでフォルダを右クリック → 「パスをコピー」でパスを取得できます")
            
            col1, col2 = st.columns(2)
            with col1:
                # カテゴリ選択または新規入力
                existing_cats = db.get_resource_categories()
                preset_cats = ["運用", "広報/法務", "デザイン", "トレーニング", "ツール", "その他"]
                all_cats = sorted(set(existing_cats + preset_cats))
                category = st.selectbox("カテゴリ", all_cats)
            
            with col2:
                tags = st.text_input("タグ（カンマ区切り）", placeholder="プロジェクト, 資料, 2024")
            
            memo = st.text_area("メモ", placeholder="リソースの説明やメモ...")
            
            submitted = st.form_submit_button("📥 登録", use_container_width=True)
            
            if submitted:
                if not title.strip():
                    st.error("タイトルは必須です")
                elif not url.strip():
                    st.error("URLまたはパスは必須です")
                else:
                    try:
                        db.create_resource(
                            title=title,
                            url=url,
                            category=category,
                            tags=tags,
                            memo=memo,
                            created_by=st.session_state.username
                        )
                        st.success(f"「{title}」を登録しました！")
                        st.balloons()
                    except Exception as e:
                        st.error(f"エラー: {e}")
    
    # ファイルアップロード（タブの外に配置）
    st.divider()
    st.subheader("📤 ファイルアップロード")
    
    import os
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    uploaded_file = st.file_uploader(
        "ファイルを選択（複数人で共有可能）",
        type=["xlsx", "xls", "docx", "doc", "pdf", "pptx", "ppt", "txt", "csv", "png", "jpg", "jpeg", "gif", "zip"],
        help="Excel, Word, PDF, PowerPoint, 画像, ZIPファイルなどをアップロードできます"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            upload_title = st.text_input("リソース名", value=uploaded_file.name)
            upload_category = st.selectbox("カテゴリ", ["運用", "広報/法務", "デザイン", "トレーニング", "ツール", "その他"], key="upload_cat")
            upload_tags = st.text_input("タグ（カンマ区切り）", key="upload_tags")
            upload_memo = st.text_input("メモ", key="upload_memo")
        
        with col2:
            st.info(f"📄 {uploaded_file.name}\n\n📦 {uploaded_file.size / 1024:.1f} KB")
        
        if st.button("📤 アップロードして登録", use_container_width=True):
            try:
                # ファイル保存
                import time
                timestamp = int(time.time())
                safe_name = f"{timestamp}_{uploaded_file.name}"
                file_path = os.path.join(UPLOAD_DIR, safe_name)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # DBに登録（URLにファイルパスを保存、プレフィックスで識別）
                db.create_resource(
                    title=upload_title,
                    url=f"[UPLOADED]{file_path}",
                    category=upload_category,
                    tags=upload_tags,
                    memo=upload_memo,
                    created_by=st.session_state.username
                )
                st.success(f"「{upload_title}」をアップロードしました！他のユーザーもダウンロードできます。")
                st.balloons()
            except Exception as e:
                st.error(f"アップロードエラー: {e}")
