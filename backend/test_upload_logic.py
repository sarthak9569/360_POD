import os
import sys
import io
import pandas as pd
from fastapi.testclient import TestClient

# Add current dir to path to import main
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from main import app, beneficiaries_collection
import asyncio
import json

client = TestClient(app)

def run_tests():
    # 1. Create a mock Excel file covering all cases
    data = {
        "S.No.": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "Tag No.": [
            "T1", "T2", "T1", # Repeated valid (T1 has 2 dists)
            "T3", # Existing, should reuse
            "", # Missing tag -> skip
            "T4", "T5", "T6", "T7", 
            "T8", 
            "T9" # Identity mismatch
        ],
        "Beneficiary Name": [
            "John", "Alice", "John", 
            "Bob", 
            "Invalid",
            "MissingQty", "ZeroQty", "DashQty", "TextQty",
            "NewGuy", 
            "IdentityMismatch"
        ],
        "Father/Husband Name": ["F1", "F2", "F1", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"],
        "Village": ["V1", "V2", "V1", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"],
        "District": ["Kondagaon", "Mahasamund", "Kondagaon", "Kanker", "Balrampur", "Sharangarh", "Kondagaon", "Kondagaon", "Kondagaon", "Kondagaon", "Kondagaon"],
        "Cattle Feed (kg)": [
            100, 50, 75,
            200,
            10,
            None, 0, "-", "invalid_text",
            100,
            100
        ],
        "Silage (kg)": [
            50, 20, 30,
            100,
            20,
            "", 0, "-", "more_text",
            50,
            50
        ]
    }
    df = pd.DataFrame(data)
    
    # Save to bytes
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False)
    excel_io.seek(0)
    
    # Setup test DB state
    loop = asyncio.get_event_loop()
    loop.run_until_complete(beneficiaries_collection.delete_many({}))
    
    # Seed T3 and T9
    loop.run_until_complete(beneficiaries_collection.insert_one({
        "tag_no": "T3",
        "farmer_name": "Bob",
        "village": "V3",
        "cattle_feed_kg": 50,
        "silage_kg": 50,
        "distributions": []
    }))
    loop.run_until_complete(beneficiaries_collection.insert_one({
        "tag_no": "T9",
        "farmer_name": "RealName",
        "village": "RealVillage",
        "cattle_feed_kg": 0,
        "silage_kg": 0,
        "distributions": []
    }))
    
    print("=== FIRST UPLOAD ===")
    response = client.post("/api/beneficiaries/upload", files={"file": ("test.xlsx", excel_io.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    print(json.dumps(response.json(), indent=2))
    
    print("\n=== VERIFY DB STATE ===")
    t1 = loop.run_until_complete(beneficiaries_collection.find_one({"tag_no": "T1"}))
    print(f"T1 total cattle_feed_kg: {t1.get('cattle_feed_kg')} (expected 175)")
    print(f"T1 distributions count: {len(t1.get('distributions', []))} (expected 2)")
    
    t3 = loop.run_until_complete(beneficiaries_collection.find_one({"tag_no": "T3"}))
    print(f"T3 total cattle_feed_kg: {t3.get('cattle_feed_kg')} (expected 250)")
    
    print("\n=== SECOND UPLOAD (EXACT SAME FILE) ===")
    response2 = client.post("/api/beneficiaries/upload", files={"file": ("test.xlsx", excel_io.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    print(json.dumps(response2.json(), indent=2))

if __name__ == "__main__":
    run_tests()
