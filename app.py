import os
import re
import math
import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
import uvicorn
import httpx

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if IS_VERCEL:
    DB_FILE = "/tmp/finance_companion.db"
else:
    DB_FILE = os.path.join(BASE_DIR, "finance_companion.db")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Static directory resolution
STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    STATIC_DIR = os.path.join(BASE_DIR, "..", "static")
if not os.path.exists(STATIC_DIR):
    STATIC_DIR = os.path.abspath("static")

# ==========================================
# DATABASE SETUP & INITIALIZATION
# ==========================================
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
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        sms_permission INTEGER DEFAULT 1,
        knowledge_level TEXT NOT NULL,
        risk_comfort TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        monthly_income REAL NOT NULL,
        essential_expenses REAL NOT NULL,
        flexible_expenses REAL NOT NULL,
        current_savings REAL NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL NOT NULL,
        deadline_months INTEGER NOT NULL,
        monthly_target REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budget_caps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        monthly_cap REAL NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        merchant TEXT NOT NULL,
        raw_text TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS learning_modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        level INTEGER NOT NULL,
        topic TEXT NOT NULL,
        content TEXT NOT NULL,
        is_recommended INTEGER DEFAULT 0
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL,
        source TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    
    # Auto-migration for users table columns
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "phone" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "sms_permission" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN sms_permission INTEGER DEFAULT 1")
    
    conn.commit()
    conn.close()

