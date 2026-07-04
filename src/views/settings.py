
import streamlit as st
import json
from src.database import (
    get_all_categories, get_all_users, get_notification_members,
    add_notification_member, remove_notification_member,
    save_system_setting, get_system_setting,
    get_notification_logs, create_user, delete_user, check_email_exists,
    get_all_departments, create_department, update_department, delete_department,
    get_users_by_department, update_user_department, get_department_by_id,
    update_user_password
)

def render_settings_view():
    from src.ui import render_header
    render_header("システム設定", "settings")
    
    st.info("通知グループとSMTP設定、およびユーザーを管理します。")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📧 SMTP設定", "🏢 部署管理", "👤 ユーザー管理", "👥 通知グループ", "📜 通知ログ"])
    
    # --- SMTP Configuration ---
    with tab1:
        st.header("SMTP設定")
        st.caption("メール通知を使用する場合に設定してください。")
        
        current_config_json = get_system_setting('smtp_config')
        default_config = {
            "enabled": False, "host": "smtp.gmail.com", "port": 587, 
            "user": "", "password": "", "from_addr": ""
        }
        
        if current_config_json:
            try:
                loaded = json.loads(current_config_json)
                default_config.update(loaded)
            except:
                pass

        # 既存パスワードが登録済みかどうか（値そのものは画面に出さない）
        has_saved_password = bool(default_config.get('password'))

        with st.form("smtp_form"):
            enabled = st.checkbox("メール通知を有効にする", value=default_config['enabled'])
            c1, c2 = st.columns(2)
            host = c1.text_input("SMTPホスト", value=default_config['host'], help="例: smtp.gmail.com")
            port = c2.number_input("SMTPポート", value=int(default_config['port']), help="例: 587")
            user = c1.text_input("SMTPユーザー名", value=default_config['user'])
            # セキュリティ上、保存済みパスワードはフォームに再表示しない。
            # 空欄のまま保存すれば既存パスワードを維持する。
            password_help = "登録済み。変更する場合のみ入力してください（空欄で現在の値を維持）" if has_saved_password else None
            password_placeholder = "●●●●●●（登録済み）" if has_saved_password else ""
            password = c2.text_input(
                "SMTPパスワード",
                value="",
                type="password",
                help=password_help,
                placeholder=password_placeholder,
            )
            from_addr = st.text_input("送信元メールアドレス (From)", value=default_config['from_addr'])

            if st.form_submit_button("保存"):
                # パスワード欄が空欄なら既存の値を維持、入力があればそれを採用
                effective_password = password if password else default_config.get('password', '')
                new_config = {
                    "enabled": enabled, "host": host, "port": port,
                    "user": user, "password": effective_password, "from_addr": from_addr
                }
                save_system_setting('smtp_config', json.dumps(new_config))
                st.success("SMTP設定を保存しました。")

        st.divider()
        st.subheader("接続テスト")
        test_email = st.text_input("テスト送信先メールアドレス", placeholder="your_email@example.com")
        if st.button("テストメール送信"):
            if not test_email:
                st.error("テスト送信先を入力してください。")
            else:
                saved_config_json = get_system_setting('smtp_config')
                if not saved_config_json:
                     st.error("設定が保存されていません。先に保存してください。")
                else:
                    conf = json.loads(saved_config_json)
                    if not conf.get('enabled'):
                        st.warning("設定では「メール通知を有効にする」がOFFになっていますが、テスト送信を試みます。")
                        
                    import smtplib
                    from email.mime.text import MIMEText
                    
                    try:
                        msg = MIMEText("This is a test email from Demo Unit Loan Management System.")
                        msg['Subject'] = "[Test] SMTP Connection Verification"
                        msg['From'] = conf.get('from_addr', 'noreply@example.com')
                        msg['To'] = test_email
                        
                        with smtplib.SMTP(conf.get('host', 'localhost'), int(conf.get('port', 25))) as server:
                             if int(conf.get('port', 25)) == 587:
                                 server.starttls()
                             if conf.get('user') and conf.get('password'):
                                 server.login(conf.get('user'), conf.get('password'))
                             server.send_message(msg)
                        
                        st.success(f"送信成功！ ({test_email})")
                    except Exception as e:
                        st.error(f"送信失敗:\n{e}")

    # --- Department Management ---
    with tab2:
        st.header("部署管理")
        st.caption("ユーザーをまとめる部署を管理します。カテゴリの管理部署として使用できます。")
        
        # Add Department
        with st.expander("➕ 新規部署登録", expanded=False):
            with st.form("create_dept_form"):
                new_dept_name = st.text_input("部署名")
                if st.form_submit_button("部署を作成"):
                    if not new_dept_name:
                        st.error("部署名を入力してください。")
                    else:
                        success, msg = create_department(new_dept_name)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        
        st.divider()
        
        # List Departments
        st.subheader("登録済み部署一覧")
        departments = get_all_departments()
        
        if departments:
            # パフォーマンス改善: 全ユーザーを一括取得してグループ化（N+1問題回避）
            all_users = get_all_users()
            users_by_dept = {}
            for u in all_users:
                dept_id = u.get('department_id')
                if dept_id not in users_by_dept:
                    users_by_dept[dept_id] = []
                users_by_dept[dept_id].append(u)
            
            for dept in departments:
                users_in_dept = users_by_dept.get(dept['id'], [])
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**🏢 {dept['name']}**")
                    c2.caption(f"{len(users_in_dept)} 名")
                    
                    # Delete button
                    if c3.button("削除", key=f"del_dept_{dept['id']}", type="secondary"):
                        success, msg = delete_department(dept['id'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    
                    # Show users in this department
                    if users_in_dept:
                        with st.expander(f"所属ユーザー ({len(users_in_dept)}名)", expanded=False):
                            for u in users_in_dept:
                                role_badge = "👑" if u['role'] == 'admin' else "👤" if u['role'] == 'user' else "🏢"
                                st.write(f"{role_badge} {u['name']} ({u['email']})")
        else:
            st.info("部署が登録されていません。")
                
    # --- User Management ---
    with tab3:
        st.header("ユーザー管理")
        st.caption("システムにログインできるユーザーを追加・削除します。")
        
        # パスワードリセットダイアログを表示（セッション状態で制御）
        _render_password_reset_dialog()


        # Get departments for dropdown
        departments = get_all_departments()
        dept_options = {d['name']: d['id'] for d in departments}
        dept_options_with_none = {"（部署なし）": None, **dept_options}

        # 1. Add User
        with st.expander("➕ 新規ユーザー登録", expanded=False):
            with st.form("create_user_form"):
                new_email = st.text_input("メールアドレス (ID)")
                new_name = st.text_input("氏名")
                new_pass = st.text_input("パスワード", type="password")
                new_pass_confirm = st.text_input("パスワード (確認)", type="password")
                new_role = st.selectbox("権限", ["user", "admin", "related"], index=0, help="admin: 全権限, user: 一般, related: 関連業者")
                new_dept = st.selectbox("所属部署", list(dept_options_with_none.keys()), index=0)
                
                if st.form_submit_button("ユーザーを作成"):
                    if not new_email or not new_name or not new_pass:
                        st.error("全ての項目を入力してください。")
                    elif new_pass != new_pass_confirm:
                        st.error("パスワードが一致しません。")
                    elif check_email_exists(new_email):
                        st.error("このメールアドレスは既に使用されています。")
                    else:
                        if create_user(new_email, new_name, new_pass, new_role):
                            # Get the newly created user and set department
                            from src.database import get_user_by_email
                            new_user = get_user_by_email(new_email)
                            if new_user and dept_options_with_none[new_dept] is not None:
                                update_user_department(new_user['id'], dept_options_with_none[new_dept])
                            st.success(f"ユーザーを作成しました: {new_name}")
                            st.rerun()
                        else:
                            st.error("作成に失敗しました。")

        st.divider()

        # 2. List Users by Department
        st.subheader("登録済みユーザー一覧")
        
        # Show users grouped by department
        for dept in departments:
            users_in_dept = get_users_by_department(dept['id'])
            if users_in_dept:
                with st.expander(f"🏢 {dept['name']} ({len(users_in_dept)}名)", expanded=True):
                    for u in users_in_dept:
                        _render_user_row(u, dept_options_with_none)
        
        # Show users without department
        users_no_dept = get_users_by_department(None)
        if users_no_dept:
            with st.expander(f"📋 部署未設定 ({len(users_no_dept)}名)", expanded=True):
                for u in users_no_dept:
                    _render_user_row(u, dept_options_with_none)
        
        if not departments and not users_no_dept:
            users = get_all_users()
            if users:
                for u in users:
                    _render_user_row(u, dept_options_with_none)
            else:
                st.info("ユーザーがいません。")

    # --- Notification Groups ---
    with tab4:
        st.header("通知グループ")
        st.caption("カテゴリごとの異常発生時の通知先を設定します。")
        
        categories = get_all_categories()
        cat_map = {c['name']: c['id'] for c in categories}
        if cat_map:
            selected_cat_name = st.selectbox("カテゴリ選択", list(cat_map.keys()))
            
            if selected_cat_name:
                cat_id = cat_map[selected_cat_name]
                members = get_notification_members(cat_id)
                
                # Show current members
                st.subheader(f"{selected_cat_name} の通知先メンバー")
                if members:
                    for m in members:
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"👤 {m['name']} ({m['email']})")
                        if c2.button("削除", key=f"del_{m['id']}"):
                            remove_notification_member(cat_id, m['id'])
                            st.rerun()
                else:
                    st.write("メンバーがいません。")
                
                st.divider()
                
                # Add Member - Two options: individual or by department
                st.subheader("メンバー追加")
                
                add_tab1, add_tab2 = st.tabs(["👤 個別追加", "🏢 部署で追加"])
                
                # Tab 1: Individual user addition
                with add_tab1:
                    all_users = get_all_users()
                    # Filter out existing members
                    member_ids = [m['id'] for m in members]
                    available_users = [u for u in all_users if u['id'] not in member_ids]
                    
                    if available_users:
                        u_map = {f"{u['name']} ({u['email']})": u['id'] for u in available_users}
                        selected_user_label = st.selectbox("ユーザー選択", list(u_map.keys()))
                        if st.button("追加", key="add_user_btn"):
                            add_notification_member(cat_id, u_map[selected_user_label])
                            st.success("メンバーを追加しました。")
                            st.rerun()
                    else:
                        st.info("追加可能なユーザーがいません（全員追加済みか、ユーザーマスタが空です）。")
                
                # Tab 2: Department-based addition
                with add_tab2:
                    departments = get_all_departments()
                    if departments:
                        dept_map = {d['name']: d['id'] for d in departments}
                        selected_dept_name = st.selectbox("部署選択", list(dept_map.keys()), key="dept_select_notif")
                        
                        if selected_dept_name:
                            dept_id = dept_map[selected_dept_name]
                            dept_users = get_users_by_department(dept_id)
                            
                            # Check how many are not already members
                            member_ids = [m['id'] for m in members]
                            new_users = [u for u in dept_users if u['id'] not in member_ids]
                            
                            if new_users:
                                st.info(f"「{selected_dept_name}」の {len(new_users)} 名を追加できます。")
                                
                                # Show preview of users to be added
                                with st.expander("追加されるユーザー"):
                                    for u in new_users:
                                        st.write(f"👤 {u['name']} ({u['email']})")
                                
                                if st.button(f"「{selected_dept_name}」の全員を追加", key="add_dept_btn", type="primary"):
                                    added_count = 0
                                    for u in new_users:
                                        add_notification_member(cat_id, u['id'])
                                        added_count += 1
                                    st.success(f"{added_count} 名を追加しました。")
                                    st.rerun()
                            else:
                                if dept_users:
                                    st.info(f"「{selected_dept_name}」のメンバーは全員追加済みです。")
                                else:
                                    st.warning(f"「{selected_dept_name}」にはユーザーが所属していません。")
                    else:
                        st.info("部署が登録されていません。設定 → 部署管理 で部署を追加してください。")
        else:
            st.warning("カテゴリが登録されていません。マスタ管理で登録してください。")

    # --- Logs ---
    with tab5:
        st.header("通知ログ")
        if st.button("更新"):
            st.rerun()
            
        logs = get_notification_logs(limit=50)
        if logs:
            for l in logs:
                status_color = "green" if l['status'] == 'sent' else "red" if l['status'] == 'failed' else "grey"
                st.markdown(f"**[{l['created_at']}]** :{status_color}[{l['status']}] {l['event_type']} -> {l['recipient']}")
                if l['error_message']:
                    st.error(f"Error: {l['error_message']}")
                st.divider()
        else:
            st.write("ログはありません。")


def _render_user_row(u, dept_options_with_none):
    """Render a single user row with department selection and delete button."""
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1, 0.5, 0.5])
        
        # 1. Name
        c1.markdown(f"**{u['name']}**")
        c1.caption(f"{u['email']}")
        
        # 2. Role (Editable)
        from src.database import update_user_role
        role_map = {'admin': '👑 管理者', 'related': '🏢 関係者', 'user': '👤 一般'}
        role_options = list(role_map.keys())
        current_role = u.get('role', 'user')
        if current_role not in role_options: current_role = 'user'
        current_idx = role_options.index(current_role)
        
        new_role = c2.selectbox(
            "権限", 
            role_options, 
            format_func=lambda x: role_map[x],
            index=current_idx, 
            key=f"role_edit_{u['id']}", 
            label_visibility="collapsed"
        )
        if new_role != current_role:
             success, msg = update_user_role(u['id'], new_role)
             if success:
                 st.cache_data.clear()
                 st.toast(f"権限を変更しました: {role_map[new_role]}")
                 st.rerun()
             else:
                 st.error(msg)
        
        # 3. Department selector
        current_dept_id = u.get('department_id')
        dept_names = list(dept_options_with_none.keys())
        current_idx_dept = 0
        for i, (name, did) in enumerate(dept_options_with_none.items()):
            if did == current_dept_id:
                current_idx_dept = i
                break
        
        new_dept_name = c3.selectbox(
            "部署",
            dept_names,
            index=current_idx_dept,
            key=f"dept_sel_{u['id']}",
            label_visibility="collapsed"
        )
        new_dept_id = dept_options_with_none[new_dept_name]
        if new_dept_id != current_dept_id:
            update_user_department(u['id'], new_dept_id)
            st.rerun()
        
        # Password reset button
        if c4.button("🔑", key=f"reset_pwd_{u['id']}", help="パスワードリセット"):
            st.session_state['reset_password_user_id'] = u['id']
            st.session_state['reset_password_user_name'] = u['name']
            st.rerun()
        
        # Delete button
        if c5.button("🗑️", key=f"del_user_{u['id']}", help="削除"):
            from src.database import delete_user
            success, msg = delete_user(u['id'])
            if success:
                st.warning(msg)
                st.rerun()
            else:
                st.error(msg)


