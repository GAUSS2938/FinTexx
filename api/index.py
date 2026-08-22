import os
import re
import math
import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Response, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = "/tmp/finance_companion.db" if IS_VERCEL else os.path.join(os.path.dirname(BASE_DIR), "finance_companion.db")

_db_initialized = False

def get_db_connection():
    global _db_initialized
    if not _db_initialized or not os.path.exists(DB_FILE):
        try:
            init_db()
            seed_demo_data()
            _db_initialized = True
        except Exception as e:
            print(f"Database init warning: {e}")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_FILE)), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT, sms_permission INTEGER DEFAULT 1, knowledge_level TEXT NOT NULL, risk_comfort TEXT NOT NULL, created_at TEXT NOT NULL);")
    cursor.execute("CREATE TABLE IF NOT EXISTS financial_profiles (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, monthly_income REAL NOT NULL, essential_expenses REAL NOT NULL, flexible_expenses REAL NOT NULL, current_savings REAL NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));")
    cursor.execute("CREATE TABLE IF NOT EXISTS savings_goals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, target_amount REAL NOT NULL, current_amount REAL NOT NULL, deadline_months INTEGER NOT NULL, monthly_target REAL NOT NULL, status TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));")
    cursor.execute("CREATE TABLE IF NOT EXISTS budget_caps (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, category TEXT NOT NULL, monthly_cap REAL NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));")
    cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL, merchant TEXT NOT NULL, raw_text TEXT, date TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));")
    cursor.execute("CREATE TABLE IF NOT EXISTS learning_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, level INTEGER NOT NULL, topic TEXT NOT NULL, content TEXT NOT NULL, is_recommended INTEGER DEFAULT 0);")
    cursor.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, title TEXT NOT NULL, due_date TEXT NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));")
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "phone" not in existing_cols: cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "sms_permission" not in existing_cols: cursor.execute("ALTER TABLE users ADD COLUMN sms_permission INTEGER DEFAULT 1")
    conn.commit()
    conn.close()

def seed_demo_data():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cursor.execute("INSERT INTO users (name, phone, sms_permission, knowledge_level, risk_comfort, created_at) VALUES ('Ananya', '+91 98765 43210', 1, 'beginner', 'low', ?)", (now,))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO financial_profiles (user_id, monthly_income, essential_expenses, flexible_expenses, current_savings, updated_at) VALUES (?, 15000.0, 7000.0, 4500.0, 10000.0, ?)", (user_id, now))
        cursor.execute("INSERT INTO savings_goals (user_id, title, target_amount, current_amount, deadline_months, monthly_target, status) VALUES (?, 'Laptop', 40000.0, 10000.0, 6, 5000.0, 'tight_budget')", (user_id,))
        caps = [(user_id, 'Food', 5000.0, now), (user_id, 'Travel', 2500.0, now), (user_id, 'Shopping', 2000.0, now), (user_id, 'Subscriptions', 500.0, now), (user_id, 'Education', 1500.0, now)]
        cursor.executemany("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", caps)
        transactions = [(user_id, 'Food', 4200.0, 'Swiggy & Campus Cafe', 'Auto-tracked via UPI SMS', now), (user_id, 'Travel', 1800.0, 'Uber & Metro', 'Auto-tracked via UPI SMS', now), (user_id, 'Shopping', 1200.0, 'Amazon Books & Clothes', 'Auto-tracked via UPI SMS', now), (user_id, 'Subscriptions', 300.0, 'Spotify Student', 'Auto-tracked via UPI SMS', now)]
        cursor.executemany("INSERT INTO transactions (user_id, category, amount, merchant, raw_text, date) VALUES (?, ?, ?, ?, ?, ?)", transactions)
        modules = [('Emergency Funds 101', 1, 'Savings', 'An emergency fund covers 3-6 months of expenses before you begin investing. Keep this liquid in a high-yield savings account or flexible FD.', 1), ('Budgeting with 50/30/20', 1, 'Budgeting', 'Allocate 50% of your income to needs (rent, groceries, books), 30% to wants (dining, fun), and 20% directly to savings before you spend.', 0), ('What is a Mutual Fund SIP?', 2, 'Investing', 'Systematic Investment Plans let you invest small, fixed amounts monthly (e.g. ₹500/mo) into diversified index funds for long-term growth.', 0), ('Power of Compound Interest', 2, 'Growth', 'Starting at age 18-20 gives your money decades to compound exponentially. Time in the market beats timing the market every single time.', 0)]
        cursor.executemany("INSERT INTO learning_modules (title, level, topic, content, is_recommended) VALUES (?, ?, ?, ?, ?)", modules)
        tasks = [(user_id, 'Save ₹3,750 this month for Laptop goal', 'This Month', 'pending', 'goal'), (user_id, 'Read: Emergency Funds 101', 'This Week', 'pending', 'learning'), (user_id, 'Review food category cap (currently ₹4,200/₹5,000)', 'This Sunday', 'pending', 'ai_companion')]
        cursor.executemany("INSERT INTO tasks (user_id, title, due_date, status, source) VALUES (?, ?, ?, ?, ?)", tasks)
        conn.commit()
    conn.close()