# ==========================================
# SEED DEMO DATA (ANANYA'S STORYLINE)
# ==========================================
def seed_demo_data():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        
        # User: Ananya (College Student, 20)
        cursor.execute("""
        INSERT INTO users (name, phone, sms_permission, knowledge_level, risk_comfort, created_at)
        VALUES ('Ananya', '+91 98765 43210', 1, 'beginner', 'low', ?)
        """, (now,))
        user_id = cursor.lastrowid
        
        # Financial Profile (Income: 15,000, Essentials: 7,000, Flexible: 4,500, Savings: 10,000)
        cursor.execute("""
        INSERT INTO financial_profiles (user_id, monthly_income, essential_expenses, flexible_expenses, current_savings, updated_at)
        VALUES (?, 15000.0, 7000.0, 4500.0, 10000.0, ?)
        """, (user_id, now))
        
        # Goal: Laptop (₹40,000 target, ₹10,000 saved, 6 months)
        cursor.execute("""
        INSERT INTO savings_goals (user_id, title, target_amount, current_amount, deadline_months, monthly_target, status)
        VALUES (?, 'Laptop', 40000.0, 10000.0, 6, 5000.0, 'tight_budget')
        """, (user_id,))
        
        # Budget Caps
        caps = [
            (user_id, 'Food', 5000.0, now),
            (user_id, 'Travel', 2500.0, now),
            (user_id, 'Shopping', 2000.0, now),
            (user_id, 'Subscriptions', 500.0, now),
            (user_id, 'Education', 1500.0, now),
        ]
        cursor.executemany("""
        INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at)
        VALUES (?, ?, ?, ?)
        """, caps)
        
        # Recent Spending Transactions (Auto-synced via SMS)
        transactions = [
            (user_id, 'Food', 4200.0, 'Swiggy & Campus Cafe', 'Auto-tracked via UPI SMS', now),
            (user_id, 'Travel', 1800.0, 'Uber & Metro', 'Auto-tracked via UPI SMS', now),
            (user_id, 'Shopping', 1200.0, 'Amazon Books & Clothes', 'Auto-tracked via UPI SMS', now),
            (user_id, 'Subscriptions', 300.0, 'Spotify Student', 'Auto-tracked via UPI SMS', now),
        ]
        cursor.executemany("""
        INSERT INTO transactions (user_id, category, amount, merchant, raw_text, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, transactions)
        
        # Learning Modules (UN SDG 8.10 & 4.4 Financial Skills)
        modules = [
            ('Emergency Funds 101', 1, 'Savings', 'An emergency fund covers 3-6 months of expenses before you begin investing. Keep this liquid in a high-yield savings account or flexible FD.', 1),
            ('Budgeting with 50/30/20', 1, 'Budgeting', 'Allocate 50% of your income to needs (rent, groceries, books), 30% to wants (dining, fun), and 20% directly to savings before you spend.', 0),
            ('What is a Mutual Fund SIP?', 2, 'Investing', 'Systematic Investment Plans let you invest small, fixed amounts monthly (e.g. ₹500/mo) into diversified index funds for long-term growth.', 0),
            ('Power of Compound Interest', 2, 'Growth', 'Starting at age 18-20 gives your money decades to compound exponentially. Time in the market beats timing the market every single time.', 0),
        ]
        cursor.executemany("""
        INSERT INTO learning_modules (title, level, topic, content, is_recommended)
        VALUES (?, ?, ?, ?, ?)
        """, modules)
        
        # Action Tasks
        tasks = [
            (user_id, 'Save ₹3,750 this month for Laptop goal', 'This Month', 'pending', 'goal'),
            (user_id, 'Read: Emergency Funds 101', 'This Week', 'pending', 'learning'),
            (user_id, 'Review food category cap (currently ₹4,200/₹5,000)', 'This Sunday', 'pending', 'ai_companion')
        ]
        cursor.executemany("""
        INSERT INTO tasks (user_id, title, due_date, status, source)
        VALUES (?, ?, ?, ?, ?)
        """, tasks)
        
        conn.commit()
    conn.close()

# ==========================================
# ENGINES: MATH, SMS PARSER & CONTEXT
# ==========================================
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
            
        return {
            "flexible_capacity": flexible_capacity,
            "amount_needed": amount_needed,
            "monthly_target": round(monthly_target, 2),
            "is_realistic": is_realistic,
            "recommended_months": recommended_months,
            "adjusted_monthly_target": round(adjusted_target, 2)
        }

class SMSParser:
    MERCHANT_CATEGORIES = {
        "swiggy": "Food", "zomato": "Food", "chaayos": "Food", "mcdonalds": "Food", "canteen": "Food", "cafe": "Food", "starbucks": "Food", "blinkit": "Food", "zepto": "Food", "instamart": "Food", "eats": "Food", "kfc": "Food", "dominos": "Food", "pizza": "Food",
        "uber": "Travel", "ola": "Travel", "rapido": "Travel", "metro": "Travel", "irctc": "Travel", "redbus": "Travel", "fuel": "Travel", "petrol": "Travel",
        "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping", "zara": "Shopping", "h&m": "Shopping", "ajio": "Shopping", "meesho": "Shopping", "nykaa": "Shopping",
        "spotify": "Subscriptions", "netflix": "Subscriptions", "prime": "Subscriptions", "youtube": "Subscriptions", "apple": "Subscriptions", "hotstar": "Subscriptions",
        "udemy": "Education", "coursera": "Education", "college": "Education", "fees": "Education", "books": "Education", "tuition": "Education"
    }

    @classmethod
    def parse(cls, sms_text: str) -> Dict[str, Any]:
        amount_match = re.search(r'(?:Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)', sms_text, re.IGNORECASE)
        type_match = "DEBIT" if re.search(r'\b(debited|spent|paid|sent|transfer to|vpa|withdrawn)\b', sms_text, re.IGNORECASE) else "CREDIT"
        merchant_match = re.search(r'(?:to|at|vpa|for)\s+([A-Za-z0-9\s._&]+?)(?:\s+on|\s+ref|\s+upi|\.|\,|$)', sms_text, re.IGNORECASE)
        
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0
        merchant = merchant_match.group(1).strip() if merchant_match else "UPI Merchant"
        
        category = "Other"
        merchant_lower = merchant.lower()
        sms_lower = sms_text.lower()
        for key, cat in cls.MERCHANT_CATEGORIES.items():
            if key in merchant_lower or key in sms_lower:
                category = cat
                break
                
        return {
            "amount": amount,
            "transaction_type": type_match,
            "merchant": merchant,
            "category": category,
            "parsed_by": "deterministic_regex",
            "raw_text": sms_text
        }

class ContextBuilder:
    @staticmethod
    def build_user_context(user_id: int = 1) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        user = dict(user_row) if user_row else {
            "name": "Ananya", "phone": "+91 98765 43210", "knowledge_level": "beginner", "risk_comfort": "low"
        }
        
        cursor.execute("SELECT * FROM financial_profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        profile_row = cursor.fetchone()
        profile = dict(profile_row) if profile_row else {
            "monthly_income": 15000.0, "essential_expenses": 7000.0, "current_savings": 10000.0
        }
        
        cursor.execute("SELECT * FROM savings_goals WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        goal_row = cursor.fetchone()
        goal = dict(goal_row) if goal_row else {
            "title": "Laptop", "target_amount": 40000.0, "current_amount": 10000.0, "deadline_months": 6, "monthly_target": 5000.0, "status": "active"
        }
        
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
            "user_profile": {
                "name": user.get("name", "Student"),
                "phone": user.get("phone", ""),
                "monthly_income": income,
                "essential_expenses": essentials,
                "flexible_room": flexible_room,
                "current_savings": profile.get("current_savings", 10000.0),
                "knowledge_level": user.get("knowledge_level", "beginner"),
                "risk_comfort": user.get("risk_comfort", "low")
            },
            "active_goal": goal,
            "recent_spending": spending,
            "budget_caps": caps,
            "tasks": tasks,
            "learning_recommendation": rec_module.get("title", "Emergency Funds 101")
        }

# ==========================================
# TOOL EXECUTOR
# ==========================================
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

    elif tool_name == "delete_task":
        task_id = int(arguments.get("task_id", 0))
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        action_info = {"type": "task_deleted", "task_id": task_id}
        res_str = f"Task #{task_id} deleted."

    elif tool_name == "set_budget_cap":
        category = arguments.get("category", "Food").capitalize()
        cap = float(arguments.get("monthly_cap", 5000.0))
        cursor.execute("SELECT id FROM budget_caps WHERE user_id = ? AND category = ?", (user_id, category))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE budget_caps SET monthly_cap = ?, updated_at = ? WHERE id = ?", (cap, now, row["id"]))
        else:
            cursor.execute("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", (user_id, category, cap, now))
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
        res_str = f"Profile updated: Income ₹{income:,.0f}, Essentials ₹{essentials:,.0f}, Flexible Room ₹{flexible:,.0f}, Savings ₹{savings:,.0f}."

    elif tool_name == "set_goal":
        title = arguments.get("title", "Goal").strip().capitalize()
        target = float(arguments.get("target_amount", 40000.0))
        deadline = int(arguments.get("deadline_months", 6))

        cursor.execute("SELECT * FROM financial_profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        prof = dict(cursor.fetchone() or {"monthly_income": 15000.0, "essential_expenses": 7000.0, "current_savings": 10000.0})
        pacing = MathEngine.calculate_savings_pacing(prof["monthly_income"], prof["essential_expenses"], target, prof["current_savings"], deadline)

        cursor.execute("INSERT INTO savings_goals (user_id, title, target_amount, current_amount, deadline_months, monthly_target, status) VALUES (?, ?, ?, ?, ?, ?, 'active')", (user_id, title, target, prof["current_savings"], pacing["recommended_months"], pacing["adjusted_monthly_target"]))
        goal_id = cursor.lastrowid
        conn.commit()
        action_info = {"type": "goal_updated", "goal_id": goal_id, "title": title, "target_amount": target, "deadline_months": pacing["recommended_months"], "monthly_target": pacing["adjusted_monthly_target"], "is_realistic": pacing["is_realistic"]}
        res_str = f"Goal '{title}' saved with target ₹{target:,.0f}, monthly saving ₹{pacing['adjusted_monthly_target']:,.0f}/mo over {pacing['recommended_months']} months."
    else:
        res_str = "Unknown tool call"

    conn.close()
    return res_str, action_info

# ==========================================
# ADVANCED CONVERSATIONAL FINANCIAL NLU
# ==========================================
async def query_llm_mentor(user_message: str, context: Dict[str, Any], user_id: int = 1) -> tuple[str, list[dict]]:
    profile = context["user_profile"]
    goal = context["active_goal"]
    msg_raw = user_message.strip()
    msg_lower = msg_raw.lower()

    # 1. INTENT: WEBSITE ACTIONS & MUTATIONS
    task_add_match = re.search(r'(?:add\s+task|create\s+task|remind\s+me\s+to|add\s+a\s+task)\s*(?::\s*|\s+for\s+me\s*:\s*|\s+to\s+|\s+that\s+)?(.+)', msg_lower, re.IGNORECASE)
    if task_add_match:
        raw_title = task_add_match.group(1).strip()
        due_m = re.search(r'(?:by|due|for|on)\s+(sunday|monday|tuesday|wednesday|thursday|friday|saturday|this\s+friday|this\s+sunday|this\s+week|this\s+month|tomorrow|today)', raw_title, re.IGNORECASE)
        due_date = due_m.group(0).capitalize() if due_m else "This Week"
        clean_title = re.sub(r'\s+(?:by|due|for|on)\s+(?:sunday|monday|tuesday|wednesday|thursday|friday|saturday|this\s+friday|this\s+sunday|this\s+week|this\s+month|tomorrow|today)', '', raw_title, flags=re.IGNORECASE).strip()
        clean_title = re.sub(r'^(?:for me:\s*|to\s*)', '', clean_title, flags=re.IGNORECASE).strip().capitalize()
        res_str, act_info = execute_mentor_tool("add_task", {"title": clean_title, "due_date": due_date}, user_id)
        return f"✅ **Mentor Action Executed:** Added task **{clean_title}** (*Due: {due_date}*). It is now live on your checklist!", [act_info]

    cap_match = re.search(r'(?:set|update|change|cap|increase)\s+(?:my\s+|the\s+)?(?:monthly\s+|weekly\s+)?(food|travel|shopping|subscriptions|education|other)[a-z\s]*?\s+(?:to|=)\s*(?:rs\.?|inr|₹)?\s*([\d,]+)', msg_lower, re.IGNORECASE)
    if cap_match:
        cat = cap_match.group(1).capitalize()
        val = float(cap_match.group(2).replace(",", ""))
        res_str, act_info = execute_mentor_tool("set_budget_cap", {"category": cat, "monthly_cap": val}, user_id)
        return f"📊 **Mentor Action Executed:** Updated monthly **{cat} budget cap** to **₹{val:,.0f}**. Your Budget page is updated!", [act_info]

    inc_match = re.search(r'(?:update|change|set)\s+(?:my\s+)?(?:monthly\s+)?income\s+(?:to|=)\s*(?:rs\.?|inr|₹)?\s*([\d,]+)', msg_lower, re.IGNORECASE)
    if inc_match:
        val = float(inc_match.group(1).replace(",", ""))
        res_str, act_info = execute_mentor_tool("update_profile", {"monthly_income": val}, user_id)
        return f"⚡ **Mentor Action Executed:** Monthly income updated to **₹{val:,.0f}**. Flexible room recalculated to **₹{val - profile['essential_expenses']:,.0f}**.", [act_info]

    goal_match = re.search(r'(?:update|set|change|add|create|increase)\s+(?:my\s+)?(?:([A-Za-z\s]+?)\s+)?goal(?:\s+(?:for|to|of)\s+)?([A-Za-z\s]*?)\s*(?:target\s+to\s+|to\s+)?(?:rs\.?|inr|₹)?\s*([\d,]+)(?:\s+in\s+(\d+)\s+months?)?', msg_lower, re.IGNORECASE)
    if goal_match:
        title_cand = (goal_match.group(1) or goal_match.group(2) or "Laptop").strip().capitalize()
        if not title_cand or title_cand.lower() in ["the", "my", "to", "for", "a"]:
            title_cand = "Laptop"
        target_amt = float(goal_match.group(3).replace(",", ""))
        dead_m = int(goal_match.group(4)) if goal_match.group(4) else 6
        res_str, act_info = execute_mentor_tool("set_goal", {"title": title_cand, "target_amount": target_amt, "deadline_months": dead_m}, user_id)
        return f"🎯 **Mentor Action Executed:** Goal **{title_cand}** updated to **₹{target_amt:,.0f}** over **{dead_m} months**.", [act_info]

    # 2. TOPIC: INVESTING, STOCKS, CRYPTO, SIP, MUTUAL FUNDS
    if any(k in msg_lower for k in ["invest", "crypto", "bitcoin", "stock", "mutual fund", "sip", "nifty", "shares", "equity"]):
        emergency_needed = profile['essential_expenses'] * 3
        has_buffer = profile['current_savings'] >= emergency_needed
        if not has_buffer:
            return (
                f"Before investing in stocks or crypto, let's examine your foundational safety net:\n\n"
                f"* **Current Liquid Savings:** ₹{profile['current_savings']:,.0f}\n"
                f"* **Target 3-Month Emergency Buffer:** **₹{emergency_needed:,.0f}** (₹{profile['essential_expenses']:,.0f}/mo essentials × 3)\n\n"
                f"* **The Golden Rule for Students:** Never invest money you might need in the next 12-24 months. Crypto and equities are volatile. If an unexpected college emergency happens, you shouldn't be forced to sell at a loss.\n"
                f"* **Recommended Path:** First complete the **Emergency Funds 101** module and secure your ₹{emergency_needed:,.0f} buffer. Once that's safe, start with a ₹500/month index SIP."
            ), []
        else:
            return (
                f"Great news! Your **₹{profile['current_savings']:,.0f}** savings comfortably covers your **₹{emergency_needed:,.0f}** emergency buffer.\n\n"
                f"* **Recommended Starter Plan:** Begin with a **₹500 - ₹1,000/month SIP in a low-cost Nifty 50 / Sensex Index Fund**.\n"
                f"* **Why Index Funds?** They carry low expense ratios (<0.2%) and own India's top 50 companies, giving you instant diversification without the stress of stock picking.\n"
                f"* **Crypto Warning:** Keep high-risk speculative assets (like Bitcoin/Altcoins) under 5% of your total portfolio."
            ), []

    # 3. TOPIC: EMERGENCY FUND & FINANCIAL SAFETY NET
    if any(k in msg_lower for k in ["emergency", "safety net", "buffer", "liquid fund", "savings account"]):
        target = profile['essential_expenses'] * 3
        return (
            f"**How to Build an Emergency Fund as a Student/Young Adult:**\n\n"
            f"* **Your Target Number:** **₹{target:,.0f}** (3 months of your ₹{profile['essential_expenses']:,.0f} essential living costs).\n"
            f"* **Where to Keep It:** Keep this money in a separate high-yield savings account or a sweep-in Fixed Deposit (FD) so it is 100% liquid and earns 6-7% without market risk.\n"
            f"* **How to Fund It:** Divert **20% of your monthly flexible room (₹{profile['flexible_room'] * 0.2:,.0f}/mo)** directly into this fund on the 1st of every month before discretionary spending.\n"
            f"* **Check Dashboard:** The **Emergency Funds 101** module on your dashboard walks you through this step-by-step."
        ), []

    # 4. TOPIC: SPENDING BREAKDOWN & RECENT TRANSACTIONS
    if any(k in msg_lower for k in ["show my spend", "what did i spend", "spending on", "how much spent", "expenses breakdown", "my transactions", "recent spending"]):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category, SUM(amount) as total, COUNT(*) as count FROM transactions WHERE user_id = ? GROUP BY category", (user_id,))
        spending = cursor.fetchall()
        conn.close()
        if spending:
            breakdown_str = "\n".join([f"* **{row['category']}:** ₹{row['total']:,.0f} ({row['count']} transactions)" for row in spending])
            return f"📊 **Your Auto-Synced Monthly Spending Summary:**\n\n{breakdown_str}\n\n* **Details:** You can view the itemized ledger and filter by category on the **Expenses** tab.", []
        else:
            return "You haven't auto-synced any transactions yet. Your incoming bank SMS stream will populate this ledger automatically!", []

    # 5. TOPIC: AFFORDABILITY & DISCRETIONARY PURCHASES
    if any(k in msg_lower for k in ["afford", "can i buy", "can i spend", "should i buy", "trip", "dinner", "party", "movie", "shopping"]):
        amt_match = re.search(r'(?:rs\.?|inr|₹)?\s*([\d,]+)', msg_lower)
        cost = float(amt_match.group(1).replace(",", "")) if amt_match else 1500.0
        remaining_flex = profile['flexible_room']
        laptop_monthly = goal.get('monthly_target', 5000.0)
        cushion = max(0.0, remaining_flex - laptop_monthly)
        can_afford = cost <= cushion

        if can_afford:
            return (
                f"**Yes, you can afford this purchase of ₹{cost:,.0f}!** Here is the math:\n\n"
                f"* **Monthly Flexible Room:** ₹{remaining_flex:,.0f}\n"
                f"* **Allocated for {goal.get('title', 'Laptop')} Goal:** ₹{laptop_monthly:,.0f}/month\n"
                f"* **Discretionary Cushion Available:** **₹{cushion:,.0f}**\n"
                f"* **Proposed Expense:** ₹{cost:,.0f}\n\n"
                f"After this expense, you will still have **₹{cushion - cost:,.0f}** left over without compromising your savings goal timeline."
            ), []
        else:
            return (
                f"**This purchase of ₹{cost:,.0f} will strain your budget.** Here is why:\n\n"
                f"* **Monthly Flexible Room:** ₹{remaining_flex:,.0f}\n"
                f"* **Goal Saving Requirement:** ₹{laptop_monthly:,.0f}/mo\n"
                f"* **Available Discretionary Cushion:** **₹{cushion:,.0f}**\n\n"
                f"* **Mentor Recommendation:** Spending ₹{cost:,.0f} exceeds your safe cushion. Consider limiting this expense to **₹{cushion * 0.5:,.0f}** or extending your goal deadline by 1-2 months."
            ), []

    # 6. TOPIC: COMPOUND INTEREST & WEALTH ACCUMULATION
    if any(k in msg_lower for k in ["compound", "compounding", "interest", "rule of 72", "wealth", "time value"]):
        return (
            f"**The Power of Compound Interest for College Students:**\n\n"
            f"* **How It Works:** Compound interest means earning return on both your original money AND on previously accumulated gains ($A = P(1 + r/n)^{{nt}}$).\n"
            f"* **The Rule of 72:** Divide 72 by your annual expected return (e.g. 12% in index funds) to see when your money doubles: $72 / 12 = 6$ years!\n"
            f"* **The Cost of Waiting:** If you invest **₹1,000/month** starting at age 20 (earning 12%), by age 50 you will have over **₹35.3 Lakhs**. If you delay until age 30, you end up with only **₹9.9 Lakhs** — starting 10 years earlier yields nearly 4x more wealth with minimal effort!"
        ), []

    # 7. TOPIC: CREDIT CARDS & CIBIL SCORE BUILDING
    if any(k in msg_lower for k in ["credit", "cibil", "score", "debt", "loan", "card", "emi", "bnpl"]):
        return (
            f"**Smart Credit Building Strategy for Students (Zero Debt Traps):**\n\n"
            f"* **1. Get a Secured FD-Backed Credit Card:** Place a ₹5,000-₹10,000 deposit at your bank to get a card without salary slips.\n"
            f"* **2. The 30% Utilization Rule:** If your limit is ₹10,000, never spend more than **₹3,000/month**. This proves credit discipline to CIBIL and Experian.\n"
            f"* **3. Always Pay the Full Bill (Not Minimum Due):** 'Minimum Due' triggers 36-42% interest rates. Enable auto-debit for 100% total due.\n"
            f"* **4. Beware of BNPL Micro-Loans:** Quick checkout loan apps report missed ₹200 payments as loan defaults, ruining your credit score for years."
        ), []

    # 8. TOPIC: BUDGETING & 50/30/20 RULE
    if any(k in msg_lower for k in ["budget", "50/30/20", "allocat", "cap", "needs", "wants"]):
        needs = profile['monthly_income'] * 0.5
        wants = profile['monthly_income'] * 0.3
        savings = profile['monthly_income'] * 0.2
        return (
            f"**The 50/30/20 Budgeting Rule for Your ₹{profile['monthly_income']:,.0f} Income:**\n\n"
            f"* **Needs (50% = ₹{needs:,.0f}):** Rent, groceries, campus transit, basic utilities.\n"
            f"* **Wants (30% = ₹{wants:,.0f}):** Dining out, entertainment, shopping, subscriptions.\n"
            f"* **Savings (20% = ₹{savings:,.0f}):** Direct transfer into your {goal.get('title', 'Laptop')} savings or emergency buffer.\n\n"
            f"You can view and adjust your category caps with live danger meters on the **Budget** tab."
        ), []

    # 9. GREETINGS & INTRODUCTIONS
    if any(k in msg_lower for k in ["hello", "hi", "hey", "who are you", "what can you do", "help"]):
        return (
            f"Hello {profile.get('name', 'Ananya')}! 👋 I am your **Inbuilt AI Financial Mentor**.\n\n"
            f"Here is how I assist you in real time:\n"
            f"* **Auto-Tracking:** Continuously reading UPI & bank SMS alerts against your **₹{profile['monthly_income']:,.0f}** income.\n"
            f"* **Goal Protection:** Keeping you on pace to buy your **{goal.get('title', 'Laptop')} (₹{goal.get('target_amount', 40000):,.0f})**.\n"
            f"* **Executing Actions:** You can prompt me to *'Set food cap to 4500'*, *'Add task: Review Swiggy'*, or *'Update income to 18000'*.\n"
            f"* **Guidance:** Ask me about compounding, credit building, emergency buffers, or whether you can afford an outing!"
        ), []

    # 10. GENERAL CONVERSATION
    return (
        f"Here is my guidance on **'{msg_raw}'** based on your financial standing:\n\n"
        f"* **Current Position:** Monthly Income ₹{profile['monthly_income']:,.0f} • Flexible Room ₹{profile['flexible_room']:,.0f} • Savings ₹{profile['current_savings']:,.0f}.\n"
        f"* **Active Priority:** Protect your **{goal.get('title', 'Laptop')} goal (₹{goal.get('monthly_target', 5000):,.0f}/mo)** by maintaining your category spending caps.\n"
        f"* **Mentor Pro-Tip:** You can ask me specific questions like *'How does compounding work?'*, *'How do I build an emergency fund?'*, or command me to *'Set travel cap to 3000'*!"
    ), []

# ==========================================
# FASTAPI APPLICATION & ROUTING
# ==========================================
app = FastAPI(
    title="FinTex Inbuilt Mentor & Auto-Sync Backend",
    description="UN SDG 8.10 & 4.4 Financial Literacy, Auto-Synced SMS Ledger & Autonomous Inbuilt Mentor with Dynamic NLU Intelligence",
    version="4.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vercel Path Normalization Middleware
@app.middleware("http")
async def vercel_path_normalizer(request: Request, call_next):
    # Check for original requested path forwarded by Vercel
    orig_path = request.headers.get("x-matched-path") or request.headers.get("x-vercel-matched-path") or request.headers.get("x-forwarded-uri") or request.headers.get("x-invoke-path")
    if orig_path and not orig_path.startswith("/api/index.py"):
        request.scope["path"] = orig_path
    else:
        path = request.scope.get("path", "")
        if path.startswith("/api/index.py"):
            subpath = path[len("/api/index.py"):]
            request.scope["path"] = subpath if (subpath and subpath.startswith("/")) else ("/" + subpath if subpath else "/")
        elif path.startswith("/api/index"):
            subpath = path[len("/api/index"):]
            request.scope["path"] = subpath if (subpath and subpath.startswith("/")) else ("/" + subpath if subpath else "/")
    
    response = await call_next(request)
    return response

# Explicit static file routes with direct string reading for Vercel Serverless reliability
@app.get("/static/style.css", include_in_schema=False)
@app.get("/api/index.py/static/style.css", include_in_schema=False)
def get_css():
    css_path = os.path.join(STATIC_DIR, "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/css")
    return Response(content="/* CSS */", media_type="text/css")

@app.get("/static/app.js", include_in_schema=False)
@app.get("/api/index.py/static/app.js", include_in_schema=False)
def get_js():
    js_path = os.path.join(STATIC_DIR, "app.js")
    if os.path.exists(js_path):
        with open(js_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="application/javascript")
    return Response(content="// JS", media_type="application/javascript")

if os.path.exists(STATIC_DIR):
    try:
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    except Exception:
        pass

@app.get("/", include_in_schema=False)
@app.get("/api/index.py", include_in_schema=False)
@app.get("/api/index", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
def get_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>FinTex is running. Please check /docs</h1>")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

class LoginRequest(BaseModel):
    name: str = "Ananya"
    phone: str = "+91 98765 43210"
    sms_permission: bool = True

class GoalCalculateRequest(BaseModel):
    target_amount: float
    deadline_months: int
    current_savings: Optional[float] = 10000.0
    monthly_income: Optional[float] = 15000.0
    essential_expenses: Optional[float] = 7000.0

class SMSIngestRequest(BaseModel):
    raw_sms: str

class BatchSMSIngestRequest(BaseModel):
    sms_list: List[str]

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = 1
    history: Optional[List[Dict[str, str]]] = None

class TaskCreateRequest(BaseModel):
    title: str
    due_date: Optional[str] = "This Week"
    source: Optional[str] = "manual"
    user_id: Optional[int] = 1

class ProfileUpdateRequest(BaseModel):
    user_id: Optional[int] = 1
    monthly_income: float
    essential_expenses: float
    current_savings: float

class GoalCreateRequest(BaseModel):
    user_id: Optional[int] = 1
    title: str
    target_amount: float
    deadline_months: int

class BudgetCapRequest(BaseModel):
    user_id: Optional[int] = 1
    category: str
    monthly_cap: float

# ==========================================
# API ROUTERS
# ==========================================
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "FinTex AI Financial Companion & Inbuilt Mentor",
        "version": "4.3.0",
        "sdg": ["SDG 8.10", "SDG 4.4"],
        "llm_engine": "Comprehensive-Conversational-NLU",
        "features": ["Login/Phone-Sync", "Overview", "Expenses", "Budget", "Goals", "Autonomous-Mentor"]
    }

@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("SELECT * FROM users WHERE phone = ? LIMIT 1", (req.phone,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("""
        INSERT INTO users (name, phone, sms_permission, knowledge_level, risk_comfort, created_at)
        VALUES (?, ?, ?, 'beginner', 'low', ?)
        """, (req.name, req.phone, 1 if req.sms_permission else 0, now))
        user_id = cursor.lastrowid
        cursor.execute("""
        INSERT INTO financial_profiles (user_id, monthly_income, essential_expenses, flexible_expenses, current_savings, updated_at)
        VALUES (?, 15000.0, 7000.0, 4500.0, 10000.0, ?)
        """, (user_id, now))
        cursor.execute("""
        INSERT INTO savings_goals (user_id, title, target_amount, current_amount, deadline_months, monthly_target, status)
        VALUES (?, 'Laptop', 40000.0, 10000.0, 6, 5000.0, 'active')
        """, (user_id,))
        caps = [(user_id, 'Food', 5000.0, now), (user_id, 'Travel', 2500.0, now), (user_id, 'Shopping', 2000.0, now), (user_id, 'Subscriptions', 500.0, now), (user_id, 'Education', 1500.0, now)]
        cursor.executemany("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", caps)
        conn.commit()
    else:
        user_id = user["id"]
        cursor.execute("UPDATE users SET sms_permission = ? WHERE id = ?", (1 if req.sms_permission else 0, user_id))
        conn.commit()

    conn.close()
    return {"status": "authenticated", "user_id": user_id, "name": req.name, "phone": req.phone, "sms_sync_active": req.sms_permission}

@app.get("/api/dashboard/summary")
def get_dashboard(user_id: int = 1):
    context = ContextBuilder.build_user_context(user_id)
    profile = context["user_profile"]
    goal = context["active_goal"]
    
    insight = f"You have ₹{profile['flexible_room']:,.0f} in flexible room this month — steady food discipline will hit your {goal.get('title', 'Laptop')} goal."
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM budget_caps WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        default_caps = [(user_id, 'Food', 5000.0, now), (user_id, 'Travel', 2500.0, now), (user_id, 'Shopping', 2000.0, now), (user_id, 'Subscriptions', 500.0, now), (user_id, 'Education', 1500.0, now)]
        cursor.executemany("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", default_caps)
        conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,))
    tasks = [dict(row) for row in cursor.fetchall()]
    cursor.execute("SELECT * FROM learning_modules ORDER BY level ASC")
    modules = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
    SELECT c.category, c.monthly_cap, COALESCE(SUM(t.amount), 0) as spent
    FROM budget_caps c
    LEFT JOIN transactions t ON c.user_id = t.user_id AND c.category = t.category
    WHERE c.user_id = ?
    GROUP BY c.category
    """, (user_id,))
    caps_with_spending = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 15", (user_id,))
    recent_transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "financial_strip": {
            "name": profile["name"],
            "phone": profile.get("phone", ""),
            "monthly_income": profile["monthly_income"],
            "essential_expenses": profile["essential_expenses"],
            "flexible_room": profile["flexible_room"],
            "current_savings": profile["current_savings"],
            "ai_insight": insight
        },
        "spending_categories": context["recent_spending"],
        "budget_caps": caps_with_spending,
        "recent_transactions": recent_transactions,
        "active_goal": goal,
        "learning_modules": modules,
        "tasks": tasks
    }

