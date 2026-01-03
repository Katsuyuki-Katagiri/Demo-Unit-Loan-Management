
import sqlite3
import os
import shutil
from src.database import (
    DB_PATH, init_db, create_device_type, create_item, add_template_line,
    create_device_unit, get_device_units, update_unit_status,
    create_loan, create_check_session, create_check_line, create_issue,
    get_open_issues, get_device_unit_by_id
)
from src.logic import process_loan

def setup_test_data():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    init_db()
    
    # 1. Create Master Data
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO categories (name) VALUES ('Test Category')")
    cat_id = c.lastrowid
    conn.commit()
    conn.close()
    
    type_id = create_device_type(cat_id, "Test Type A")
    item1 = create_item("Item 1")
    item2 = create_item("Item 2")
    
    add_template_line(type_id, item1, 1)
    add_template_line(type_id, item2, 2)
    
    # 2. Create Units
    create_device_unit(type_id, "LOT001", "2023-01-01", "Shelf A") # For Success Test
    create_device_unit(type_id, "LOT002", "2023-01-01", "Shelf B") # For NG Test
    
    units = get_device_units(type_id)
    return units[0], units[1], item1, item2

def verify():
    print("--- Starting Phase 2 Verification ---")
    
    unit_ok, unit_ng, item1, item2 = setup_test_data()
    print(f"Created Test Units: OK={unit_ok['id']}, NG={unit_ng['id']}")
    
    # Test 1: Successful Loan
    print("\n[Test 1] Process Successful Loan...")
    results_ok = [
        {'item_id': item1, 'name': 'Item 1', 'required_qty': 1, 'result': 'OK'},
        {'item_id': item2, 'name': 'Item 2', 'required_qty': 2, 'result': 'OK'}
    ]
    
    status = process_loan(
        device_unit_id=unit_ok['id'],
        checkout_date="2024-01-01",
        destination="Hospital A",
        purpose="Demo",
        check_results=results_ok,
        photo_dir="test_photos",
        user_name="Tester"
    )
    
    print(f"Result Status: {status}")
    assert status == 'loaned'
    
    u = get_device_unit_by_id(unit_ok['id'])
    print(f"Unit Status in DB: {u['status']}")
    assert u['status'] == 'loaned'
    
    # Test 2: Block Loan on Loaned Unit
    print("\n[Test 2] Block Loan on Loaned Unit...")
    try:
        process_loan(
            device_unit_id=unit_ok['id'],
            checkout_date="2024-01-02",
            destination="Hospital B",
            purpose="Demo",
            check_results=results_ok,
            photo_dir="test_photos_2",
            user_name="Tester"
        )
        print("ERROR: Allowed loan on loaned unit!")
    except ValueError as e:
        print(f"Success: Blocked with error: {e}")
        
    # Test 3: NG Loan -> Needs Attention
    print("\n[Test 3] Process NG Loan...")
    results_ng = [
        {'item_id': item1, 'name': 'Item 1', 'required_qty': 1, 'result': 'OK'},
        {'item_id': item2, 'name': 'Item 2', 'required_qty': 2, 'result': 'NG', 'ng_reason': '破損', 'comment': 'Broken'}
    ]
    
    status_ng = process_loan(
        device_unit_id=unit_ng['id'],
        checkout_date="2024-01-01",
        destination="Hospital C",
        purpose="Repair",
        check_results=results_ng,
        photo_dir="test_photos_ng",
        user_name="Tester"
    )
    
    print(f"Result Status: {status_ng}")
    assert status_ng == 'needs_attention'
    
    u_ng = get_device_unit_by_id(unit_ng['id'])
    print(f"Unit Status in DB: {u_ng['status']}")
    assert u_ng['status'] == 'needs_attention'
    
    issues = get_open_issues(unit_ng['id'])
    print(f"Open Issues: {len(issues)}")
    assert len(issues) > 0
    print(f"Issue Summary: {issues[0]['summary']}")

    # Test 4: Block Loan on Needs Attention Unit
    print("\n[Test 4] Block Loan on Unit with Issues...")
    try:
        process_loan(
            device_unit_id=unit_ng['id'],
            checkout_date="2024-01-02",
            destination="Hospital D",
            purpose="Demo",
            check_results=results_ok,
            photo_dir="test_photos_retry",
            user_name="Tester"
        )
        print("ERROR: Allowed loan on needs_attention unit!")
    except ValueError as e:
        print(f"Success: Blocked with error: {e}")

    print("\n--- Phase 2 Verification Completed Successfully ---")

if __name__ == "__main__":
    verify()
