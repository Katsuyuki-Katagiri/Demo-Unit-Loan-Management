
import sqlite3
import os
import json

DB_PATH = os.path.join("data", "app.db")
OUT_PATH = "debug_out.txt"

def inspect_units():
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    results = []
    print("--- Device Units ---")
    c.execute("SELECT * FROM device_units")
    units = c.fetchall()
    for u in units:
        results.append(dict(u))
        
    with open(OUT_PATH, "w", encoding='utf-8') as f:
        json.dump(results, f, default=str, indent=2)
        
    print(f"Total count: {len(units)}")
    conn.close()

if __name__ == "__main__":
    inspect_units()
