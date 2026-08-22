// =======================================================
// FINTEX V3.0 CLIENT SPA CONTROLLER
// Multi-Page Navigation, Phone SMS Auto-Sync & Inbuilt Mentor
// =======================================================

let currentUser = {
  id: 1,
  name: "Ananya",
  phone: "+91 98765 43210",
  sms_permission: true
};

let currentProfile = {
  monthly_income: 15000,
  essential_expenses: 7000,
  current_savings: 10000,
  flexible_room: 8000
};

let activePage = "overview";
let expensesFilterCat = "All";
let expensesSearchQuery = "";

// Auto-Sync Phone SMS Stream Mock List
const PHONE_SMS_STREAM = [
  "Sent Rs. 380.00 from HDFC Bank to Swiggy on 22-08-2026 ref 492019 UPI: food order",
  "Paid INR 180.00 to Uber India on 22-08-2026 ref 192837 UPI: campus cab",
  "Debited Rs. 450.00 to Blinkit Grocery Store ref 332190 UPI: groceries",
  "Sent INR 1,299.00 to Myntra Fashion via UPI ref 441029: college clothes",
  "Paid Rs. 119.00 to Spotify Student Subscription via UPI ref 102938",
  "Sent Rs. 240.00 to Campus Cafe Canteen via UPI ref 882910: coffee & snacks",
  "Paid INR 850.00 to Amazon Books via UPI ref 772910: engineering textbooks",
  "Debited Rs. 320.00 to Zepto Quick Grocery ref 991823 UPI: snacks",
  "Paid INR 650.00 to Zomato Online Food ref 481920 UPI: dinner"
];
let smsStreamIdx = 0;
let smsSyncInterval = null;

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
  initAuthSession();
  initNavigation();
  initGoalSimulator();
  initExpensesFilters();
  initMentorChat();
  initModals();
});

// --- AUTH & LOGIN SESSION ---
function initAuthSession() {
  const saved = localStorage.getItem("fintex_user_v3");
  const loginView = document.getElementById("view-login");
  const appView = document.getElementById("view-app");

  if (saved) {
    try {
      currentUser = JSON.parse(saved);
      loginView.style.display = "none";
      appView.style.display = "block";
      document.getElementById("app-user-name").textContent = currentUser.name;
      loadAllDashboardData();
      startBackgroundSMSSync();
    } catch (e) {
      showLoginScreen();
    }
  } else {
    showLoginScreen();
  }

  // Login Form Submission
  const loginForm = document.getElementById("login-form");
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("login-name-input").value.trim();
    const phone = document.getElementById("login-phone-input").value.trim();
    const smsPerm = document.getElementById("login-sms-permission").checked;

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, phone: `+91 ${phone}`, sms_permission: smsPerm })
      });
      if (!res.ok) throw new Error("Authentication failed");
      const data = await res.json();

      currentUser = {
        id: data.user_id,
        name: data.name,
        phone: data.phone,
        sms_permission: data.sms_sync_active
      };
      localStorage.setItem("fintex_user_v3", JSON.stringify(currentUser));

      loginView.style.display = "none";
      appView.style.display = "block";
      document.getElementById("app-user-name").textContent = currentUser.name;
      
      showToast(`Welcome ${currentUser.name}! SMS Auto-Sync Activated.`, "🌟");
      loadAllDashboardData();
      startBackgroundSMSSync();
    } catch (err) {
      console.error("Login error:", err);
      showToast("Error connecting to server", "⚠️");
    }
  });

  // Logout Button
  document.getElementById("btn-logout").addEventListener("click", () => {
    localStorage.removeItem("fintex_user_v3");
    if (smsSyncInterval) clearInterval(smsSyncInterval);
    showLoginScreen();
    showToast("Signed out successfully", "👋");
  });
}

function showLoginScreen() {
  document.getElementById("view-login").style.display = "flex";
  document.getElementById("view-app").style.display = "none";
}

