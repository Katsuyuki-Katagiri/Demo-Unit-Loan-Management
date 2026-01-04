
import sqlite3
import os

DB_PATH = os.path.join("data", "app.db")

def fix_data():
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    target_unit_id = 1
    
    print(f"Deleting data for Unit ID: {target_unit_id}...")
    
    try:
        # Delete related tables first (foreign keys might restrict, but explicit delete is safer)
        tables = [
            "check_lines", "issues", "check_sessions", "returns", "loans", 
            "unit_overrides", "device_units"
        ]
        
        # We need to find IDs for child tables to be precise, 
        # but for cleanup of a specific root unit, we can filter by unit_id or through joins.
        
        # 1. Get loan IDs
        c.execute("SELECT id FROM loans WHERE device_unit_id = ?", (target_unit_id,))
        loan_ids = [r[0] for r in c.fetchall()]
        
        # 2. Get check_session IDs
        c.execute("SELECT id FROM check_sessions WHERE device_unit_id = ?", (target_unit_id,))
        session_ids = [r[0] for r in c.fetchall()]
        
        # Delete from check_lines
        if session_ids:
            placeholders = ','.join(['?']*len(session_ids))
            c.execute(f"DELETE FROM check_lines WHERE check_session_id IN ({placeholders})", session_ids)
            print(f"Deleted check_lines for sessions: {session_ids}")

        # Delete from issues
        c.execute("DELETE FROM issues WHERE device_unit_id = ?", (target_unit_id,))
        print("Deleted issues")

        # Delete from check_sessions
        c.execute("DELETE FROM check_sessions WHERE device_unit_id = ?", (target_unit_id,))
        print("Deleted check_sessions")

        # Delete from returns (linked to loans)
        if loan_ids:
            placeholders = ','.join(['?']*len(loan_ids))
            c.execute(f"DELETE FROM returns WHERE loan_id IN ({placeholders})", loan_ids)
            print("Deleted returns")

        # Delete from loans
        c.execute("DELETE FROM loans WHERE device_unit_id = ?", (target_unit_id,))
        print("Deleted loans")

        # Delete from unit_overrides
        c.execute("DELETE FROM unit_overrides WHERE device_unit_id = ?", (target_unit_id,))
        print("Deleted unit_overrides")

        # Finally delete the unit
        c.execute("DELETE FROM device_units WHERE id = ?", (target_unit_id,))
        print("Deleted device_unit")
        
        conn.commit()
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_data()
