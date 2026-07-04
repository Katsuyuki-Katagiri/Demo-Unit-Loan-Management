import streamlit as st
# Force reload: 2026-01-25 17:36
import os
from src.database import init_db, check_users_exist, seed_categories, update_user_password, get_user_by_id
from src.auth import is_logged_in, logout_user
from src.views.setup import render_setup_view
from src.views.login import render_login_view
from src.views.home import render_home_view
from src.views.master import render_master_view

# Page configuration
st.set_page_config(
    page_title="デモ機管理アプリ",
    page_icon="🏥",
    layout="wide", # Phase 1: Wide layout for better tables/grids
    initial_sidebar_state="collapsed"
)

# Apply Global Styles
from src.styles import apply_custom_css
apply_custom_css()


def _stop_with_db_connection_error(err: Exception):
    """
    DB（Supabase）への接続に失敗したとき、生のトレースバックで落とさず、
    日本語の案内と再接続ボタンを表示してアプリを停止する。
    """
    st.error("🔌 データベースに接続できませんでした。")
    st.markdown(
        """
        時間をおいて再度お試しください。数分待っても復旧しない場合は、以下をご確認ください。

        - **Supabaseプロジェクトが一時停止していないか**（無料プランは無操作が続くと自動停止します）。
          Supabaseのダッシュボードでプロジェクトを開き、停止中なら「Restore / Resume」で再開してください。
        - **接続情報（SUPABASE_URL / SUPABASE_KEY）が正しいか**。
        - Supabase側で一時的な障害が発生していないか。
        """
    )
    if st.button("🔄 再接続を試す", type="primary"):
        # キャッシュ済みのSupabaseクライアントを破棄してから再実行
        try:
            st.cache_resource.clear()
        except Exception:
            pass
        st.session_state.pop('db_initialized', None)
        st.rerun()

    with st.expander("技術的な詳細"):
        st.code(f"{type(err).__name__}: {err}")

    st.stop()


# Initialize DB on start
if 'db_initialized' not in st.session_state:
    try:
        init_db()
        # Migration for new features - すべてのマイグレーションを起動時に実行
        from src.database import (
            migrate_category_visibility,
            migrate_loans_assetment_check,
            migrate_loans_notes,
            migrate_returns_assetment_check,
            migrate_returns_notes
        )
        migrate_category_visibility()
        migrate_loans_assetment_check()
        migrate_loans_notes()
        migrate_returns_assetment_check()
        migrate_returns_notes()

        seed_categories()
        st.session_state['db_initialized'] = True
    except Exception as e:
        # 起動時のDB接続失敗を握りつぶさず、ユーザーに分かる形で案内する
        _stop_with_db_connection_error(e)

def _render_password_change_dialog():
    """パスワード変更ダイアログを表示"""
    from src.auth import check_password
    
    @st.dialog("🔑 パスワード変更")
    def password_dialog():
        st.write("新しいパスワードを設定してください。")
        
        current_password = st.text_input("現在のパスワード", type="password")
        new_password = st.text_input("新しいパスワード", type="password")
        new_password_confirm = st.text_input("新しいパスワード（確認）", type="password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("変更", type="primary", use_container_width=True):
                if not current_password or not new_password or not new_password_confirm:
                    st.error("すべての項目を入力してください。")
                elif new_password != new_password_confirm:
                    st.error("新しいパスワードが一致しません。")
                elif len(new_password) < 4:
                    st.error("パスワードは4文字以上にしてください。")
                else:
                    # 現在のパスワードを確認
                    user_id = st.session_state.get('user_id')
                    user = get_user_by_id(user_id)
                    
                    if user and check_password(current_password, user['password_hash']):
                        success, message = update_user_password(user_id, new_password)
                        if success:
                            st.success(message)
                            st.session_state['show_password_change'] = False
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("現在のパスワードが正しくありません。")
        
        with col2:
            if st.button("キャンセル", use_container_width=True):
                st.session_state['show_password_change'] = False
                st.rerun()
    
    password_dialog()

def main():
    # 1. Check if Setup is needed
    # 起動直後のDBアクセス。接続断が起きても生のトレースバックで落とさない。
    try:
        users_exist = check_users_exist()
    except Exception as e:
        _stop_with_db_connection_error(e)
        return

    if not users_exist:
        render_setup_view()
        return

    # 2. Check Authentication
    if not is_logged_in():
        render_login_view()
        return

    # 3. Main Logic (Logged In)
    
    def reset_home_state():
        """ホームボタンが押された時にホーム画面の状態をリセットするコールバック"""
        if st.session_state.get('nav_selection') == "ホーム":
            st.session_state['selected_category_id'] = None
            st.session_state['selected_type_id'] = None
            st.session_state['selected_unit_id'] = None
            st.session_state['loan_mode'] = False
            st.session_state['return_mode'] = False
            if 'checklist_data' in st.session_state: del st.session_state['checklist_data']
            if 'return_checklist_data' in st.session_state: del st.session_state['return_checklist_data']

    # Sidebar Navigation
    with st.sidebar:
        st.write(f"ユーザー: **{st.session_state.get('user_name')}**")
        st.caption(f"権限: {st.session_state.get('user_role')}")
        
        # Navigation Menu
        # Key-Value pair for cleaner code or just list? List is fine for simple app.
        page_options = ["ホーム"]
        
        page_options.append("分析")
        
        if st.session_state.get('user_role') in ['admin', 'related']:
            page_options.append("マスタ管理")
            
        if st.session_state.get('user_role') == 'admin':
            page_options.append("システム設定")
            
        # keyとon_changeを追加して、選択変更時にリセット処理を実行
        selected_page = st.radio("メニュー", page_options, key="nav_selection", on_change=reset_home_state)
        
        st.divider()
        
        # パスワード変更（管理者のみ）
        if st.session_state.get('user_role') == 'admin':
            if st.button("🔑 パスワード変更"):
                st.session_state['show_password_change'] = True
        
        if st.button("ログアウト", type="primary"):
            logout_user()
            st.rerun()
    
    # パスワード変更ダイアログ
    if st.session_state.get('show_password_change'):
        _render_password_change_dialog()

    # Routing
    if selected_page == "ホーム":
        render_home_view()
    elif selected_page == "分析":
        from src.views.analytics import render_analytics_view
        render_analytics_view()
    elif selected_page == "マスタ管理":
        render_master_view()
    elif selected_page == "システム設定":
        from src.views.settings import render_settings_view
        render_settings_view()

if __name__ == "__main__":
    main()