// --- SPA TAB NAVIGATION ---
function initNavigation() {
  const tabs = document.querySelectorAll(".nav-page-tabs .tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.getAttribute("data-target");
      navigateTo(target);
    });
  });
}

function navigateTo(pageId) {
  activePage = pageId;

  // Update navbar tab highlights
  document.querySelectorAll(".nav-page-tabs .tab-btn").forEach(t => {
    if (t.getAttribute("data-target") === pageId) {
      t.classList.add("active");
    } else {
      t.classList.remove("active");
    }
  });

  // Toggle page visibility
  document.querySelectorAll(".page-view").forEach(p => {
    p.classList.remove("active");
  });

  const activePageElem = document.getElementById(`page-${pageId}`);
  if (activePageElem) {
    activePageElem.classList.add("active");
  }

  // Refresh page specific views
  if (pageId === "expenses") {
    loadTransactionsLedger();
  } else if (pageId === "budget") {
    loadBudgetCaps();
  }
}

// --- DASHBOARD DATA FETCHER ---
async function loadAllDashboardData() {
  try {
    const res = await fetch(`/api/dashboard/summary?user_id=${currentUser.id}`);
    if (!res.ok) throw new Error("Failed to load dashboard data");
    const data = await res.json();
    renderOverviewPage(data);
    renderBudgetCaps(data.budget_caps);
    renderGoalsPage(data.active_goal);
  } catch (err) {
    console.error("Data load error:", err);
  }
}

