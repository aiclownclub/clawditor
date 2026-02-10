import sys
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
HOURLY_RATE = 50.00      # Replace with your hourly cost. No, I'm not putting my actual number in here.
LOCKOUT_HOURS = 5        # Standard Claude Code cooldown
PRICING_IN = 3.00        # Per 1M tokens (Sonnet 4.5)
PRICING_OUT = 15.00      # Per 1M tokens (Sonnet 4.5)

STATE_FILE = ".claude/clawditor_state.json"
LOG_FILE = "clawditor_audit.log"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"in_t": 0, "out_t": 0, "builds": 0, "last_status": "passing"}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def log_event(title, state, is_lockout=False):
    in_t, out_t, builds = state["in_t"], state["out_t"], state["builds"]
    token_cost = (in_t / 1_000_000 * PRICING_IN) + (out_t / 1_000_000 * PRICING_OUT)
    opp_cost = HOURLY_RATE * LOCKOUT_HOURS if is_lockout else 0
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = "🚨 LOCKOUT DETECTED" if is_lockout else f"✅ {title.upper()}"
    
    entry = (f"[{timestamp}] {header}\n"
             f" ├─ Usage: {in_t + out_t:,} tokens (${token_cost:.4f})\n"
             f" ├─ Build Attempts: {builds}\n"
             f" └─ Opportunity Cost: ${opp_cost:.2f}\n"
             f"{'-'*50}\n")
    
    with open(LOG_FILE, 'a') as f:
        f.write(entry)

def main():
    try:
        hook_data = json.load(sys.stdin)
    except: return

    event = hook_data.get("hook_event_name")
    state = load_state()

    # 1. Update Token Usage
    usage = hook_data.get("usage", {})
    state["in_t"] += usage.get("input_tokens", 0)
    state["out_t"] += usage.get("output_tokens", 0)

    # 2. Event: PostToolUse (Successful tool completion)
    if event == "PostToolUse":
        tool_input = str(hook_data.get("tool_input", ""))
        if "dotnet build" in tool_input:
            state["builds"] += 1
            # exit_code 0 = Success
            if hook_data.get("exit_code") == 0 and state["last_status"] == "failed":
                log_event("Build Fixed", state)
                state.update({"in_t": 0, "out_t": 0, "builds": 0})
            state["last_status"] = "passing" if hook_data.get("exit_code") == 0 else "failed"

    # 3. Event: PostToolUseFailure (API/Rate Limit Errors)
    elif event == "PostToolUseFailure":
        error_msg = str(hook_data.get("error", "")).lower()
        if "rate limit" in error_msg or "quota" in error_msg:
            log_event("Quota Hit", state, is_lockout=True)

    # 4. Event: Notification (Claude alerting you it is stuck/limited)
    elif event == "Notification":
        msg = str(hook_data.get("message", "")).lower()
        if "resets in" in msg or "limit reached" in msg:
            log_event("Notification Lockout", state, is_lockout=True)

    # 5. Event: SessionEnd (Final Tally)
    elif event == "SessionEnd":
        if state["in_t"] + state["out_t"] > 0:
            log_event("Session Closed", state)
        if os.path.exists(STATE_FILE): os.remove(STATE_FILE)
        return

    save_state(state)

if __name__ == "__main__":
    main()
