#!/usr/bin/env python3
"""Find UI elements in uiautomator dump XML by text, resource-id, or class.

Usage:
    python ui_find.py <ui.xml> --text "保存"
    python ui_find.py <ui.xml> --id "btn_submit"
    python ui_find.py <ui.xml> --text "日记" --class "TextView"
    python ui_find.py <ui.xml> --contains "日"       # partial text match
    python ui_find.py <ui.xml> --all                  # list all clickable elements

Exit code: 0 = found, 1 = not found
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET


def parse_bounds(bounds_str: str) -> tuple[int, int, int, int] | None:
    """Parse bounds string like '[200,1800][400,1900]' into (left, top, right, bottom)."""
    m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def center_of(bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    """Calculate center point from (left, top, right, bottom)."""
    return (bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2


def find_elements(xml_path: str, text=None, rid=None, cls=None, contains=None, clickable_only=False):
    """Find elements matching criteria in uiautomator XML dump."""
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse XML: {e}", file=sys.stderr)
        return []

    results = []
    for node in tree.iter('node'):
        attrs = node.attrib
        node_text = attrs.get('text', '')
        node_id = attrs.get('resource-id', '')
        node_class = attrs.get('class', '')
        node_clickable = attrs.get('clickable', 'false')
        node_enabled = attrs.get('enabled', 'true')
        node_bounds = attrs.get('bounds', '')

        # Filter by clickable if requested
        if clickable_only and node_clickable != 'true':
            continue

        # Filter by enabled
        if node_enabled != 'true':
            continue

        # Match criteria
        match = True
        if text is not None and node_text != text:
            match = False
        if rid is not None and node_id != rid:
            match = False
        if cls is not None and cls not in node_class:
            match = False
        if contains is not None and contains not in node_text:
            match = False

        if match and node_bounds:
            bounds = parse_bounds(node_bounds)
            if bounds:
                cx, cy = center_of(bounds)
                results.append({
                    'text': node_text,
                    'resource-id': node_id,
                    'class': node_class,
                    'clickable': node_clickable,
                    'bounds': bounds,
                    'bounds_str': node_bounds,
                    'tap_x': cx,
                    'tap_y': cy,
                })

    return results


def main():
    parser = argparse.ArgumentParser(description='Find UI elements in uiautomator dump')
    parser.add_argument('xml', help='Path to uiautomator dump XML')
    parser.add_argument('--text', help='Exact text match')
    parser.add_argument('--id', dest='rid', help='Exact resource-id match')
    parser.add_argument('--class', dest='cls', help='Class name contains (e.g. TextView, Button)')
    parser.add_argument('--contains', help='Partial text match')
    parser.add_argument('--clickable', action='store_true', help='Only match clickable elements')
    parser.add_argument('--all', action='store_true', help='List all clickable elements')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if args.all:
        results = find_elements(args.xml, clickable_only=True)
    elif not args.text and not args.rid and not args.contains:
        print("ERROR: Specify --text, --id, --contains, or --all", file=sys.stderr)
        sys.exit(2)
    else:
        results = find_elements(
            args.xml,
            text=args.text,
            rid=args.rid,
            cls=args.cls,
            contains=args.contains,
            clickable_only=args.clickable,
        )

    if not results:
        print("NOT FOUND")
        sys.exit(1)

    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"FOUND: text=\"{r['text']}\" id=\"{r['resource-id']}\" "
                  f"bounds={r['bounds_str']} → tap({r['tap_x']}, {r['tap_y']})")

    sys.exit(0)


if __name__ == '__main__':
    main()
