# Clawditor

Because you must audit the Claude! 


## Overview

If you're here, you know why you're here. I have no idea if this works. I've neither run it, nor tested it, but Gemini said this would do the trick. It's about time to put these models in true antagonistic mode against each other, amirite? I mean, who DOESN'T love watching their usage burn through the roof while Claude Code makes wildly naive - ok, dumb and wasteful - changes to files that cause errors that it has to fix. It's the ultimate Ponzi scheme - Madoff would be proud!

## Configuration

You need to tell Claude Code to execute this script. Add the following to your project's .claude/settings.json:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 clawditor.py" }]
      }
    ],
    "PostToolUseFailure": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "python3 clawditor.py" }]
      }
    ],
    "Notification": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "python3 clawditor.py" }]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [{ "type": "command", "command": "python3 clawditor.py" }]
      }
    ]
  }
}
```
