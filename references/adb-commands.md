# ADB Command Reference

Quick-reference for APK feature testing. All commands run from host shell.

## Device Management

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

## UI Interaction

### Taps and Swipes

```bash
# Tap at coordinates
adb shell input tap <x> <y>

# Long press (hold 2 seconds)
adb shell swipe <x> <y> <x> <y> 2000

# Swipe
adb shell input swipe <x1> <y1> <x2> <y2> [duration_ms]
# Scroll down:  adb shell input swipe 500 1500 500 500 300
# Scroll up:    adb shell input swipe 500 500 500 1500 300

# Drag (longer duration)
adb shell input swipe <x1> <y1> <x2> <y2> 1000
```

### Text Input

```bash
# Type ASCII text (cursor must be in a text field)
adb shell input text "hello"

# Type with spaces (escape spaces)
adb shell input text "hello%sworld"

# Chinese text via ADBKeyboard (must be installed and set as IME)
adb shell am broadcast -a ADB_INPUT_TEXT --es msg '你好世界'

# Clear existing text: select all + delete
adb shell input keyevent 29 --longpress   # Ctrl+A (select all)
adb shell input keyevent 67               # DEL key

# Alternative: triple-tap to select all, then type
adb shell input tap <x> <y>
adb shell input tap <x> <y>
adb shell input tap <x> <y>
adb shell input keyevent 67
```

### Key Events

```bash
# Back button
adb shell input keyevent 4    # KEYCODE_BACK

# Home button
adb shell input keyevent 3    # KEYCODE_HOME

# Recent apps
adb shell input keyevent 187  # KEYCODE_APP_SWITCH

# Enter/Done
adb shell input keyevent 66   # KEYCODE_ENTER

# Tab (move focus)
adb shell input keyevent 61   # KEYCODE_TAB

# Volume
adb shell input keyevent 24   # VOLUME_UP
adb shell input keyevent 25   # VOLUME_DOWN

# Power
adb shell input keyevent 26   # KEYCODE_POWER

# Menu
adb shell input keyevent 82   # KEYCODE_MENU

# Clipboard paste
adb shell input keyevent 279  # KEYCODE_PASTE
```

## UI Inspection

```bash
# Dump UI hierarchy to XML
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml /tmp/ui.xml

# Dump and display (one-liner for quick check)
adb shell uiautomator dump /dev/tty 2>/dev/null | head -5

# Read specific element info from dumped XML
# Look for: text, resource-id, bounds, clickable, enabled, selected
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

### Calculate Tap Target

```
bounds="[200,1800][400,1900]"
center_x = (200 + 400) / 2 = 300
center_y = (1800 + 1900) / 2 = 1850
→ adb shell input tap 300 1850
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

## Common Patterns

### Wait for screen to settle

```bash
sleep 2   # simple approach; UI transitions typically take 0.5-2s
```

### Find and tap element by text

```bash
# 1. Dump UI
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml /tmp/ui.xml

# 2. Find element with target text and extract bounds
grep -o 'text="保存"[^>]*bounds="\[[0-9,]*\]\[[0-9,]*\]"' /tmp/ui.xml

# 3. Parse bounds and calculate center, then tap
# (Manual or scripted parsing needed)
```

### Verify element exists on screen

```bash
adb shell uiautomator dump /sdcard/ui.xml
adb pull /sdcard/ui.xml /tmp/ui.xml
grep -q 'text="预期文本"' /tmp/ui.xml && echo "FOUND" || echo "NOT FOUND"
```

### Check if app is running

```bash
adb shell pidof <package_name>   # returns PID if running, empty if not
```

### Navigate to a specific screen via deep link

```bash
adb shell am start -a android.intent.action.VIEW -d "app://specific-screen"
```
