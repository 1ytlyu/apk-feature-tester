---
name: apk-feature-tester
description: Use when testing, verifying, or validating Android APK features via ADB automation. Triggers on requests like "test the app", "check if feature X works", "verify the APK", "run UI tests", "test this Android app", "验证功能", "测试APK", "检查功能是否正常". Simulates real user interactions (tap, swipe, input) on emulator/device, captures screenshots, and generates a product feature analysis report focused on user-perspective issues.
---

# APK Feature Tester

Simulate operating an Android APK to verify feature implementation and generate a product analysis report from the user's perspective.

## Core Philosophy

You are a **QA tester**, not a code reviewer. Think like a real user:
- Does the feature actually work when I tap it?
- Is the flow intuitive? Can I figure out what to do next?
- What happens when I do something unexpected (empty input, rapid taps, back button)?
- Are there visual glitches, missing feedback, or confusing states?

The goal is not to check code quality — it's to check **whether the product delivers what the user asked for**.

## Prerequisites

- ADB installed and in PATH
- Running emulator or connected device (`adb devices` shows a device)
- APK built (debug or release)
- Python 3.10+ (for utility scripts — uses only stdlib)

## Workflow

### Phase 1: Understand the Request

Before touching ADB, clarify what the user wants tested:

1. **Specific features** — "test the diary feature" means focus on diary CRUD, not the entire app
2. **Full app audit** — "test everything" means systematically go through all screens
3. **Regression check** — "did the latest change fix X?" means reproduce the specific scenario

If the user says something vague like "test the app", ask which features or screens they care about most. Don't assume.

### Phase 2: Build a Feature Map

Read the source code to build a mental model of what exists before testing. This prevents blind fumbling on the device.

For each target feature, identify:
- **Entry point** — which Activity/Fragment hosts it, what Intent or navigation action reaches it
- **Key UI elements** — buttons, text fields, lists, toggles (from layout XML files). Note the `android:id` values — these become `resource-id` on device and are the most stable way to locate elements.
- **Expected behavior** — what should happen on tap, submit, long-press
- **Data layer** — Room DAO, SharedPreferences, network calls (so you can verify persistence)
- **Dependencies** — permissions needed, services required, login state

Use the source code as your map, but **test from the UI, not from the code**. The code tells you what should happen; the device tells you what actually happens.

### Phase 3: Device Setup

```bash
# Check connected devices
adb devices

# If no device: start emulator
emulator -avd <avd_name> &    # or: ~/Android/Sdk/emulator/emulator -avd <avd_name>
adb wait-for-device

# Install APK (if not already installed)
adb install -r path/to/app.apk

# Clear app data for clean state (optional, for fresh testing)
adb shell pm clear <package_name>
```

Verify the app launches:
```bash
adb shell am start -n <package>/<main_activity>
python scripts/ui_wait.py --text "<expected_text>" --timeout 10
adb shell screencap -p /sdcard/screen_check.png
adb pull /sdcard/screen_check.png /tmp/screen_check.png
```

If the app crashes on launch, check logcat immediately:
```bash
adb logcat -d -s AndroidRuntime:E | tail -50
```

### Phase 4: Systematic UI Exploration

All element interaction uses the bundled Python scripts in `scripts/`. These replace fragile coordinate-based tapping with **semantic element locating**, **polling waits**, and **automatic retry**.

#### Script Overview

| Script | Purpose | Example |
|--------|---------|---------|
| `ui_find.py` | Find element by text/id, get tap coordinates | `python scripts/ui_find.py /tmp/ui.xml --text "保存"` |
| `ui_wait.py` | Poll until element appears/disappears | `python scripts/ui_wait.py --text "加载完成" --timeout 15` |
| `adb_input.py` | Text input with auto Chinese support | `python scripts/adb_input.py text "你好"` |
| `adb_interact.py` | High-level: find + tap + wait + retry | `python scripts/adb_interact.py tap --text "保存" --wait-after "已保存"` |

#### Step 1: Navigate to the feature

```bash
# Launch specific activity
adb shell am start -n <package>/<activity>

# Wait for the screen to load (don't use sleep!)
python scripts/ui_wait.py --text "<expected_screen_text>" --timeout 10
```

#### Step 2: Capture the initial state

```bash
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png /tmp/screen_01.png
```

#### Step 3: Interact with semantic locating

**Tap an element by text:**
```bash
python scripts/adb_interact.py tap --text "保存" --retries 3
```

**Tap an element by resource-id (more stable):**
```bash
python scripts/adb_interact.py tap --id "com.shendu.app:id/btn_save" --retries 3
```

**Tap and wait for confirmation:**
```bash
python scripts/adb_interact.py tap --text "保存" --wait-after "保存成功" --timeout 5
```

**Tap and wait for screen transition:**
```bash
python scripts/adb_interact.py tap --text "日记" --wait-screen "日记详情" --timeout 10
```

**Input Chinese text:**
```bash
python scripts/adb_input.py text "今天天气真好"
```

