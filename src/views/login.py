import streamlit as st
from src.auth import login_user

def render_login_view():
    from src.ui import render_header
    render_header("ログイン", "login")
    
    with st.form("login_form"):
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        
        submitted = st.form_submit_button("ログイン", use_container_width=True)
        
        if submitted:
            if login_user(email, password):
                st.success("ログインしました")
                st.rerun()
            else:
                st.error("メールアドレスまたはパスワードが間違っています。")