// --- OVERVIEW PAGE RENDERING ---
function renderOverviewPage(data) {
  const strip = data.financial_strip;
  currentProfile.monthly_income = strip.monthly_income;
  currentProfile.essential_expenses = strip.essential_expenses;
  currentProfile.flexible_room = strip.flexible_room;
  currentProfile.current_savings = strip.current_savings;

  // Metric Strip
  document.getElementById("val-income").textContent = `₹${strip.monthly_income.toLocaleString('en-IN')}`;
  document.getElementById("val-essentials").textContent = `₹${strip.essential_expenses.toLocaleString('en-IN')}`;
  document.getElementById("val-flexible").textContent = `₹${strip.flexible_room.toLocaleString('en-IN')}`;
  document.getElementById("val-savings").textContent = `₹${strip.current_savings.toLocaleString('en-IN')}`;

  // AI Insight
  document.getElementById("ai-insight-text").textContent = strip.ai_insight;

  // Overview Goal Card
  if (data.active_goal) {
    const goal = data.active_goal;
    document.getElementById("overview-goal-title").textContent = goal.title;
    document.getElementById("overview-goal-target").textContent = `₹${goal.target_amount.toLocaleString('en-IN')}`;
    document.getElementById("overview-goal-monthly").textContent = `₹${goal.monthly_target.toLocaleString('en-IN')}/mo`;
    document.getElementById("overview-goal-deadline").textContent = `${goal.deadline_months} Months`;

    const pct = Math.min(100, Math.round((goal.current_amount / (goal.target_amount || 1)) * 100));
    document.getElementById("overview-goal-pct").textContent = `${pct}%`;

    const circle = document.getElementById("overview-goal-bar");
    if (circle) {
      const radius = 42;
      const circumference = 2 * Math.PI * radius;
      circle.style.strokeDasharray = `${circumference}`;
      const offset = circumference - (pct / 100) * circumference;
      circle.style.strokeDashoffset = `${offset}`;
    }
  }

  // Overview Recent Transactions
  const recTransContainer = document.getElementById("overview-recent-transactions");
  recTransContainer.innerHTML = "";
  if (data.recent_transactions && data.recent_transactions.length > 0) {
    data.recent_transactions.slice(0, 4).forEach(tx => {
      const div = document.createElement("div");
      div.style.display = "flex";
      div.style.justifyContent = "space-between";
      div.style.alignItems = "center";
      div.style.padding = "0.5rem 0.75rem";
      div.style.background = "#0d131f";
      div.style.borderRadius = "4px";
      div.style.fontSize = "0.78rem";
      div.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="cat-badge ${tx.category}">${tx.category}</span>
          <strong style="color:#fff;">${tx.merchant}</strong>
        </div>
        <span style="font-family:'Outfit',sans-serif; font-weight:700; color:#fff;">₹${tx.amount.toLocaleString('en-IN')}</span>
      `;
      recTransContainer.appendChild(div);
    });
  } else {
    recTransContainer.innerHTML = `<div style="font-size:0.75rem; color:var(--text-dim);">No transactions auto-synced yet.</div>`;
  }

  // Overview Tasks
  renderTasks(data.tasks);
}

function renderTasks(tasks) {
  const container = document.getElementById("overview-tasks-list");
  container.innerHTML = "";

  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<div style="font-size:0.75rem; color:var(--text-dim); text-align:center; padding:0.5rem;">No pending tasks. Tell your Mentor to add one!</div>`;
    return;
  }

  tasks.forEach(task => {
    const isDone = task.status === "completed";
    const div = document.createElement("div");
    div.className = `task-row ${isDone ? "completed" : ""}`;
    div.id = `task-row-${task.id}`;
    div.innerHTML = `
      <div class="task-check-box" onclick="toggleTask(${task.id})">${isDone ? "✓" : ""}</div>
      <div class="task-text-wrap" onclick="toggleTask(${task.id})" style="cursor:pointer;">
        <div class="task-text">${task.title}</div>
        <div class="task-sub-info">Due: ${task.due_date} • ${task.source}</div>
      </div>
      <button class="task-delete-btn" title="Delete Task" onclick="deleteTask(${task.id})">&times;</button>
    `;
    container.appendChild(div);
  });
}

async function toggleTask(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/toggle`, { method: "POST" });
    if (!res.ok) throw new Error("Toggle failed");
    const data = await res.json();
    loadAllDashboardData();
    showToast(`Task marked ${data.new_status}`, "✅");
  } catch (err) {
    console.error("Task toggle error:", err);
  }
}

async function deleteTask(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    showToast("Task deleted", "🗑️");
    loadAllDashboardData();
  } catch (err) {
    console.error("Delete task error:", err);
  }
}

// --- EXPENSES PAGE LEDGER ---
function initExpensesFilters() {
  const filterPills = document.querySelectorAll("#expenses-filter-pills .filter-pill");
  filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      expensesFilterCat = pill.getAttribute("data-cat");
      loadTransactionsLedger();
    });
  });

  const searchInput = document.getElementById("expenses-search-input");
  searchInput.addEventListener("input", (e) => {
    expensesSearchQuery = e.target.value.trim();
    loadTransactionsLedger();
  });

  document.getElementById("btn-trigger-mock-sms").addEventListener("click", () => {
    triggerMockSMSAutoSync();
  });
}

async function loadTransactionsLedger() {
  try {
    let url = `/api/transactions?user_id=${currentUser.id}`;
    if (expensesFilterCat && expensesFilterCat !== "All") {
      url += `&category=${expensesFilterCat}`;
    }
    if (expensesSearchQuery) {
      url += `&search=${encodeURIComponent(expensesSearchQuery)}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch transactions");
    const data = await res.json();
    
    const tbody = document.getElementById("expenses-table-body");
    tbody.innerHTML = "";

    if (data.transactions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-dim); padding:2rem;">No matching auto-synced transactions found.</td></tr>`;
      return;
    }

    data.transactions.forEach(tx => {
      const tr = document.createElement("tr");
      const dateStr = tx.date ? new Date(tx.date).toLocaleDateString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "Today";
      tr.innerHTML = `
        <td><span class="cat-badge ${tx.category}">${tx.category}</span></td>
        <td><strong style="color:#fff;">${tx.merchant}</strong></td>
        <td><span style="font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:var(--text-muted);">${tx.raw_text || "UPI Transaction"}</span></td>
        <td style="font-family:'Outfit',sans-serif; font-weight:700; color:#fff; font-size:0.95rem;">₹${tx.amount.toLocaleString('en-IN')}</td>
        <td style="font-size:0.75rem; color:var(--text-dim);">${dateStr}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Ledger error:", err);
  }
}

// --- BUDGET PAGE RENDERING ---
function renderBudgetCaps(caps) {
  // 50/30/20 values
  const income = currentProfile.monthly_income;
  document.getElementById("budget-needs-val").textContent = `₹${(income * 0.5).toLocaleString('en-IN')}`;
  document.getElementById("budget-wants-val").textContent = `₹${(income * 0.3).toLocaleString('en-IN')}`;
  document.getElementById("budget-savings-val").textContent = `₹${(income * 0.2).toLocaleString('en-IN')}`;

  const container = document.getElementById("budget-caps-container");
  container.innerHTML = "";

  if (!caps || caps.length === 0) {
    container.innerHTML = `<div style="font-size:0.8rem; color:var(--text-dim);">No budget caps configured yet.</div>`;
    return;
  }

  caps.forEach(cap => {
    const pct = Math.min(100, Math.round((cap.spent / (cap.monthly_cap || 1)) * 100));
    let statusClass = "";
    let statusLabel = "Safe (<75%)";
    let statusColor = "#34d399";

    if (pct >= 90) {
      statusClass = "danger";
      statusLabel = "⚠️ Near Cap Limit";
      statusColor = "var(--rose)";
    } else if (pct >= 75) {
      statusClass = "amber";
      statusLabel = "Caution (75-90%)";
      statusColor = "var(--replit-amber)";
    }

    const div = document.createElement("div");
    div.className = "cap-item-row";
    div.innerHTML = `
      <div class="cap-item-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="cat-badge ${cap.category}">${cap.category}</span>
          <strong style="color:#fff; font-size:0.9rem;">₹${cap.spent.toLocaleString('en-IN')} <span style="font-size:0.75rem; color:var(--text-dim); font-weight:normal;">/ ₹${cap.monthly_cap.toLocaleString('en-IN')} cap</span></strong>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:0.72rem; font-family:'JetBrains Mono',monospace; color:${statusColor}; font-weight:600;">${pct}% • ${statusLabel}</span>
          <button class="replit-btn replit-btn-sm" onclick="openCapModalFor('${cap.category}', ${cap.monthly_cap})">Edit Cap</button>
        </div>
      </div>
      <div class="cap-progress-bar-bg">
        <div class="cap-progress-bar-fill ${statusClass}" style="width: ${pct}%;"></div>
      </div>
    `;
    container.appendChild(div);
  });
}

function openCapModalFor(category, currentCap) {
  document.getElementById("cap-category-select").value = category;
  document.getElementById("cap-amount-input").value = currentCap;
  document.getElementById("modal-budget-cap").classList.add("active");
}

// --- GOALS PAGE & MATH SIMULATOR ---
function renderGoalsPage(activeGoal) {
  const container = document.getElementById("goals-cards-grid");
  container.innerHTML = "";

  if (!activeGoal) return;

  const pct = Math.min(100, Math.round((activeGoal.current_amount / (activeGoal.target_amount || 1)) * 100));
  
  const div = document.createElement("div");
  div.className = "goal-card-item";
  div.innerHTML = `
    <div class="goal-svg-wrap">
      <svg width="90" height="90" viewBox="0 0 100 100">
        <circle class="goal-circle-bg" cx="50" cy="50" r="42"></circle>
        <circle class="goal-circle-bar" cx="50" cy="50" r="42" style="stroke-dasharray: 264; stroke-dashoffset: ${264 - (pct/100)*264};"></circle>
      </svg>
      <div class="goal-pct-center">
        <div class="goal-pct-number">${pct}%</div>
        <div style="font-size:0.6rem; color:var(--text-dim);">SAVED</div>
      </div>
    </div>
    <div style="flex-grow:1;">
      <h4 style="font-size:1.15rem; color:#fff; margin-bottom:0.25rem;">${activeGoal.title}</h4>
      <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:4px;">
        Target: <strong style="color:#fff;">₹${activeGoal.target_amount.toLocaleString('en-IN')}</strong> • Saved: <strong style="color:#34d399;">₹${activeGoal.current_amount.toLocaleString('en-IN')}</strong>
      </div>
      <div style="font-size:0.75rem; color:var(--text-dim);">
        Target Saving: <strong style="color:var(--sea-cyan);">₹${activeGoal.monthly_target.toLocaleString('en-IN')}/month</strong> • Deadline: ${activeGoal.deadline_months} Months
      </div>
    </div>
  `;
  container.appendChild(div);

  // Set simulator sliders
  const simTarget = document.getElementById("sim-target-slider");
  const simDeadline = document.getElementById("sim-deadline-slider");
  if (simTarget) simTarget.value = activeGoal.target_amount;
  if (simDeadline) simDeadline.value = activeGoal.deadline_months;
  updateSimulator();
}

function initGoalSimulator() {
  const targetSlider = document.getElementById("sim-target-slider");
  const deadlineSlider = document.getElementById("sim-deadline-slider");

  if (targetSlider && deadlineSlider) {
    targetSlider.addEventListener("input", updateSimulator);
    deadlineSlider.addEventListener("input", updateSimulator);
  }
}

async function updateSimulator() {
  const target = parseFloat(document.getElementById("sim-target-slider").value);
  const deadline = parseInt(document.getElementById("sim-deadline-slider").value, 10);

  document.getElementById("sim-target-label").textContent = `₹${target.toLocaleString('en-IN')}`;
  document.getElementById("sim-deadline-label").textContent = `${deadline} Month${deadline > 1 ? 's' : ''}`;

  try {
    const res = await fetch("/api/goals/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_amount: target,
        deadline_months: deadline,
        current_savings: currentProfile.current_savings,
        monthly_income: currentProfile.monthly_income,
        essential_expenses: currentProfile.essential_expenses
      })
    });
    if (!res.ok) throw new Error("Calculation failed");
    const result = await res.json();

    document.getElementById("sim-required-monthly").textContent = `₹${result.monthly_target.toLocaleString('en-IN')} / month`;
    
    const tag = document.getElementById("sim-status-tag");
    const note = document.getElementById("sim-status-note");

    if (result.is_realistic) {
      tag.style.background = "rgba(16,185,129,0.15)";
      tag.style.borderColor = "rgba(16,185,129,0.4)";
      tag.style.color = "#34d399";
      tag.textContent = `Realistic Pacing (${Math.round((result.monthly_target / currentProfile.flexible_room) * 100)}% Flex)`;
      note.textContent = "Timeline aligned with monthly flexible room";
    } else {
      tag.style.background = "rgba(245,158,11,0.15)";
      tag.style.borderColor = "rgba(245,158,11,0.4)";
      tag.style.color = "var(--replit-amber)";
      tag.textContent = `Tight Budget (>75% Flex)`;
      note.textContent = `Recommended extended pace: ${result.recommended_months} months (₹${result.adjusted_monthly_target.toLocaleString('en-IN')}/mo)`;
    }
  } catch (err) {
    console.error("Simulator error:", err);
  }
}

// --- PHONE SMS AUTO-SYNC BACKGROUND ENGINE ---
function startBackgroundSMSSync() {
  if (smsSyncInterval) clearInterval(smsSyncInterval);
  // Auto-sync incoming SMS simulation every 18 seconds
  smsSyncInterval = setInterval(() => {
    triggerMockSMSAutoSync();
  }, 18000);
}

async function triggerMockSMSAutoSync() {
  smsStreamIdx = (smsStreamIdx + 1) % PHONE_SMS_STREAM.length;
  const mockSMS = PHONE_SMS_STREAM[smsStreamIdx];

  const previewElem = document.getElementById("expenses-stream-preview");
  if (previewElem) {
    previewElem.textContent = mockSMS;
  }

  try {
    const res = await fetch(`/api/transactions/sms-ingest?user_id=${currentUser.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_sms: mockSMS })
    });
    if (!res.ok) throw new Error("Auto-sync failed");
    const data = await res.json();

    showToast(data.alert, "📱");
    
    // Refresh all active pages in real-time
    loadAllDashboardData();
    if (activePage === "expenses") {
      loadTransactionsLedger();
    }
  } catch (err) {
    console.error("SMS auto-sync error:", err);
  }
}

