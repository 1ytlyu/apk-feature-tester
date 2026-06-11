#!/usr/bin/env python3
"""Unified ADB input with automatic Chinese text support.

Usage:
    python adb_input.py text "hello world"          # ASCII text
    python adb_input.py text "你好世界"               # Chinese (auto uses ADBKeyboard)
    python adb_input.py tap 500 1000                 # Tap at coordinates
    python adb_input.py swipe 500 1500 500 500 300   # Swipe (x1 y1 x2 y2 duration)
    python adb_input.py key 4                        # Key event (back=4, home=3, enter=66)
    python adb_input.py clear                        # Clear current text field

For Chinese input, ADBKeyboard is auto-installed and configured if needed.
The original IME is saved and restored after input.
"""

import subprocess
import sys
import time

ADB_KEYBOARD_PKG = 'com.android.adbkeyboard'
ADB_KEYBOARD_IME = f'{ADB_KEYBOARD_PKG}/.AdbIME'


def run_adb(*args, check=True):
    """Run an ADB command and return the result."""
    cmd = ['adb'] + list(args)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=check)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: adb {' '.join(args)}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("ERROR: adb not found in PATH", file=sys.stderr)
        sys.exit(2)


def get_current_ime() -> str:
    """Get the current input method."""
    result = run_adb('shell', 'settings', 'get', 'secure', 'default_input_method')
    if result and result.returncode == 0:
        return result.stdout.strip()
    return ''


def set_ime(ime: str):
    """Set the input method."""
    run_adb('shell', 'settings', 'put', 'secure', 'default_input_method', ime)


def is_adb_keyboard_installed() -> bool:
    """Check if ADBKeyboard is installed."""
    result = run_adb('shell', 'pm', 'list', 'packages', ADB_KEYBOARD_PKG, check=False)
    return result is not None and ADB_KEYBOARD_PKG in (result.stdout or '')


def install_adb_keyboard():
    """Install ADBKeyboard from the skill's assets directory."""
    # Look for ADBKeyboard.apk in common locations
    import glob
    import os

    search_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'assets', 'ADBKeyboard.apk'),
        os.path.expanduser('~/ADBKeyboard.apk'),
        '/tmp/ADBKeyboard.apk',
    ]

    apk_path = None
    for p in search_paths:
        matches = glob.glob(p)
        if matches:
            apk_path = matches[0]
            break

    if not apk_path:
        print("ERROR: ADBKeyboard.apk not found. Download from "
              "https://github.com/nicholascao/ADBKeyboard and place in assets/", file=sys.stderr)
        sys.exit(2)

    print(f"Installing ADBKeyboard from {apk_path}...")
    result = run_adb('install', '-r', apk_path)
    if result and result.returncode == 0:
        print("ADBKeyboard installed successfully")
    else:
        print(f"ERROR: Failed to install ADBKeyboard: {result.stderr if result else 'unknown'}", file=sys.stderr)
        sys.exit(2)


def setup_adb_keyboard():
    """Ensure ADBKeyboard is installed and set as IME. Returns original IME."""
    original_ime = get_current_ime()

    if not is_adb_keyboard_installed():
        install_adb_keyboard()

    # Set ADBKeyboard as current IME
    set_ime(ADB_KEYBOARD_IME)
    time.sleep(0.3)  # Let IME switch settle

    return original_ime


def restore_ime(original_ime: str):
    """Restore the original IME."""
    if original_ime and original_ime != ADB_KEYBOARD_IME:
        set_ime(original_ime)


def has_non_ascii(text: str) -> bool:
    """Check if text contains non-ASCII characters."""
    return any(ord(c) > 127 for c in text)


def input_text(text: str):
    """Input text, using ADBKeyboard for non-ASCII characters."""
    if not text:
        return

    if has_non_ascii(text):
        # Use ADBKeyboard for Chinese/Unicode
        original_ime = setup_adb_keyboard()
        try:
            result = run_adb('shell', 'am', 'broadcast',
                             '-a', 'ADB_INPUT_TEXT',
                             '--es', 'msg', text)
            if result and 'result=1' not in (result.stdout or ''):
                print(f"WARNING: ADBKeyboard broadcast may have failed: {result.stdout.strip()}", file=sys.stderr)
        finally:
            # Small delay before IME switch
            time.sleep(0.2)
            restore_ime(original_ime)
    else:
        # Standard ASCII input
        # Escape special characters for shell
        escaped = text.replace(' ', '%s').replace("'", "\\'").replace('"', '\\"')
        run_adb('shell', 'input', 'text', escaped)


def tap(x: int, y: int):
    """Tap at coordinates."""
    run_adb('shell', 'input', 'tap', str(x), str(y))


def swipe(x1: int, y1: int, x2: int, y2: int, duration: int = 300):
    """Swipe from (x1,y1) to (x2,y2) over duration ms."""
    run_adb('shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration))


def key_event(code: int):
    """Send a key event."""
    run_adb('shell', 'input', 'keyevent', str(code))


def clear_text():
    """Clear current text field (select all + delete)."""
    # Select all: Ctrl+A (keyevent 29 with META_CTRL_ON)
    run_adb('shell', 'input', 'keyevent', '--longpress', '29')
    time.sleep(0.1)
    # Delete
    run_adb('shell', 'input', 'keyevent', '67')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    action = sys.argv[1].lower()

    if action == 'text':
        if len(sys.argv) < 3:
            print("ERROR: specify text to input", file=sys.stderr)
            sys.exit(2)
        input_text(sys.argv[2])

    elif action == 'tap':
        if len(sys.argv) < 4:
            print("ERROR: specify x y coordinates", file=sys.stderr)
            sys.exit(2)
        tap(int(sys.argv[2]), int(sys.argv[3]))

    elif action == 'swipe':
        if len(sys.argv) < 6:
            print("ERROR: specify x1 y1 x2 y2 [duration]", file=sys.stderr)
            sys.exit(2)
        duration = int(sys.argv[6]) if len(sys.argv) > 6 else 300
        swipe(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), duration)

    elif action == 'key':
        if len(sys.argv) < 3:
            print("ERROR: specify key event code", file=sys.stderr)
            sys.exit(2)
        key_event(int(sys.argv[2]))

    elif action == 'clear':
        clear_text()

    else:
        print(f"ERROR: unknown action '{action}'. Use: text, tap, swipe, key, clear", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
