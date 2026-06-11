# ADB Command Reference

Quick-reference for APK feature testing. All commands run from host shell.

**Prefer the bundled Python scripts over raw ADB commands** — they handle element locating, polling waits, Chinese input, and retry automatically. Raw ADB is listed here for edge cases and device management.

---

## Script Quick Reference

All scripts are in `scripts/` and use only Python stdlib (no pip install needed).

### ui_find.py — Find Element

```bash
# Find by exact text
python scripts/ui_find.py /tmp/ui.xml --text "保存"

# Find by resource-id
python scripts/ui_find.py /tmp/ui.xml --id "com.app:id/btn_save"

# Find by partial text
python scripts/ui_find.py /tmp/ui.xml --contains "日"

# List all clickable elements
python scripts/ui_find.py /tmp/ui.xml --all

# Filter by class + clickable
python scripts/ui_find.py /tmp/ui.xml --class "Button" --clickable

# JSON output for programmatic use
python scripts/ui_find.py /tmp/ui.xml --all --json
```

Output: `FOUND: text="保存" id="com.app:id/save" bounds=[900,1800][1080,1920] → tap(990, 1860)`

### ui_wait.py — Polling Wait

```bash
# Wait for element to appear (replaces sleep!)
python scripts/ui_wait.py --text "日记详情" --timeout 10

# Wait for element to disappear (e.g., loading spinner)
python scripts/ui_wait.py --text "加载中" --gone --timeout 30

# Wait by resource-id
python scripts/ui_wait.py --id "progress_bar" --gone --timeout 20

# Custom poll interval (default 0.8s)
python scripts/ui_wait.py --text "完成" --timeout 15 --interval 0.5
```

Exit code: 0 = found/gone, 1 = timeout.

### adb_input.py — Text Input (Chinese + ASCII)

```bash
# ASCII text
python scripts/adb_input.py text "hello world"

# Chinese text (auto-installs ADBKeyboard, switches IME, restores after)
python scripts/adb_input.py text "你好世界"

# Tap at coordinates (prefer adb_interact.py for semantic tap)
python scripts/adb_input.py tap 500 1000

# Swipe
python scripts/adb_input.py swipe 500 1500 500 500 300

# Key event
python scripts/adb_input.py key 4    # back
python scripts/adb_input.py key 66   # enter

# Clear current text field
python scripts/adb_input.py clear
```

### adb_interact.py — High-Level Interaction

```bash
# Tap by text (with 3 retries)
python scripts/adb_interact.py tap --text "保存" --retries 3

# Tap by resource-id
python scripts/adb_interact.py tap --id "com.app:id/btn_save"

# Tap + wait for confirmation text
python scripts/adb_interact.py tap --text "保存" --wait-after "保存成功" --timeout 5

# Tap + wait for screen transition
python scripts/adb_interact.py tap --text "日记" --wait-screen "日记详情" --timeout 10

# Scroll down until element appears
python scripts/adb_interact.py scroll-find --text "隐私政策" --max-scrolls 5

# Scroll up
python scripts/adb_interact.py scroll-find --text "顶部" --direction up --max-scrolls 3

# Input text (delegates to adb_input.py)
python scripts/adb_interact.py input "今天天气真好"
```

---

## Device Management (raw ADB)

```bash
# List connected devices
adb devices -l

# Start emulator (background)
~/Android/Sdk/emulator/emulator -avd <avd_name> &
adb wait-for-device

# Check device is ready
adb shell getprop sys.boot_completed   # returns "1" when ready

# Kill emulator
adb emu kill
```

## App Lifecycle

```bash
# Install APK
adb install -r path/to/app.apk          # -r = replace existing

# Uninstall
adb uninstall <package_name>

# Launch activity
adb shell am start -n <package>/<activity>
# Example: adb shell am start -n com.shendu.app/.ui.MainActivity

# Launch with extras
adb shell am start -n <package>/<activity> --es key "value" --ei key 123

# Force stop
adb shell am force-stop <package_name>

# Clear app data (fresh start)
adb shell pm clear <package_name>

# Get current foreground activity
adb shell dumpsys activity activities | grep mResumedActivity
```

