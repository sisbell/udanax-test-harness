#!/usr/bin/env python3
"""Compare golden test outputs from two backends.

Walks both golden directories, compares each scenario operation by operation,
classifies differences, and reports per-scenario results.

Usage:
    PYTHONPATH=. python compare_golden.py --reference ../golden --actual /tmp/my-golden
    PYTHONPATH=. python compare_golden.py --reference ../golden --actual /tmp/my-golden --verbose
    PYTHONPATH=. python compare_golden.py --reference ../golden --actual /tmp/my-golden --category links
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Tumbler pattern: digits separated by dots (e.g., "1.1.0.1.0.1", "0.14")
TUMBLER_RE = re.compile(r'^[0-9]+(\.[0-9]+)*$')


def is_tumbler(value):
    """Check if a string looks like a tumbler address or offset."""
    return isinstance(value, str) and bool(TUMBLER_RE.match(value))


def normalize_tumbler(s):
    """Normalize a tumbler string by stripping leading zero digits.

    "0.0.0.0.0.0.0.0.14" and "0.14" represent the same tumbler.
    Normalize to the shortest form.
    """
    parts = s.split('.')
    if not parts:
        return s
    # Parse as tumbler: first element is exponent (count of leading zeros)
    try:
        exp = int(parts[0])
        digits = [0] * exp + [int(p) for p in parts[1:]]
    except (ValueError, IndexError):
        return s

    # Re-encode: find first non-zero
    first_nonzero = 0
    for i, d in enumerate(digits):
        if d != 0:
            first_nonzero = i
            break
    else:
        # All zeros
        return '0'

    result = str(first_nonzero)
    for d in digits[first_nonzero:]:
        result += '.' + str(d)
    return result


def classify_value_diff(ref_val, act_val):
    """Classify a difference between two values.

    Returns:
        'match'    - values are identical
        'encoding' - same tumbler, different encoding (e.g., leading zeros)
        'address'  - both are tumblers but different values
        'content'  - non-tumbler difference (behavioral)
    """
    if ref_val == act_val:
        return 'match'

    # Both tumblers?
    if is_tumbler(ref_val) and is_tumbler(act_val):
        if normalize_tumbler(ref_val) == normalize_tumbler(act_val):
            return 'encoding'
        return 'address'

    # Lists of tumblers?
    if isinstance(ref_val, list) and isinstance(act_val, list):
        if len(ref_val) == len(act_val):
            all_tumbler = True
            for r, a in zip(ref_val, act_val):
                if is_tumbler(r) and is_tumbler(a):
                    continue
                all_tumbler = False
                break
            if all_tumbler:
                return 'address'

    return 'content'


def classify_dict_diff(ref_dict, act_dict):
    """Classify the difference between two dicts (e.g., an operation).

    Returns the worst classification found across all fields:
        'match' < 'encoding' < 'address' < 'content' < 'structural'
    """
    severity = {'match': 0, 'encoding': 1, 'address': 2, 'content': 3, 'structural': 4}
    worst = 'match'

    all_keys = set(list(ref_dict.keys()) + list(act_dict.keys()))
    # Skip comment/note fields — they're documentation, not behavior
    skip = {'comment', 'note', 'description'}

    for key in all_keys:
        if key in skip:
            continue
        if key not in ref_dict or key not in act_dict:
            return 'structural'

        ref_v = ref_dict[key]
        act_v = act_dict[key]

        if ref_v == act_v:
            continue

        if isinstance(ref_v, str) and isinstance(act_v, str):
            cls = classify_value_diff(ref_v, act_v)
        elif isinstance(ref_v, list) and isinstance(act_v, list):
            cls = classify_list_diff(ref_v, act_v)
        elif isinstance(ref_v, dict) and isinstance(act_v, dict):
            cls = classify_dict_diff(ref_v, act_v)
        else:
            cls = 'content'

        if severity.get(cls, 4) > severity.get(worst, 0):
            worst = cls

    return worst


def classify_list_diff(ref_list, act_list):
    """Classify difference between two lists."""
    if len(ref_list) != len(act_list):
        return 'structural'

    severity = {'match': 0, 'encoding': 1, 'address': 2, 'content': 3, 'structural': 4}
    worst = 'match'

    for ref_item, act_item in zip(ref_list, act_list):
        if ref_item == act_item:
            continue
        if isinstance(ref_item, str) and isinstance(act_item, str):
            cls = classify_value_diff(ref_item, act_item)
        elif isinstance(ref_item, dict) and isinstance(act_item, dict):
            cls = classify_dict_diff(ref_item, act_item)
        elif isinstance(ref_item, list) and isinstance(act_item, list):
            cls = classify_list_diff(ref_item, act_item)
        else:
            cls = 'content'

        if severity.get(cls, 4) > severity.get(worst, 0):
            worst = cls

    return worst


def compare_scenario(ref_data, act_data):
    """Compare two scenario JSON objects.

    Returns:
        classification: 'match', 'encoding', 'address', 'content', 'structural'
        details: list of per-operation diffs
    """
    ref_ops = ref_data.get('operations', [])
    act_ops = act_data.get('operations', [])

    if len(ref_ops) != len(act_ops):
        return 'structural', [{
            'issue': 'operation_count',
            'reference': len(ref_ops),
            'actual': len(act_ops)
        }]

    severity = {'match': 0, 'encoding': 1, 'address': 2, 'content': 3, 'structural': 4}
    worst = 'match'
    details = []

    for i, (ref_op, act_op) in enumerate(zip(ref_ops, act_ops)):
        cls = classify_dict_diff(ref_op, act_op)
        if cls != 'match':
            detail = {'operation': i, 'classification': cls}

            # Find which fields differ
            diffs = {}
            for key in set(list(ref_op.keys()) + list(act_op.keys())):
                if key in ('comment', 'note', 'description'):
                    continue
                ref_v = ref_op.get(key)
                act_v = act_op.get(key)
                if ref_v != act_v:
                    diffs[key] = {'reference': ref_v, 'actual': act_v}
            detail['fields'] = diffs
            details.append(detail)

        if severity.get(cls, 4) > severity.get(worst, 0):
            worst = cls

    return worst, details


def main():
    parser = argparse.ArgumentParser(description="Compare golden test outputs")
    parser.add_argument("--reference", required=True, help="Reference golden directory")
    parser.add_argument("--actual", required=True, help="Actual golden directory to compare")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-operation diffs")
    parser.add_argument("--category", help="Only compare this category")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    ref_dir = Path(args.reference)
    act_dir = Path(args.actual)

    if not ref_dir.exists():
        print(f"Error: reference directory not found: {ref_dir}")
        sys.exit(2)
    if not act_dir.exists():
        print(f"Error: actual directory not found: {act_dir}")
        sys.exit(2)

    # Find all scenarios
    ref_files = sorted(ref_dir.rglob("*.json"))
    act_files_set = {f.relative_to(act_dir) for f in act_dir.rglob("*.json")}

    results = {
        'match': [],
        'encoding': [],
        'address': [],
        'content': [],
        'structural': [],
        'ref_only': [],
        'actual_only': [],
    }

    all_results = []  # for JSON output

    for ref_file in ref_files:
        rel = ref_file.relative_to(ref_dir)
        category = rel.parts[0] if len(rel.parts) > 1 else ''

        if args.category and category != args.category:
            continue

        act_file = act_dir / rel
        scenario_name = f"{category}/{rel.stem}"

        if not act_file.exists():
            results['ref_only'].append(scenario_name)
            all_results.append({'scenario': scenario_name, 'classification': 'ref_only'})
            continue

        act_files_set.discard(rel)

        with open(ref_file) as f:
            ref_data = json.load(f)
        with open(act_file) as f:
            act_data = json.load(f)

        classification, details = compare_scenario(ref_data, act_data)
        results[classification].append(scenario_name)
        all_results.append({
            'scenario': scenario_name,
            'classification': classification,
            'details': details if details else None
        })

        if not args.json and classification != 'match':
            label = {
                'encoding': 'ENCODING',
                'address': 'ADDRESS',
                'content': 'CONTENT',
                'structural': 'STRUCTURAL',
            }[classification]

            if args.verbose:
                print(f"  {label:10s}  {scenario_name}")
                for d in details:
                    op_idx = d['operation']
                    op_cls = d['classification']
                    fields = d.get('fields', {})
                    for field, vals in fields.items():
                        ref_v = vals['reference']
                        act_v = vals['actual']
                        # Truncate long values
                        ref_s = str(ref_v)[:60]
                        act_s = str(act_v)[:60]
                        print(f"             op[{op_idx}].{field}: {ref_s}")
                        print(f"             {'':>{len(f'op[{op_idx}].{field}')}s}  {act_s}")

    # Check for actual-only files
    for rel in sorted(act_files_set):
        category = rel.parts[0] if len(rel.parts) > 1 else ''
        if args.category and category != args.category:
            continue
        scenario_name = f"{category}/{rel.stem}"
        results['actual_only'].append(scenario_name)
        all_results.append({'scenario': scenario_name, 'classification': 'actual_only'})

    # Output
    if args.json:
        json.dump({
            'summary': {k: len(v) for k, v in results.items()},
            'scenarios': all_results,
        }, sys.stdout, indent=2)
        print()
    else:
        total = sum(len(v) for v in results.values())
        match_count = len(results['match'])
        encoding_count = len(results['encoding'])
        address_count = len(results['address'])
        content_count = len(results['content'])
        structural_count = len(results['structural'])
        ref_only_count = len(results['ref_only'])
        actual_only_count = len(results['actual_only'])

        print()
        print(f"  {'match':12s}  {match_count:4d}  identical output")
        print(f"  {'encoding':12s}  {encoding_count:4d}  same values, different tumbler encoding")
        print(f"  {'address':12s}  {address_count:4d}  different addresses (allocation scheme)")
        print(f"  {'content':12s}  {content_count:4d}  different behavior (content, counts, results)")
        print(f"  {'structural':12s}  {structural_count:4d}  different operation count or missing fields")
        if ref_only_count:
            print(f"  {'ref only':12s}  {ref_only_count:4d}  in reference but not actual")
        if actual_only_count:
            print(f"  {'actual only':12s}  {actual_only_count:4d}  in actual but not reference")
        print(f"  {'':12s}  ----")
        print(f"  {'total':12s}  {total:4d}")
        print()

        if content_count > 0 and args.verbose:
            print("Content diffs (behavioral):")
            for name in results['content']:
                print(f"  {name}")
            print()

        if structural_count > 0 and args.verbose:
            print("Structural diffs:")
            for name in results['structural']:
                print(f"  {name}")
            print()

    # Exit code: 0 if everything matches or only has address/encoding diffs
    if results['content'] or results['structural']:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
