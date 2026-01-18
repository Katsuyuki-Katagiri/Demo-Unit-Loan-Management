# データベースレイヤー ディスパッチャー
# Supabaseが設定されている場合はSupabase版を使用し、そうでなければSQLiteを使用

import os
import streamlit as st

# Supabaseが設定されているかチェック
_use_supabase = False
try:
    _supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    _supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if _supabase_url and _supabase_key:
        _use_supabase = True
except Exception:
    pass

if _use_supabase:
    # Supabase版を使用
    from src.database_supabase import *
else:
    # SQLite版を使用
    from src.database_sqlite import *