## Screenshots

```bash
# Take screenshot
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png /tmp/screen.png

# Take screenshot and save directly (Android 10+)
adb exec-out screencap -p > /tmp/screen.png

# Screen recording (max 180s)
adb shell screenrecord /sdcard/record.mp4 --time-limit 30
adb pull /sdcard/record.mp4 /tmp/record.mp4
```

## Logcat (for crash/debug)

```bash
# Filter for crashes only
adb logcat -d -s AndroidRuntime:E

# Filter for app-specific logs
adb logcat -d | grep <package_name>

# Filter for ANR
adb logcat -d -s ActivityManager:E | grep ANR

# Clear logcat buffer
adb logcat -c

# Watch live (background)
adb logcat -s AndroidRuntime:E *:W &
```

## File Operations

```bash
# Pull file from device
adb pull /sdcard/file.txt /tmp/file.txt

# Push file to device
adb push /tmp/file.txt /sdcard/file.txt

# List app's private data (requires root or run-as)
adb shell run-as <package_name> ls files/
adb shell run-as <package_name> cat files/data.json

# Check shared preferences (debuggable builds)
adb shell run-as <package_name> cat /data/data/<package_name>/shared_prefs/*.xml
```

## Device Settings

```bash
# Get screen resolution
adb shell wm size

# Get screen density
adb shell wm density

# Toggle airplane mode (Android 6+)
adb shell settings put global airplane_mode_on 1
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true

# Disable airplane mode
adb shell settings put global airplane_mode_on 0
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false

# Toggle WiFi
adb shell svc wifi disable
adb shell svc wifi enable

# Set screen brightness
adb shell settings put system screen_brightness 255

# Keep screen on while plugged in
adb shell settings put global stay_on_while_plugged_in 3
```

## Permissions

```bash
# Grant permission
adb shell pm grant <package_name> android.permission.READ_CONTACTS

# Revoke permission
adb shell pm revoke <package_name> android.permission.READ_CONTACTS

# List all permissions
adb shell dumpsys package <package_name> | grep permission
```

## UI Inspection (raw, prefer scripts above)

```bash
# Dump UI hierarchy to XML
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml /tmp/ui.xml

# Dump and display (one-liner for quick check)
adb shell uiautomator dump /dev/tty 2>/dev/null | head -5
```

### XML Element Attributes

| Attribute | Meaning | Use |
|-----------|---------|-----|
| `text` | Visible text | Verify content, find element by label |
| `resource-id` | R.id reference | Most stable locator |
| `bounds` | `[left,top][right,bottom]` | Calculate tap coordinates |
| `clickable` | Can be tapped | Filter interactive elements |
| `enabled` | Not grayed out | Check if action is available |
| `selected` | Active/current tab | Verify navigation state |
| `scrollable` | Contains scrollable content | Know if swipe will work |
| `content-desc` | Accessibility label | Alternative locator |
| `password` | Is password field | Verify masking |
| `checked` | Toggle state | Verify switch/checkbox |

## Common Patterns (prefer scripts)

### Wait for screen to settle
```bash
# DON'T: sleep 2
# DO:
python scripts/ui_wait.py --text "expected_text" --timeout 10
```

### Find and tap element
```bash
# DON'T: grep XML, calculate coordinates, input tap
# DO:
python scripts/adb_interact.py tap --text "保存" --retries 3
```

### Verify element exists on screen
```bash
python scripts/ui_find.py /tmp/ui.xml --text "预期文本"
# Exit code 0 = found, 1 = not found
```

### Check if app is running
```bash
adb shell pidof <package_name>   # returns PID if running, empty if not
```

### Navigate to a specific screen via deep link
```bash
adb shell am start -a android.intent.action.VIEW -d "app://specific-screen"
```
