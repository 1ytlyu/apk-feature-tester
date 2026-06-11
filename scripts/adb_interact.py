#!/usr/bin/env python3
"""High-level ADB interaction with semantic locating, polling wait, and retry.

Usage:
    # Tap element by text, wait for confirmation
    python adb_interact.py tap --text "保存" --wait-after "已保存" --retries 3

    # Tap element by resource-id
    python adb_interact.py tap --id "btn_submit"

    # Tap and wait for screen transition
    python adb_interact.py tap --text "日记" --wait-screen "日记详情" --timeout 10

    # Input text into a focused field
    python adb_interact.py input "你好世界"

    # Navigate: tap element, wait for new screen
    python adb_interact.py tap --text "设置" --wait-screen "账号安全"

    # Scroll down until element appears
    python adb_interact.py scroll-find --text "隐私政策" --max-scrolls 5

Exit code: 0 = success, 1 = failed after retries
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_find import find_elements
from ui_wait import wait_for_element, dump_ui
from adb_input import input_text as adb_input_text


def run_adb(*args, check=True):
    """Run an ADB command."""
    cmd = ['adb'] + list(args)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=check)
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        print("ERROR: adb not found in PATH", file=sys.stderr)
        sys.exit(2)


def find_and_tap(text=None, rid=None, contains=None) -> bool:
    """Find element and tap its center. Returns True on success."""
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
        xml_path = f.name

    try:
        if not dump_ui(xml_path):
            return False
        results = find_elements(xml_path, text=text, rid=rid, contains=contains)
        if not results:
            return False

        target = results[0]
        x, y = target['tap_x'], target['tap_y']
        print(f"  TAP: \"{target['text']}\" at ({x}, {y})")
        run_adb('shell', 'input', 'tap', str(x), str(y))
        return True
    finally:
        try:
            os.unlink(xml_path)
        except OSError:
            pass


def tap_with_retry(text=None, rid=None, contains=None, wait_after=None,
                   wait_screen=None, timeout=10, retries=3) -> bool:
    """Find element, tap it, optionally wait for result. Retry on failure."""
    for attempt in range(1, retries + 1):
        print(f"Attempt {attempt}/{retries}:")

        # Step 1: Find and tap
        if not find_and_tap(text=text, rid=rid, contains=contains):
            print(f"  Element not found on screen")
            if attempt < retries:
                print(f"  Retrying in 1s...")
                time.sleep(1)
            continue

        # Step 2: Wait for expected result
        if wait_after:
            time.sleep(0.5)  # Brief pause before polling
            if wait_for_element(text=wait_after, timeout=timeout):
                print(f"  SUCCESS: confirmation \"{wait_after}\" appeared")
                return True
            else:
                print(f"  WARNING: confirmation \"{wait_after}\" not found within {timeout}s")
                if attempt < retries:
                    time.sleep(1)
                continue

        if wait_screen:
            time.sleep(0.5)
            if wait_for_element(text=wait_screen, timeout=timeout):
                print(f"  SUCCESS: screen \"{wait_screen}\" loaded")
                return True
            else:
                print(f"  WARNING: screen \"{wait_screen}\" not loaded within {timeout}s")
                if attempt < retries:
                    time.sleep(1)
                continue

        # No wait condition — tap was sufficient
        time.sleep(0.3)
        print(f"  SUCCESS: tapped")
        return True

    print(f"FAILED after {retries} attempts")
    return False


def scroll_find(text=None, rid=None, max_scrolls=5, direction='down') -> bool:
    """Scroll the screen until an element is found."""
    # Get screen size for scroll coordinates
    result = run_adb('shell', 'wm', 'size')
    if not result or result.returncode != 0:
        print("ERROR: cannot get screen size", file=sys.stderr)
        return False

    # Parse "Physical size: 1080x1920"
    import re
    m = re.search(r'(\d+)x(\d+)', result.stdout or '')
    if not m:
        print(f"ERROR: cannot parse screen size: {result.stdout}", file=sys.stderr)
        return False

    w, h = int(m.group(1)), int(m.group(2))

    # Scroll coordinates: center of screen
    cx = w // 2
    scroll_up = (cx, h * 2 // 3, cx, h // 3, 400)    # swipe up = scroll down
    scroll_down = (cx, h // 3, cx, h * 2 // 3, 400)   # swipe down = scroll up

    scroll_coords = scroll_up if direction == 'down' else scroll_down

    for i in range(max_scrolls):
        # Check if element is already visible
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            xml_path = f.name

        try:
            if dump_ui(xml_path):
                results = find_elements(xml_path, text=text, rid=rid)
                if results:
                    r = results[0]
                    print(f"FOUND after {i} scrolls: \"{r['text']}\" → tap({r['tap_x']}, {r['tap_y']})")
                    return True
        finally:
            try:
                os.unlink(xml_path)
            except OSError:
                pass

        # Scroll
        print(f"  Scrolling {direction} ({i+1}/{max_scrolls})...")
        run_adb('shell', 'input', 'swipe',
                str(scroll_coords[0]), str(scroll_coords[1]),
                str(scroll_coords[2]), str(scroll_coords[3]),
                str(scroll_coords[4]))
        time.sleep(0.8)

    # Final check after last scroll
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
        xml_path = f.name
    try:
        if dump_ui(xml_path):
            results = find_elements(xml_path, text=text, rid=rid)
            if results:
                r = results[0]
                print(f"FOUND after {max_scrolls} scrolls: \"{r['text']}\" → tap({r['tap_x']}, {r['tap_y']})")
                return True
    finally:
        try:
            os.unlink(xml_path)
        except OSError:
            pass

    print(f"NOT FOUND after {max_scrolls} scrolls")
    return False


def main():
    parser = argparse.ArgumentParser(description='High-level ADB interaction with retry')
    subparsers = parser.add_subparsers(dest='action', required=True)

    # tap subcommand
    tap_p = subparsers.add_parser('tap', help='Find and tap an element')
    tap_p.add_argument('--text', help='Element text')
    tap_p.add_argument('--id', dest='rid', help='Element resource-id')
    tap_p.add_argument('--contains', help='Partial text match')
    tap_p.add_argument('--wait-after', help='Text to wait for after tap (confirmation)')
    tap_p.add_argument('--wait-screen', help='Screen text to wait for after tap (navigation)')
    tap_p.add_argument('--timeout', type=float, default=10, help='Wait timeout (default: 10s)')
    tap_p.add_argument('--retries', type=int, default=3, help='Max retry attempts (default: 3)')

    # input subcommand
    input_p = subparsers.add_parser('input', help='Input text into focused field')
    input_p.add_argument('text', help='Text to input')

    # scroll-find subcommand
    scroll_p = subparsers.add_parser('scroll-find', help='Scroll until element is found')
    scroll_p.add_argument('--text', help='Element text')
    scroll_p.add_argument('--id', dest='rid', help='Element resource-id')
    scroll_p.add_argument('--max-scrolls', type=int, default=5, help='Max scroll attempts')
    scroll_p.add_argument('--direction', choices=['up', 'down'], default='down', help='Scroll direction')

    args = parser.parse_args()

    if args.action == 'tap':
        if not args.text and not args.rid and not args.contains:
            print("ERROR: specify --text, --id, or --contains", file=sys.stderr)
            sys.exit(2)
        success = tap_with_retry(
            text=args.text, rid=args.rid, contains=args.contains,
            wait_after=args.wait_after, wait_screen=args.wait_screen,
            timeout=args.timeout, retries=args.retries,
        )
        sys.exit(0 if success else 1)

    elif args.action == 'input':
        adb_input_text(args.text)
        print(f"INPUT: \"{args.text}\"")

    elif args.action == 'scroll-find':
        if not args.text and not args.rid:
            print("ERROR: specify --text or --id", file=sys.stderr)
            sys.exit(2)
        success = scroll_find(
            text=args.text, rid=args.rid,
            max_scrolls=args.max_scrolls, direction=args.direction,
        )
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
