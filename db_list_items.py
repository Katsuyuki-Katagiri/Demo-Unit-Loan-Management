
import os
import streamlit as st
from supabase import create_client

def list_items():
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    client = create_client(url, key)
    
    print("--- Categories ---")
    cats = client.table("categories").select("name").execute()
    cat_names = {c['name'] for c in cats.data}
    print(cat_names)

    print("\n--- Items ---")
    items = client.table("items").select("id, name").execute()
    for i in items.data:
        is_garbage = i['name'] in cat_names
        marker = "[GARBAGE?]" if is_garbage else ""
        print(f"ID: {i['id']}, Name: {i['name']} {marker}")

if __name__ == "__main__":
    list_items()
