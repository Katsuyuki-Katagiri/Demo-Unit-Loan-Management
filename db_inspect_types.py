
import os
import streamlit as st
from supabase import create_client

def inspect_types():
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("SUPABASE_URL or SUPABASE_KEY not set")
        return
    
    client = create_client(url, key)
    
    print("--- Categories ---")
    cats = client.table("categories").select("*").execute()
    cat_map = {}
    for c in cats.data:
        print(f"ID: {c['id']}, Name: {c['name']}")
        cat_map[c['id']] = c['name']
        
    print("\n--- Device Type ID: 1 ---")
    type1 = client.table("device_types").select("*").eq("id", 1).execute()
    if type1.data:
        t = type1.data[0]
        cat_name = cat_map.get(t['category_id'], "Unknown")
        print(f"ID: {t['id']}, Name: '{t['name']}', CategoryID: {t['category_id']} ({cat_name})")
    else:
        print("Device Type ID 1 not found")

    print("\n--- All Device Types ---")
    types = client.table("device_types").select("*").execute()
    for t in types.data:
        cat_name = cat_map.get(t['category_id'], "Unknown")
        print(f"ID: {t['id']}, Name: '{t['name']}', CategoryID: {t['category_id']} ({cat_name})")

if __name__ == "__main__":
    inspect_types()
