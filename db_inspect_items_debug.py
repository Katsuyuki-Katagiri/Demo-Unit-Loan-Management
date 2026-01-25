
import os
import streamlit as st
from supabase import create_client

def inspect_get_all_items():
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("SUPABASE_URL or SUPABASE_KEY not set")
        return
    
    client = create_client(url, key)
    
    print("--- Inspecting 'items' table directly ---")
    items_direct = client.table("items").select("*").execute()
    print(f"Count: {len(items_direct.data)}")
    if items_direct.data:
        print(f"First item: {items_direct.data[0]}")
    
    print("\n--- Inspecting 'get_all_items' function logic ---")
    # Simulate the logic instead of importing to avoid cache/dependency issues in this script
    result = client.table("items").select("*").execute()
    print(f"Simulated Result Count: {len(result.data)}")
    for item in result.data[:5]:
        print(f"ID: {item.get('id')}, Name: {item.get('name')}, Tips: {item.get('tips', 'N/A')}")
        
    print("\n--- Inspecting 'categories' table for comparison ---")
    cats = client.table("categories").select("*").execute()
    for cat in cats.data[:5]:
         print(f"Category ID: {cat.get('id')}, Name: {cat.get('name')}")

if __name__ == "__main__":
    inspect_get_all_items()
