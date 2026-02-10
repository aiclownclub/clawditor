import sys
import json
import os
from datetime import datetime

# Path for persistent state and the final log
STATE_FILE = ".claude/build_monitor_state.json"
LOG_FILE = "claude_performance_audit.log"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"running_tokens": 0, "build_count": 0, "last_status": "passing"}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def log_event(trigger, tokens, builds):
    timestamp = datetime.now().isoformat()
    entry = (f"[{timestamp}] TRIGGER: {trigger} | "
             f"TOKENS: {tokens} | BUILDS: {builds}\n")
    with open(LOG_FILE, 'a') as f:
        f.write(entry)

def main():
    # Claude Code passes event data via stdin
    try:
        hook_data = json.load(sys.stdin)
    except EOFError:
        return

    event = hook_data.get("hook_event_name")
    state = load_state()

    # 1. Track Token Usage (Extracted from hook metadata)
    # Most hook payloads include 'usage' from the underlying API call
    usage = hook_data.get("usage", {})
    state["running_tokens"] += usage.get("total_tokens", 0)

    # 2. Handle Build Monitoring
    if event == "PostToolUse":
        tool_name = hook_data.get("tool_name")
        tool_input = hook_data.get("tool_input", "")
        
        # Check if Claude tried to run a dotnet build
        if tool_name == "Bash" and "dotnet build" in tool_input:
            state["build_count"] += 1
            # Check exit code of the tool (0 = success, != 0 = failure)
            current_status = "passing" if hook_data.get("exit_code") == 0 else "failed"

            # Check for Status Change: Failed -> Passing
            if state["last_status"] == "failed" and current_status == "passing":
                log_event("Status Changed to Passing", state["running_tokens"], state["build_count"])
                # Reset counters after success
                state["running_tokens"] = 0
                state["build_count"] = 0
            
            state["last_status"] = current_status

    # 3. Handle Session Termination
    elif event == "SessionEnd":
        log_event("Session Terminated", state["running_tokens"], state["build_count"])
        # Optional: Reset state for next session
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        return

    save_state(state)

if __name__ == "__main__":
    main()