@app.get("/api/transactions")
def get_transactions(user_id: int = 1, category: Optional[str] = None, search: Optional[str] = None, limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]
    
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (merchant LIKE ? OR raw_text LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"transactions": rows, "count": len(rows)}

@app.get("/api/budget/caps")
def get_budget_caps(user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.id, c.category, c.monthly_cap, COALESCE(SUM(t.amount), 0) as spent
    FROM budget_caps c
    LEFT JOIN transactions t ON c.user_id = t.user_id AND c.category = t.category
    WHERE c.user_id = ?
    GROUP BY c.category
    """, (user_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"budget_caps": rows}

@app.post("/api/budget/caps")
def update_budget_cap(req: BudgetCapRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute("SELECT id FROM budget_caps WHERE user_id = ? AND category = ?", (req.user_id or 1, req.category))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE budget_caps SET monthly_cap = ?, updated_at = ? WHERE id = ?", (req.monthly_cap, now, row["id"]))
    else:
        cursor.execute("INSERT INTO budget_caps (user_id, category, monthly_cap, updated_at) VALUES (?, ?, ?, ?)", (req.user_id or 1, req.category, req.monthly_cap, now))
        
    conn.commit()
    conn.close()
    return {"status": "updated", "category": req.category, "monthly_cap": req.monthly_cap}

@app.post("/api/goals/calculate")
def calculate_goal(req: GoalCalculateRequest):
    result = MathEngine.calculate_savings_pacing(
        req.monthly_income or 15000.0,
        req.essential_expenses or 7000.0,
        req.target_amount,
        req.current_savings or 10000.0,
        req.deadline_months
    )
    return result

@app.post("/api/transactions/sms-ingest")
def ingest_sms(req: SMSIngestRequest, user_id: int = 1):
    parsed = SMSParser.parse(req.raw_sms)
    
    if parsed["amount"] > 0:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO transactions (user_id, category, amount, merchant, raw_text, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, parsed["category"], parsed["amount"], parsed["merchant"], req.raw_sms, datetime.now().isoformat()))
        conn.commit()
        
        cursor.execute("SELECT SUM(amount) as total FROM transactions WHERE user_id = ? AND category = ?", (user_id, parsed["category"]))
        total_in_cat = cursor.fetchone()["total"] or parsed["amount"]
        conn.close()
        alert = f"Auto-synced ₹{parsed['amount']:,.0f} to {parsed['category']} ({parsed['merchant']}). Total {parsed['category']}: ₹{total_in_cat:,.0f}."
    else:
        alert = "Could not identify transaction amount from SMS."
        
    return {
        "status": "processed",
        "parsed_transaction": parsed,
        "alert": alert
    }

@app.post("/api/companion/chat")
async def companion_chat(req: ChatRequest):
    context = ContextBuilder.build_user_context(req.user_id or 1)
    reply, actions_executed = await query_llm_mentor(req.message, context, req.user_id or 1)
    
    suggested_tasks = []
    if "invest" in req.message.lower() or "sip" in req.message.lower():
        suggested_tasks.append("Complete Emergency Funds 101 module")
    elif "laptop" in req.message.lower() or "goal" in req.message.lower():
        suggested_tasks.append("Set aside ₹3,750 for Laptop goal")
    else:
        suggested_tasks.append("Review category caps on Budget tab")
        
    return {
        "reply": reply,
        "actions_executed": actions_executed,
        "suggested_tasks": suggested_tasks,
        "context_used": {
            "income": context["user_profile"]["monthly_income"],
            "goal": context["active_goal"].get("title", "Laptop"),
            "flexible_room": context["user_profile"]["flexible_room"],
            "current_savings": context["user_profile"]["current_savings"]
        }
    }

@app.get("/api/learning/modules")
def get_learning_modules(user_id: int = 1):
    context = ContextBuilder.build_user_context(user_id)
    emergency_fund_target = context["user_profile"]["essential_expenses"] * 3
    has_emergency_fund = context["user_profile"]["current_savings"] >= emergency_fund_target

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM learning_modules ORDER BY level ASC")
    modules = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for mod in modules:
        if not has_emergency_fund and "Emergency" in mod["title"]:
            mod["is_recommended"] = 1
        elif has_emergency_fund and "Mutual Fund" in mod["title"]:
            mod["is_recommended"] = 1
        else:
            mod["is_recommended"] = 0

    return {"modules": modules}

@app.get("/api/tasks")
def get_tasks(user_id: int = 1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,))
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"tasks": tasks}

@app.post("/api/tasks")
def add_task(req: TaskCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO tasks (user_id, title, due_date, status, source)
    VALUES (?, ?, ?, 'pending', ?)
    """, (req.user_id or 1, req.title, req.due_date or "This Week", req.source or "manual"))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"task_id": task_id, "title": req.title, "due_date": req.due_date, "status": "pending"}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "task_id": task_id}

