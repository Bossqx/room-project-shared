#!/usr/bin/env python3
"""
JSON Fixer Script
Fixes common JSON errors including:
- Truncated content
- Missing closing brackets/braces
- Incomplete strings
- Trailing commas
"""

import json
import re
from typing import Optional, Tuple


def fix_truncated_json(json_str: str) -> Tuple[str, list]:
    """
    Attempts to fix truncated or malformed JSON.
    Returns the fixed JSON string and a list of fixes applied.
    """
    fixes_applied = []
    if isinstance(json_str, str):
        original = json_str.strip()
    elif isinstance(json_str, (list, dict)):
        original = json.dumps(json_str, ensure_ascii=False)
    else:
        original = str(json_str).strip()
    
    # Try parsing first - maybe it's already valid
    try:
        json.loads(original)
        return original, ["JSON is already valid"]
    except json.JSONDecodeError as e:
        fixes_applied.append(f"Original error: {e}")
    
    fixed = original
    
    # Fix 1: Close unclosed strings
    # Count quotes and check if we need to close a string
    in_string = False
    escape_next = False
    last_quote_pos = -1
    
    for i, char in enumerate(fixed):
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            if in_string:
                last_quote_pos = i
    
    if in_string:
        # String wasn't closed - close it
        fixed = fixed + '"'
        fixes_applied.append("Closed unclosed string")
    
    # Fix 2: Remove trailing incomplete content after last valid structure
    # Try to find a good cutoff point
    def find_last_complete_item(s: str) -> str:
        """Find the last complete JSON item in an array."""
        # Look for patterns like }, or } at the end
        patterns = [
            (r',\s*$', ''),  # Remove trailing comma
            (r'}\s*$', '}'),  # Keep closing brace
            (r'"\s*$', '"'),  # Keep closing quote
        ]
        
        for pattern, replacement in patterns:
            s = re.sub(pattern, replacement, s)
        
        return s
    
    fixed = find_last_complete_item(fixed)
    
    # Fix 3: Balance brackets and braces
    def count_unmatched(s: str) -> dict:
        """Count unmatched brackets/braces (ignoring those in strings)."""
        counts = {'[': 0, ']': 0, '{': 0, '}': 0}
        in_string = False
        escape_next = False
        
        for char in s:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string and char in counts:
                counts[char] += 1
        
        return {
            'open_brackets': counts['['] - counts[']'],
            'open_braces': counts['{'] - counts['}']
        }
    
    unmatched = count_unmatched(fixed)
    
    # Close unclosed braces first, then brackets
    if unmatched['open_braces'] > 0:
        fixed = fixed.rstrip()
        # Check if we need to complete a key-value pair
        if fixed.endswith(':'):
            fixed += ' null'
            fixes_applied.append("Added null for incomplete value")
        elif fixed.endswith(','):
            fixed = fixed[:-1]
            fixes_applied.append("Removed trailing comma")
        
        fixed += '}' * unmatched['open_braces']
        fixes_applied.append(f"Added {unmatched['open_braces']} closing brace(s)")
    
    if unmatched['open_brackets'] > 0:
        fixed = fixed.rstrip()
        if fixed.endswith(','):
            fixed = fixed[:-1]
            fixes_applied.append("Removed trailing comma before closing bracket")
        
        fixed += ']' * unmatched['open_brackets']
        fixes_applied.append(f"Added {unmatched['open_brackets']} closing bracket(s)")
    
    # Fix 4: Try to validate and if still broken, try more aggressive fixes
    try:
        json.loads(fixed)
        return fixed, fixes_applied
    except json.JSONDecodeError as e:
        fixes_applied.append(f"Still invalid after basic fixes: {e}")
    
    # More aggressive fix: find last complete object in array
    def extract_valid_portion(s: str) -> str:
        """Try to extract the largest valid JSON portion."""
        # For arrays, try to find the last complete object
        if s.strip().startswith('['):
            # Find all potential object endings
            depth_brace = 0
            depth_bracket = 0
            in_string = False
            escape_next = False
            last_valid_end = -1
            
            for i, char in enumerate(s):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                    
                if char == '{':
                    depth_brace += 1
                elif char == '}':
                    depth_brace -= 1
                    if depth_brace == 0 and depth_bracket == 1:
                        last_valid_end = i
                elif char == '[':
                    depth_bracket += 1
                elif char == ']':
                    depth_bracket -= 1
            
            if last_valid_end > 0:
                return s[:last_valid_end + 1] + ']'
        
        return s
    
    fixed = extract_valid_portion(original)
    fixes_applied.append("Extracted valid portion of JSON array")
    
    # Final validation
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError as e:
        fixes_applied.append(f"Final error: {e}")
        return fixed


def fix_json_file(input_path: str, output_path: Optional[str] = None) -> dict:
    """
    Fix a JSON file and optionally save to a new file.
    Returns a dict with results.
    """
    if output_path is None:
        output_path = input_path.replace('.json', '_fixed.json')
        if output_path == input_path:
            output_path = input_path + '.fixed'
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fixed_content, fixes = fix_truncated_json(content)
    
    # Try to parse the fixed content
    try:
        parsed = json.loads(fixed_content)
        is_valid = True
        
        # Save the fixed file with proper formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        
        item_count = len(parsed) if isinstance(parsed, list) else 1
        
    except json.JSONDecodeError as e:
        is_valid = False
        parsed = None
        item_count = 0
        
        # Save the attempted fix anyway
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
    # return {
    #     'fixes_applied': fixes,
    # }

    
    return {
        'input_path': input_path,
        'output_path': output_path,
        'is_valid': is_valid,
        'fixes_applied': fixes,
        'item_count': item_count
    }


# def main():
#     import sys
    
#     if len(sys.argv) < 2:
#         print("Usage: python fix_json.py <input_file> [output_file]")
#         print("\nExample:")
#         print("  python fix_json.py broken.json fixed.json")
#         sys.exit(1)
    
#     input_file = sys.argv[1]
#     output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
#     result = fix_json_file(input_file, output_file)
    
#     print(f"\n{'='*60}")
#     print("JSON Fix Results")
#     print(f"{'='*60}")
#     print(f"Input:  {result['input_path']}")
#     print(f"Output: {result['output_path']}")
#     print(f"Valid:  {'✓ Yes' if result['is_valid'] else '✗ No'}")
#     if result['is_valid']:
#         print(f"Items:  {result['item_count']}")
#     print(f"\nFixes applied:")
#     for i, fix in enumerate(result['fixes_applied'], 1):
#         print(f"  {i}. {fix}")
#     print(f"{'='*60}\n")


# if __name__ == "__main__":
#     main()