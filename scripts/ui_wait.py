#!/usr/bin/env python3
"""Poll uiautomator dump until a target element appears or disappears.

Usage:
    python ui_wait.py --text "日记详情" --timeout 10
    python ui_wait.py --id "btn_submit" --timeout 15
    python ui_wait.py --text "加载中" --gone --timeout 30    # wait for element to disappear
    python ui_wait.py --contains "成功" --timeout 10

Exit code: 0 = condition met, 1 = timeout
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

# Import find logic from sibling
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui_find import find_elements


def dump_ui(xml_path: str) -> bool:
    """Run uiautomator dump and pull XML. Returns True on success."""
    try:
        subprocess.run(
            ['adb', 'shell', 'uiautomator', 'dump', '/sdcard/_uiwait.xml'],
            capture_output=True, timeout=5,
        )
        result = subprocess.run(
            ['adb', 'pull', '/sdcard/_uiwait.xml', xml_path],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0 and os.path.exists(xml_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def wait_for_element(text=None, rid=None, contains=None, gone=False, timeout=10, poll_interval=0.8):
    """Poll until element appears (or disappears if gone=True)."""
    start = time.time()
    attempt = 0

    while time.time() - start < timeout:
        attempt += 1
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            xml_path = f.name

        try:
            if not dump_ui(xml_path):
                time.sleep(poll_interval)
                continue

            results = find_elements(xml_path, text=text, rid=rid, contains=contains)

            if gone:
                if not results:
                    elapsed = time.time() - start
                    print(f"GONE: element disappeared after {elapsed:.1f}s (attempt {attempt})")
                    return True
            else:
                if results:
                    elapsed = time.time() - start
                    r = results[0]
                    print(f"FOUND: text=\"{r['text']}\" after {elapsed:.1f}s "
                          f"→ tap({r['tap_x']}, {r['tap_y']})")
                    return True
        finally:
            try:
                os.unlink(xml_path)
            except OSError:
                pass

        time.sleep(poll_interval)

    print(f"TIMEOUT: element {'gone' if gone else 'not found'} after {timeout}s")
    return False


def main():
    parser = argparse.ArgumentParser(description='Wait for UI element to appear/disappear')
    parser.add_argument('--text', help='Exact text to find')
    parser.add_argument('--id', dest='rid', help='Resource-id to find')
    parser.add_argument('--contains', help='Partial text match')
    parser.add_argument('--gone', action='store_true', help='Wait for element to disappear')
    parser.add_argument('--timeout', type=float, default=10, help='Timeout in seconds (default: 10)')
    parser.add_argument('--interval', type=float, default=0.8, help='Poll interval in seconds (default: 0.8)')

    args = parser.parse_args()

    if not args.text and not args.rid and not args.contains:
        print("ERROR: Specify --text, --id, or --contains", file=sys.stderr)
        sys.exit(2)

    success = wait_for_element(
        text=args.text,
        rid=args.rid,
        contains=args.contains,
        gone=args.gone,
        timeout=args.timeout,
        poll_interval=args.interval,
    )
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
