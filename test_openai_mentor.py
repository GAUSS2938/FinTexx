import sys
import httpx
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def test_openai_mentor():
    print("Testing OpenAI Inbuilt Mentor Dynamic Responses & Function Calling...")
    
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        # 1. Health check
        res = client.get("/api/health")
        assert res.status_code == 200
        print(f"[OK] Health: {res.json()['llm_engine']}")

        # 2. General / Open-ended Financial Query
        print("\n--- Testing Open-Ended Question 1: College Credit Building ---")
        res1 = client.post("/api/companion/chat", json={
            "message": "I am a college student. How can I start building credit without getting into bad debt?",
            "user_id": 1
        })
        assert res1.status_code == 200
        data1 = res1.json()
        print(data1["reply"])

        # 3. Dynamic Tool Calling: Set Budget Cap via Natural Language
        print("\n--- Testing Tool Execution 1: Set Budget Cap ---")
        res2 = client.post("/api/companion/chat", json={
            "message": "Please set my monthly Food budget cap to 4200 rupees.",
            "user_id": 1
        })
        assert res2.status_code == 200
        data2 = res2.json()
        print(f"Reply: {data2['reply']}")
        print(f"Actions Executed: {data2['actions_executed']}")
        assert len(data2["actions_executed"]) > 0

        # 4. Dynamic Tool Calling: Add Action Task
        print("\n--- Testing Tool Execution 2: Add Action Task ---")
        res3 = client.post("/api/companion/chat", json={
            "message": "Add a task for me: Check my campus cafe spending by this Friday",
            "user_id": 1
        })
        assert res3.status_code == 200
        data3 = res3.json()
        print(f"Reply: {data3['reply']}")
        print(f"Actions Executed: {data3['actions_executed']}")
        assert len(data3["actions_executed"]) > 0

        # 5. Open-ended Query: Custom Meal Planning vs Flexible Room
        print("\n--- Testing Open-Ended Question 2: Personalized Financial Assessment ---")
        res4 = client.post("/api/companion/chat", json={
            "message": "Can I afford to go out for a dinner with friends costing ₹1,500 this weekend based on my income and active goals?",
            "user_id": 1
        })
        assert res4.status_code == 200
        data4 = res4.json()
        print(data4["reply"])

    print("\n=======================================================")
    print(" OPENAI INBUILT MENTOR TEST PASSED SUCCESSFULLY! ")
    print("=======================================================")

if __name__ == "__main__":
    test_openai_mentor()