class MathEngine:
    @staticmethod
    def calculate_savings_pacing(income: float, essentials: float, target_amount: float, current_savings: float, deadline_months: int):
        flexible_capacity = max(0.0, income - essentials)
        amount_needed = max(0.0, target_amount - current_savings)
        monthly_target = amount_needed / max(1, deadline_months)
        is_realistic = monthly_target <= (flexible_capacity * 0.75) if flexible_capacity > 0 else False
        recommended_months = deadline_months
        adjusted_target = monthly_target
        if not is_realistic and flexible_capacity > 0:
            recommended_months = math.ceil(amount_needed / (flexible_capacity * 0.6)) if flexible_capacity > 0 else 12
            adjusted_target = amount_needed / max(1, recommended_months)
        return {"flexible_capacity": flexible_capacity, "amount_needed": amount_needed, "monthly_target": round(monthly_target, 2), "is_realistic": is_realistic, "recommended_months": recommended_months, "adjusted_monthly_target": round(adjusted_target, 2)}

class SMSParser:
    MERCHANT_CATEGORIES = {"swiggy": "Food", "zomato": "Food", "uber": "Travel", "ola": "Travel", "amazon": "Shopping", "flipkart": "Shopping", "spotify": "Subscriptions", "netflix": "Subscriptions"}
    @classmethod
    def parse(cls, sms_text: str) -> Dict[str, Any]:
        amount_match = re.search(r'(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)', sms_text, re.IGNORECASE)
        type_match = "DEBIT" if re.search(r'\b(debited|spent|paid|sent|transfer to|vpa|withdrawn)\b', sms_text, re.IGNORECASE) else "CREDIT"
        merchant_match = re.search(r'(?:to|at|vpa|for)\s+([A-Za-z0-9\s._&]+?)(?:\s+on|\s+ref|\s+upi|\.|\,|$)', sms_text, re.IGNORECASE)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
        merchant = merchant_match.group(1).strip() if merchant_match else "UPI Merchant"
        category = "Other"
        for key, cat in cls.MERCHANT_CATEGORIES.items():
            if key in merchant.lower() or key in sms_text.lower():
                category = cat; break
        return {"amount": amount, "transaction_type": type_match, "merchant": merchant, "category": category, "parsed_by": "deterministic_regex", "raw_text": sms_text}