**Input ASCII text:**
```bash
python scripts/adb_input.py text "hello world"
```

**Scroll to find an off-screen element:**
```bash
python scripts/adb_interact.py scroll-find --text "隐私政策" --max-scrolls 5
```

**Press back:**
```bash
python scripts/adb_input.py key 4
```

#### Step 4: Verify the outcome

After each interaction, verify the result:
```bash
# Wait for expected state (don't use sleep!)
python scripts/ui_wait.py --text "预期文本" --timeout 5

# Take screenshot for visual verification
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png /tmp/screen_after.png
```

Check whether the expected result occurred:
- **Visual**: Does the screenshot show the expected screen/content?
- **State**: Did data persist? (Check via UI — e.g., reopen the screen, check if item appears in list)
- **Feedback**: Did the user get confirmation (toast, snackbar, navigation)?
- **Error handling**: What happens with invalid input? (empty fields, special characters, extremely long text)

#### Finding elements without knowing exact text

When you need to explore what's on screen:
```bash
# List all clickable elements
python scripts/ui_find.py /tmp/ui.xml --all

# Search by partial text
python scripts/ui_find.py /tmp/ui.xml --contains "日"

# Filter by class
python scripts/ui_find.py /tmp/ui.xml --class "Button" --clickable

# Get JSON output for complex queries
python scripts/ui_find.py /tmp/ui.xml --all --json
```

### Phase 5: Edge Case Testing

For each feature, also test these common failure modes:

| Scenario | How to test |
|----------|-------------|
| Empty submission | Leave fields blank, tap submit |
| Rapid double-tap | Tap the same button twice quickly (`adb_interact.py tap` then immediate second tap) |
| Back button mid-flow | `python scripts/adb_input.py key 4` during multi-step process |
| Rotation | `adb shell settings put system accelerometer_rotation 1` then rotate |
| Long text | Input 500+ characters: `python scripts/adb_input.py text "$(python3 -c 'print("A"*500)')"` |
| Special characters | `python scripts/adb_input.py text '<script>alert(1)</script>'` |
| Permission denial | Deny a permission, check graceful handling |
| Network unavailable | Toggle airplane mode, test offline behavior |
| Background/foreground | Press home, reopen app, check state preservation |

Not all of these apply to every feature — use judgment. Focus on scenarios a real user would actually encounter.

### Phase 6: Generate the Report

Read `references/report-template.md` for the full template. The report structure:

```markdown
# APK Feature Analysis Report

## Executive Summary
[2-3 sentences: overall assessment, total features tested, pass/fail ratio]

## Feature Analysis

### Feature: [Name]
- **Status**: ✅ Pass / ⚠️ Partial / ❌ Fail
- **User Flow Tested**: [describe the steps you took]
- **Expected**: [what should happen]
- **Actual**: [what actually happened]
- **Screenshot**: [attach key screenshots]
- **Issues Found**:
  - [issue description with severity]

## UX Issues Summary
| # | Issue | Feature | Severity | Description |
|---|-------|---------|----------|-------------|
| 1 | ... | Diary | Major | ... |

## Recommendations
[Prioritized list of what to fix, from user impact perspective]
```

#### Severity Levels

- **Critical**: App crashes, data loss, feature completely non-functional
- **Major**: Feature works but with significant UX problems (confusing flow, missing feedback, broken layout)
- **Minor**: Polish issues (inconsistent styling, missing animation, minor alignment)

#### Screenshots

Save all screenshots to a temporary directory. In the report, reference them by filename:
```
![Diary - Empty State](/tmp/apk_test/diary_empty.png)
```

At the end, offer to open the screenshot directory so the user can review visually.

## When Things Go Wrong

- **App crashes**: Immediately capture `adb logcat -d -s AndroidRuntime:E` and include in report
- **ANR (hang)**: `adb pull /data/anr/traces.txt` for stack traces
- **Element not found**: Use `--all` to list what's actually on screen — the element may have different text than expected
- **UI dump fails**: Some system dialogs can't be dumped; use screenshot instead
- **Tap missed**: The element may have moved or the screen scrolled. Dump UI again to get fresh coordinates
- **ADBKeyboard not responding**: Re-run `python scripts/adb_input.py text "test"` — it auto-recovers by reinstalling

## Important Constraints

- You are simulating a user, not a developer. Don't read logcat to "understand" what happened — look at the screen first.
- **Never use `sleep N` for UI synchronization.** Always use `ui_wait.py` — it polls until the target state is detected, which is both faster and more reliable.
- **Never hardcode tap coordinates.** Always use `ui_find.py` or `adb_interact.py` to locate elements semantically. Coordinates change with screen size, density, and content.
- If a feature requires login, handle that first. Don't skip features because of auth walls — log in and proceed.
- Don't modify app data or source code during testing. You're an observer, not a developer (unless explicitly asked).
- Save screenshots liberally. They're cheap and invaluable for the report.
