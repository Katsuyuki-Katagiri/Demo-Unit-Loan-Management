
import os
import streamlit as st
from supabase import create_client

def cleanup_items():
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    client = create_client(url, key)
    
    # 1. Get all Category Names
    cats = client.table("categories").select("name").execute()
    cat_names = [c['name'] for c in cats.data]
    print(f"Found {len(cat_names)} categories.")

    # 2. Find Items matching these names
    garbage_ids = []
    items = client.table("items").select("id, name").execute()
    
    print("\n--- Deleting Garbage Items ---")
    for i in items.data:
        if i['name'] in cat_names:
            print(f"Deleting Item ID: {i['id']}, Name: {i['name']}")
            garbage_ids.append(i['id'])
    
    if garbage_ids:
        # Batch delete
        client.table("items").delete().in_("id", garbage_ids).execute()
        print(f"\nDeleted {len(garbage_ids)} items.")
    else:
        print("\nNo garbage items found.")

if __name__ == "__main__":
    cleanup_items()
