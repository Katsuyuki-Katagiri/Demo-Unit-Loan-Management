
import os
import sys
import toml
from supabase import create_client

# Load secrets
try:
    secrets = toml.load(".streamlit/secrets.toml")
    url = secrets["SUPABASE_URL"]
    key = secrets["SUPABASE_KEY"]
except Exception as e:
    print(f"Error loading secrets: {e}")
    sys.exit(1)

def inspect_items():
    try:
        client = create_client(url, key)
        print(f"Connected to Supabase: {url}")
        
        # Fetch items
        response = client.table("items").select("*").limit(1).execute()
        data = response.data
        
        if not data:
            print("No items found in 'items' table.")
            # Check columns via empty insert/analysis or just assuming empty
            return

        item = data[0]
        print("Keys in returned item:")
        print(list(item.keys()))
        
        if "photo_path" in item:
            print(f"photo_path exists! Value: {item['photo_path']}")
        else:
            print("CRITICAL: photo_path key is MISSING.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_items()