// --- INBUILT MENTOR CHAT ENGINE ---
function initMentorChat() {
  const form = document.getElementById("mentor-chat-form");
  const input = document.getElementById("mentor-chat-input");
  const chips = document.querySelectorAll("#mentor-prompt-chips .mentor-prompt-chip");

  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      const cmd = chip.getAttribute("data-cmd");
      input.value = cmd;
      sendMentorMessage(cmd);
      input.value = "";
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (query) {
      sendMentorMessage(query);
      input.value = "";
    }
  });
}

async function sendMentorMessage(query) {
  const thread = document.getElementById("mentor-chat-thread");

  // User message bubble
  const userMsg = document.createElement("div");
  userMsg.className = "chat-bubble user";
  userMsg.textContent = query;
  thread.appendChild(userMsg);
  thread.scrollTop = thread.scrollHeight;

  // AI Mentor Placeholder
  const aiMsg = document.createElement("div");
  aiMsg.className = "chat-bubble ai";
  aiMsg.innerHTML = `<em>Inbuilt Mentor is analyzing and executing your command...</em>`;
  thread.appendChild(aiMsg);
  thread.scrollTop = thread.scrollHeight;

  try {
    const res = await fetch("/api/companion/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: query, user_id: currentUser.id })
    });
    if (!res.ok) throw new Error("Mentor request failed");
    const data = await res.json();

    // Format markdown
    let formatted = data.reply
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/^\* (.*$)/gim, "<li>$1</li>")
      .replace(/\n\n/g, "<br><br>")
      .replace(/\n/g, "<br>");

    if (formatted.includes("<li>")) {
      formatted = formatted.replace(/(<li>.*?<\/li>)/s, "<ul>$1</ul>");
    }

    aiMsg.innerHTML = formatted;

    // Render action badges if actions were executed
    if (data.actions_executed && data.actions_executed.length > 0) {
      data.actions_executed.forEach(act => {
        const badge = document.createElement("div");
        badge.className = "action-badge-pill";
        badge.innerHTML = `⚡ MENTOR ACTION EXECUTED: ${act.type.replace('_', ' ').toUpperCase()}`;
        aiMsg.appendChild(badge);
      });
      // Synchronize entire application state across all pages!
      loadAllDashboardData();
    }

    thread.scrollTop = thread.scrollHeight;
  } catch (err) {
    console.error("Mentor chat error:", err);
    aiMsg.innerHTML = `⚠️ Mentor connection error. Please try again.`;
  }
}