class ContextBuilder:
    @staticmethod
    def build_user_context(user_id: int = 1) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        user = dict(user_row) if user_row else {"name": "Ananya", "phone": "+91 98765 43210", "knowledge_level": "beginner", "risk_comfort": "low"}
        cursor.execute("SELECT * FROM financial_profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        profile_row = cursor.fetchone()
        profile = dict(profile_row) if profile_row else {"monthly_income": 15000.0, "essential_expenses": 7000.0, "current_savings": 10000.0}
        cursor.execute("SELECT * FROM savings_goals WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        goal_row = cursor.fetchone()
        goal = dict(goal_row) if goal_row else {"title": "Laptop", "target_amount": 40000.0, "current_amount": 10000.0, "deadline_months": 6, "monthly_target": 5000.0, "status": "active"}
        cursor.execute("SELECT category, SUM(amount) as total FROM transactions WHERE user_id = ? GROUP BY category", (user_id,))
        spending = [{"category": row["category"], "amount": float(row["total"])} for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM budget_caps WHERE user_id = ?", (user_id,))
        caps = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,))
        tasks = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM learning_modules WHERE is_recommended = 1 LIMIT 1")
        rec_row = cursor.fetchone()
        rec_module = dict(rec_row) if rec_row else {"title": "Emergency Funds 101"}
        conn.close()
        income = profile.get("monthly_income", 15000.0)
        essentials = profile.get("essential_expenses", 7000.0)
        flexible_room = max(0.0, income - essentials)
        return {
            "user_profile": {"name": user.get("name", "Student"), "phone": user.get("phone", ""), "monthly_income": income, "essential_expenses": essentials, "flexible_room": flexible_room, "current_savings": profile.get("current_savings", 10000.0), "knowledge_level": user.get("knowledge_level", "beginner"), "risk_comfort": user.get("risk_comfort", "low")},
            "active_goal": goal, "recent_spending": spending, "budget_caps": caps, "tasks": tasks, "learning_recommendation": rec_module.get("title", "Emergency Funds 101")
        }

def execute_mentor_tool(tool_name: str, arguments: dict, user_id: int = 1) -> tuple[str, dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    action_info = {}
    if tool_name == "add_task":
        title = arguments.get("title", "New Task").strip()
        due_date = arguments.get("due_date", "This Week")
        cursor.execute("INSERT INTO tasks (user_id, title, due_date, status, source) VALUES (?, ?, ?, 'pending', 'mentor_ai')", (user_id, title, due_date))
        task_id = cursor.lastrowid
        conn.commit()
        action_info = {"type": "task_added", "task_id": task_id, "title": title, "due_date": due_date}
        res_str = f"Task '{title}' added to checklist with ID #{task_id} (Due: {due_date})."
    elif tool_name == "set_budget_cap":
        category = arguments.get("category", "Food").capitalize()
        cap = float(arguments.get("monthly_cap", 5000.0))
        cursor.execute("SELECT id FROM budget_caps WHERE user_id = ? AND category = ?", (user_id, category))
        row = cursor.fetchone()
        if row: cursor.execute("UPDATE budget_caps SET monthly_cap = ?, updated_at = ? WHERE id = ?", (cap, now, row["id"]))
        else: cursor.execute("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", (user_id, category, cap, now))
        conn.commit()
        action_info = {"type": "budget_cap_updated", "category": category, "monthly_cap": cap}
        res_str = f"Monthly budget cap for {category} set to ₹{cap:,.0f}."
    elif tool_name == "update_profile":
        cursor.execute("SELECT * FROM financial_profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        prof = dict(cursor.fetchone() or {"monthly_income": 15000.0, "essential_expenses": 7000.0, "current_savings": 10000.0})
        income = float(arguments.get("monthly_income", prof["monthly_income"]))
        essentials = float(arguments.get("essential_expenses", prof["essential_expenses"]))
        savings = float(arguments.get("current_savings", prof["current_savings"]))
        flexible = max(0.0, income - essentials)
        cursor.execute("UPDATE financial_profiles SET monthly_income = ?, essential_expenses = ?, flexible_expenses = ?, current_savings = ?, updated_at = ? WHERE user_id = ?", (income, essentials, flexible * 0.5, savings, now, user_id))
        conn.commit()
        action_info = {"type": "profile_updated", "monthly_income": income, "essential_expenses": essentials, "flexible_room": flexible, "current_savings": savings}
        res_str = f"Profile updated: Income ₹{income:,.0f}, Essentials ₹{essentials:,.0f}."
    else: res_str = "Done"
    conn.close()
    return res_str, action_info

async def query_llm_mentor(user_message: str, context: Dict[str, Any], user_id: int = 1) -> tuple[str, list[dict]]:
    profile = context["user_profile"]
    goal = context["active_goal"]
    msg_raw = user_message.strip()
    msg_lower = msg_raw.lower()
    if any(k in msg_lower for k in ["afford", "can i buy", "can i spend"]):
        amt_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d,]+)', msg_lower)
        cost = float(amt_match.group(1).replace(",", "")) if amt_match else 1500.0
        remaining_flex = profile['flexible_room']
        laptop_monthly = goal.get('monthly_target', 5000.0)
        cushion = max(0.0, remaining_flex - laptop_monthly)
        can_afford = cost <= cushion
        if can_afford: return f"**Yes, you can afford this purchase of ₹{cost:,.0f}!** Remaining cushion: ₹{cushion - cost:,.0f}.", []
        else: return f"**This purchase of ₹{cost:,.0f} will strain your budget.** Safe cushion is ₹{cushion:,.0f}.", []
    return f"I am your AI Financial Mentor! Your current flexible room is ₹{profile['flexible_room']:,.0f} and savings goal is {goal.get('title', 'Laptop')}.", []

app = FastAPI(title="FinTex Backend", version="4.7.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class LoginRequest(BaseModel):
    name: str = "Ananya"
    phone: str = "+91 98765 43210"
    sms_permission: bool = True

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1

class TaskCreateRequest(BaseModel):
    title: str
    due_date: Optional[str] = "This Week"
    source: Optional[str] = "manual"
    user_id: Optional[int] = 1

class BudgetCapRequest(BaseModel):
    user_id: Optional[int] = 1
    category: str
    monthly_cap: float

# Master Router mounted on both "" and "/api"
api = APIRouter()

@api.get("/health")
@api.get("/api/health")
def health_endpoint():
    return {"status": "ok", "service": "FinTex Inbuilt AI Mentor", "version": "4.7.0"}

@api.post("/auth/login")
@api.post("/api/auth/login")
def login_user_endpoint(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE phone = ? LIMIT 1", (req.phone,))
    user = cursor.fetchone()
    if not user:
        now = datetime.now().isoformat()
        cursor.execute("INSERT INTO users (name, phone, sms_permission, knowledge_level, risk_comfort, created_at) VALUES (?, ?, ?, 'beginner', 'low', ?)", (req.name, req.phone, 1 if req.sms_permission else 0, now))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO financial_profiles (user_id, monthly_income, essential_expenses, flexible_expenses, current_savings, updated_at) VALUES (?, 15000.0, 7000.0, 4500.0, 10000.0, ?)", (user_id, now))
        cursor.execute("INSERT INTO savings_goals (user_id, title, target_amount, current_amount, deadline_months, monthly_target, status) VALUES (?, 'Laptop', 40000.0, 10000.0, 6, 5000.0, 'active')", (user_id,))
        caps = [(user_id, 'Food', 5000.0, now), (user_id, 'Travel', 2500.0, now), (user_id, 'Shopping', 2000.0, now), (user_id, 'Subscriptions', 500.0, now), (user_id, 'Education', 1500.0, now)]
        cursor.executemany("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", caps)
        conn.commit()
    else:
        user_id = user["id"]
    conn.close()
    return {"status": "authenticated", "user_id": user_id, "name": req.name, "phone": req.phone, "sms_sync_active": req.sms_permission}

@api.get("/dashboard/summary")
@api.get("/api/dashboard/summary")
def dashboard_endpoint(user_id: int = 1):
    context = ContextBuilder.build_user_context(user_id)
    profile = context["user_profile"]
    goal = context["active_goal"]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,))
    tasks = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM learning_modules ORDER BY level ASC")
    modules = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT c.category, c.monthly_cap, COALESCE(SUM(t.amount), 0) as spent FROM budget_caps c LEFT JOIN transactions t ON c.user_id = t.user_id AND c.category = t.category WHERE c.user_id = ? GROUP BY c.category", (user_id,))
    caps_with_spending = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 15", (user_id,))
    recent_transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {
        "financial_strip": {"name": profile["name"], "phone": profile.get("phone", ""), "monthly_income": profile["monthly_income"], "essential_expenses": profile["essential_expenses"], "flexible_room": profile["flexible_room"], "current_savings": profile["current_savings"], "ai_insight": f"Flexible Room: ₹{profile['flexible_room']:,.0f}"},
        "spending_categories": context["recent_spending"],
        "budget_caps": caps_with_spending,
        "recent_transactions": recent_transactions,
        "active_goal": goal,
        "learning_modules": modules,
        "tasks": tasks
    }

@api.post("/companion/chat")
@api.post("/api/companion/chat")
async def chat_endpoint(req: ChatRequest):
    context = ContextBuilder.build_user_context(req.user_id or 1)
    reply, actions = await query_llm_mentor(req.message, context, req.user_id or 1)
    return {"reply": reply, "actions_executed": actions, "suggested_tasks": ["Review Budget Caps"]}

@api.get("/transactions")
@api.get("/api/transactions")
def transactions_endpoint(user_id: int = 1, category: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if category and category != "All":
        cursor.execute("SELECT * FROM transactions WHERE user_id = ? AND category = ? ORDER BY id DESC", (user_id, category))
    else:
        cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"transactions": rows, "count": len(rows)}

@api.get("/tasks")
@api.get("/api/tasks")
def tasks_endpoint(user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"tasks": tasks}

@api.post("/tasks/{task_id}/toggle")
@api.post("/api/tasks/{task_id}/toggle")
def toggle_task_endpoint(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if row:
        new_status = "completed" if row["status"] == "pending" else "pending"
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        conn.commit()
    else:
        new_status = "pending"
    conn.close()
    return {"task_id": task_id, "new_status": new_status}

app.include_router(api)
