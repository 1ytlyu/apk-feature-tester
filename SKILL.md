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
- **Key UI elements** — buttons, text fields, lists, toggles (from layout XML files)
- **Expected behavior** — what should happen on tap, submit, long-press
- **Data layer** — Room DAO, SharedPreferences, network calls (so you can verify persistence)
- **Dependencies** — permissions needed, services required, login state

Use the source code as your map, but **test from the UI, not from the code**. The code tells you what should happen; the device tells you what actually happens.

Read `references/adb-commands.md` for the ADB command toolkit.

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
sleep 2
adb shell screencap -p /sdcard/screen_check.png
adb pull /sdcard/screen_check.png /tmp/screen_check.png
```

If the app crashes on launch, check logcat immediately:
```bash
adb logcat -d -s AndroidRuntime:E | tail -50
```

### Phase 4: Systematic UI Exploration

For each feature, follow this cycle:

#### Step 1: Navigate to the feature
```bash
# Launch specific activity
adb shell am start -n <package>/<activity>

# Or tap through navigation (e.g., bottom tab)
adb shell input tap <x> <y>
sleep 1
```

#### Step 2: Capture the initial state
```bash
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml /tmp/ui_current.xml
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png /tmp/screen_01.png
```

Read the UI XML to understand what's on screen — find clickable elements, text fields, their coordinates and resource-ids.

#### Step 3: Interact and observe
Execute the user flow step by step:
- **Tap a button**: `adb shell input tap <x> <y>`
- **Type text**: `adb shell input text "hello"` (for ASCII) or use ADBKeyboard for Chinese
- **Swipe/scroll**: `adb shell input swipe <x1> <y1> <x2> <y2> <duration_ms>`
- **Press back**: `adb shell input keyevent 4`
- **Press home**: `adb shell input keyevent 3`

After each action, wait briefly (`sleep 1`), then dump UI + screenshot to verify the result.

#### Step 4: Verify the outcome
Check whether the expected result occurred:
- **Visual**: Does the screenshot show the expected screen/content?
- **State**: Did data persist? (Check via UI — e.g., reopen the screen, check if item appears in list)
- **Feedback**: Did the user get confirmation (toast, snackbar, navigation)?
- **Error handling**: What happens with invalid input? (empty fields, special characters, extremely long text)

### Phase 5: Edge Case Testing

For each feature, also test these common failure modes:

| Scenario | How to test |
|----------|-------------|
| Empty submission | Leave fields blank, tap submit |
| Rapid double-tap | Tap the same button twice quickly |
| Back button mid-flow | Press back during multi-step process |
| Rotation | `adb shell settings put system accelerometer_rotation 1` then rotate |
| Long text | Input 500+ characters into text fields |
| Special characters | Input `<script>`, emojis, newlines |
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

## ADB Tips for Chinese Text Input

Standard `adb shell input text` doesn't handle Chinese. Options:

1. **ADBKeyboard** (recommended): Install ADBKeyboard.apk, set as default input method:
   ```bash
   adb install ADBKeyboard.apk
   adb shell settings put secure default_input_method com.android.adbkeyboard/.AdbIME
   ```
   Then: `adb shell am broadcast -a ADB_INPUT_TEXT --es msg '你好世界'`

2. **Unicode escape**: `adb shell input text '%E4%BD%A0%E5%A5%BD'` (unreliable across devices)

3. **Paste via clipboard**: Copy text to clipboard via `adb shell service call clipboard 2 i32 1 s16 "text"` then paste with `adb shell input keyevent 279` (complex, device-dependent)

## Working with UI Hierarchy XML

After `uiautomator dump`, the XML contains all visible UI nodes:

```xml
<node index="0" text="日记" resource-id="com.example:id/tab_diary"
      class="android.widget.TextView" package="com.example"
      content-desc="" checkable="false" checked="false" clickable="true"
      enabled="true" focusable="true" focused="false"
      scrollable="false" long-clickable="false" password="false"
      selected="false" bounds="[200,1800][400,1900]" />
```

Key attributes for finding elements:
- `text` — visible text content
- `resource-id` — stable identifier (preferred for targeting)
- `bounds` — screen coordinates for tap targets: `[left,top][right,bottom]`
- `clickable="true"` — can be tapped
- `enabled="false"` — grayed out / disabled

To tap the center of an element: `adb shell input tap <(left+right)/2> <(top+bottom)/2>`

## When Things Go Wrong

- **App crashes**: Immediately capture `adb logcat -d -s AndroidRuntime:E` and include in report
- **ANR (hang)**: `adb pull /data/anr/traces.txt` for stack traces
- **Screen not changing**: Dump UI again — maybe a dialog appeared, or the tap missed the target
- **UI dump fails**: Some system dialogs can't be dumped; use screenshot instead
- **Emulator not responding**: `adb emu kill` and restart

## Important Constraints

- You are simulating a user, not a developer. Don't read logcat to "understand" what happened — look at the screen first.
- Always dump UI AFTER every interaction. Screenshots alone miss disabled states, hidden elements, and content descriptions.
- If a feature requires login, handle that first. Don't skip features because of auth walls — log in and proceed.
- Don't modify app data or source code during testing. You're an observer, not a developer (unless explicitly asked).
- Save screenshots liberally. They're cheap and invaluable for the report.