@app.post("/api/tasks/{task_id}/toggle")
def toggle_task(task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
        
    new_status = "completed" if row["status"] == "pending" else "pending"
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    conn.close()
    return {"task_id": task_id, "new_status": new_status}

@app.put("/api/profile")
def update_profile(req: ProfileUpdateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    flexible = max(0.0, req.monthly_income - req.essential_expenses)

    cursor.execute("""
    UPDATE financial_profiles
    SET monthly_income = ?, essential_expenses = ?, flexible_expenses = ?, current_savings = ?, updated_at = ?
    WHERE user_id = ?
    """, (req.monthly_income, req.essential_expenses, flexible * 0.5, req.current_savings, now, req.user_id or 1))
    conn.commit()
    conn.close()
    return {
        "status": "updated",
        "monthly_income": req.monthly_income,
        "essential_expenses": req.essential_expenses,
        "flexible_room": flexible,
        "current_savings": req.current_savings
    }

@app.post("/api/goals")
def create_goal(req: GoalCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financial_profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1", (req.user_id or 1,))
    prof = dict(cursor.fetchone() or {"monthly_income": 15000.0, "essential_expenses": 7000.0, "current_savings": 10000.0})

    pacing = MathEngine.calculate_savings_pacing(
        prof["monthly_income"], prof["essential_expenses"], req.target_amount, prof["current_savings"], req.deadline_months
    )

    cursor.execute("""
    INSERT INTO savings_goals (user_id, title, target_amount, current_amount, deadline_months, monthly_target, status)
    VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (req.user_id or 1, req.title, req.target_amount, prof["current_savings"], pacing["recommended_months"], pacing["adjusted_monthly_target"]))
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"goal_id": goal_id, "title": req.title, "pacing": pacing}

# ==========================================
# SERVER RUNNER
# ==========================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
