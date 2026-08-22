import sys
import httpx
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("Testing FinTex v3.0 Backend Endpoints...")
    
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health Check
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health failed: {res.status_code}"
        data = res.json()
        print(f"[OK] Health Check: {data['service']} v{data['version']}")
        assert data["status"] == "ok"
        assert "Autonomous-Mentor" in data["features"]

        # 2. Login Endpoint (Phone & SMS Permission)
        login_res = client.post("/api/auth/login", json={
            "name": "Ananya",
            "phone": "+91 98765 43210",
            "sms_permission": True
        })
        assert login_res.status_code == 200
        login_data = login_res.json()
        print(f"[OK] Auth Login: User ID={login_data['user_id']}, SMS Sync Active={login_data['sms_sync_active']}")
        assert login_data["status"] == "authenticated"

        # 3. Dashboard Summary with Budget Caps & Recent Transactions
        res = client.get("/api/dashboard/summary?user_id=1")
        assert res.status_code == 200
        data = res.json()
        print(f"[OK] Dashboard: User={data['financial_strip']['name']}, Income=Rs.{data['financial_strip']['monthly_income']}, Caps count={len(data['budget_caps'])}")
        assert len(data["budget_caps"]) > 0

        # 4. Budget Caps CRUD
        cap_res = client.post("/api/budget/caps", json={"user_id": 1, "category": "Food", "monthly_cap": 5500.0})
        assert cap_res.status_code == 200
        cap_data = cap_res.json()
        print(f"[OK] Budget Cap Updated: {cap_data['category']} -> Rs.{cap_data['monthly_cap']}")
        assert cap_data["monthly_cap"] == 5500.0

        # 5. Transactions Listing & Search
        tx_res = client.get("/api/transactions?user_id=1&category=Food")
        assert tx_res.status_code == 200
        tx_data = tx_res.json()
        print(f"[OK] Transactions Filter (Food): Found {tx_data['count']} transactions")

        # 6. Mentor Command: Set Budget Cap via Chat
        chat_res = client.post("/api/companion/chat", json={"message": "Set food budget cap to 4500", "user_id": 1})
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        print(f"\n--- Mentor Action: Set Budget Cap ---")
        print(f"Reply: {chat_data['reply']}")
        print(f"Actions Executed: {chat_data['actions_executed']}")
        assert len(chat_data["actions_executed"]) > 0
        assert chat_data["actions_executed"][0]["type"] == "budget_cap_updated"

        # 7. Mentor Command: Add Task via Chat
        chat_res2 = client.post("/api/companion/chat", json={"message": "Add task: Review Swiggy dining cap by Sunday", "user_id": 1})
        assert chat_res2.status_code == 200
        chat_data2 = chat_res2.json()
        print(f"\n--- Mentor Action: Add Task ---")
        print(f"Reply: {chat_data2['reply']}")
        assert len(chat_data2["actions_executed"]) > 0
        assert chat_data2["actions_executed"][0]["type"] == "task_added"

        # 8. Mentor Command: Retrieve Budget Status
        chat_res3 = client.post("/api/companion/chat", json={"message": "Show my budget status", "user_id": 1})
        assert chat_res3.status_code == 200
        chat_data3 = chat_res3.json()
        print(f"\n--- Mentor Query: Budget Status ---")
        print(chat_data3["reply"])

        # 9. SMS Auto-Ingest
        sms_res = client.post("/api/transactions/sms-ingest?user_id=1", json={
            "raw_sms": "Sent Rs. 380.00 from HDFC Bank to Swiggy on 22-08-2026 ref 492019 UPI"
        })
        assert sms_res.status_code == 200
        sms_data = sms_res.json()
        print(f"\n[OK] Auto-Sync SMS Ingest: {sms_data['alert']}")
        assert sms_data["parsed_transaction"]["amount"] == 380.0

    print("\n=======================================================")
    print(" ALL FINTEX V3.0 BACKEND TESTS PASSED SUCCESSFULLY! ")
    print("=======================================================")

if __name__ == "__main__":
    test_all()