def _render_password_reset_dialog():
    """管理者用パスワードリセットダイアログを表示"""
    user_id = st.session_state.get('reset_password_user_id')
    user_name = st.session_state.get('reset_password_user_name', '')
    
    if not user_id:
        return
    
    @st.dialog(f"🔑 パスワードリセット: {user_name}")
    def password_reset_dialog():
        st.warning("管理者としてパスワードをリセットします。現在のパスワードは不要です。")
        
        new_password = st.text_input("新しいパスワード", type="password")
        new_password_confirm = st.text_input("新しいパスワード（確認）", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("リセット実行", type="primary", use_container_width=True):
                if not new_password or not new_password_confirm:
                    st.error("パスワードを入力してください。")
                elif new_password != new_password_confirm:
                    st.error("パスワードが一致しません。")
                elif len(new_password) < 4:
                    st.error("パスワードは4文字以上にしてください。")
                else:
                    success, message = update_user_password(user_id, new_password)
                    if success:
                        st.success(f"{user_name} のパスワードをリセットしました。")
                        st.session_state.pop('reset_password_user_id', None)
                        st.session_state.pop('reset_password_user_name', None)
                        st.rerun()
                    else:
                        st.error(f"エラー: {message}")
        
        with col2:
            if st.button("キャンセル", use_container_width=True):
                st.session_state.pop('reset_password_user_id', None)
                st.session_state.pop('reset_password_user_name', None)
                st.rerun()
    
    password_reset_dialog()
