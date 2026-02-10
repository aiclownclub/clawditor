import sys
import json
import os
from datetime import datetime

# February 2026 Sonnet 4.5 Pricing (per 1M tokens)
PRICING = {
    "input": 3.00,
    "output": 15.00
}

STATE_FILE = ".claude/build_monitor_state.json"
LOG_FILE = "clawditor_audit.log"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"in_tokens": 0, "out_tokens": 0, "build_count": 0, "last_status": "passing"}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f)

def calculate_cost(in_t, out_t):
    return (in_t / 1_000_000 * PRICING["input"]) + (out_t / 1_000_000 * PRICING["output"])

def log_event(trigger, in_t, out_t, builds):
    cost = calculate_cost(in_t, out_t)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # The "Shame Report" Format
    entry = (f"[{timestamp}] {trigger.upper()}\n"
             f" ├─ Total Tokens: {in_t + out_t:,} (In: {in_t:,} / Out: {out_t:,})\n"
             f" ├─ Build Attempts: {builds}\n"
             f" └─ Estimated Cost: ${cost:.4f}\n"
             f"{'-'*50}\n")
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(entry)

def main():
    try:
        hook_data = json.load(sys.stdin)
    except (EOFError, json.JSONDecodeError):
        return

    event = hook_data.get("hook_event_name")
    state = load_state()

    # Track Token Usage from API metadata
    usage = hook_data.get("usage", {})
    state["in_tokens"] += usage.get("input_tokens", 0)
    state["out_tokens"] += usage.get("output_tokens", 0)

    if event == "PostToolUse":
        tool_name = hook_data.get("tool_name")
        tool_input = hook_data.get("tool_input", "")
        
        # Monitor .NET builds
        if tool_name == "Bash" and "dotnet build" in tool_input:
            state["build_count"] += 1
            current_status = "passing" if hook_data.get("exit_code") == 0 else "failed"

            if state["last_status"] == "failed" and current_status == "passing":
                log_event("Success Recovered", state["in_tokens"], state["out_tokens"], state["build_count"])
                # Reset counters
                state.update({"in_tokens": 0, "out_tokens": 0, "build_count": 0})
            
            state["last_status"] = current_status

    elif event == "SessionEnd":
        if state["in_tokens"] + state["out_tokens"] > 0:
            log_event("Session Terminated", state["in_tokens"], state["out_tokens"], state["build_count"])
        
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        return

    save_state(state)

if __name__ == "__main__":
    main()