// --- MODALS (PROFILE, GOALS, BUDGET CAPS) ---
function initModals() {
  // Profile Modal
  const profModal = document.getElementById("modal-profile");
  const openProfBtn = document.getElementById("btn-edit-profile-nav");
  const closeProfBtn = document.getElementById("btn-close-profile-modal");
  const cancelProfBtn = document.getElementById("btn-cancel-profile-modal");
  const profForm = document.getElementById("profile-form");

  openProfBtn.addEventListener("click", () => {
    document.getElementById("prof-income-input").value = currentProfile.monthly_income;
    document.getElementById("prof-essentials-input").value = currentProfile.essential_expenses;
    document.getElementById("prof-savings-input").value = currentProfile.current_savings;
    profModal.classList.add("active");
  });
  const closeProf = () => profModal.classList.remove("active");
  closeProfBtn.addEventListener("click", closeProf);
  cancelProfBtn.addEventListener("click", closeProf);

  profForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      user_id: currentUser.id,
      monthly_income: parseFloat(document.getElementById("prof-income-input").value),
      essential_expenses: parseFloat(document.getElementById("prof-essentials-input").value),
      current_savings: parseFloat(document.getElementById("prof-savings-input").value)
    };
    try {
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Profile update failed");
      closeProf();
      showToast("Profile updated successfully", "✅");
      loadAllDashboardData();
    } catch (err) {
      console.error(err);
      showToast("Error updating profile", "⚠️");
    }
  });

  // Goal Modal
  const goalModal = document.getElementById("modal-new-goal");
  const openGoalBtn = document.getElementById("btn-open-new-goal-modal");
  const closeGoalBtn = document.getElementById("btn-close-goal-modal");
  const cancelGoalBtn = document.getElementById("btn-cancel-goal-modal");
  const goalForm = document.getElementById("new-goal-form");

  openGoalBtn.addEventListener("click", () => goalModal.classList.add("active"));
  const closeGoal = () => goalModal.classList.remove("active");
  closeGoalBtn.addEventListener("click", closeGoal);
  cancelGoalBtn.addEventListener("click", closeGoal);

  goalForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      user_id: currentUser.id,
      title: document.getElementById("new-goal-title").value,
      target_amount: parseFloat(document.getElementById("new-goal-target").value),
      deadline_months: parseInt(document.getElementById("new-goal-months").value, 10)
    };
    try {
      const res = await fetch("/api/goals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Goal creation failed");
      closeGoal();
      showToast(`Goal '${payload.title}' created!`, "🎯");
      loadAllDashboardData();
    } catch (err) {
      console.error(err);
      showToast("Error creating goal", "⚠️");
    }
  });

  // Budget Cap Modal
  const capModal = document.getElementById("modal-budget-cap");
  const openCapBtn = document.getElementById("btn-open-budget-cap-modal");
  const closeCapBtn = document.getElementById("btn-close-cap-modal");
  const cancelCapBtn = document.getElementById("btn-cancel-cap-modal");
  const capForm = document.getElementById("budget-cap-form");

  if (openCapBtn) openCapBtn.addEventListener("click", () => capModal.classList.add("active"));
  const closeCap = () => capModal.classList.remove("active");
  closeCapBtn.addEventListener("click", closeCap);
  cancelCapBtn.addEventListener("click", closeCap);

  capForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      user_id: currentUser.id,
      category: document.getElementById("cap-category-select").value,
      monthly_cap: parseFloat(document.getElementById("cap-amount-input").value)
    };
    try {
      const res = await fetch("/api/budget/caps", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Cap update failed");
      closeCap();
      showToast(`Updated ${payload.category} cap to ₹${payload.monthly_cap.toLocaleString('en-IN')}`, "📊");
      loadAllDashboardData();
    } catch (err) {
      console.error(err);
      showToast("Error saving cap", "⚠️");
    }
  });

  // Overview Quick Task
  document.getElementById("btn-overview-add-task").addEventListener("click", () => {
    const title = prompt("Enter new action task description:");
    if (title && title.trim()) {
      fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), due_date: "This Week", source: "manual", user_id: currentUser.id })
      }).then(() => {
        showToast("Task added to checklist", "✅");
        loadAllDashboardData();
      });
    }
  });
}

// --- REPLIT TOAST NOTIFICATIONS ---
let toastTimeout;
function showToast(message, icon = "⚡") {
  const toast = document.getElementById("replit-toast");
  document.getElementById("toast-icon").textContent = icon;
  document.getElementById("toast-msg").textContent = message;

  toast.style.display = "flex";
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.style.display = "none";
  }, 4500);
}
