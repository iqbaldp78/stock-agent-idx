#!/usr/bin/env python3
"""Fix hardcoded hex colors in TSX files - replace with theme tokens"""

import os
import re
from pathlib import Path

# Color mapping: hardcoded hex -> theme token
REPLACEMENTS = [
    # Accent/Purple
    (r'focus:border-\[#7C3AED\]', 'focus:border-accent'),
    (r'bg-gradient-to-r from-\[#7C3AED\] to-\[#7C3AED\]', 'bg-accent'),
    (r'text-\[#7C3AED\]', 'text-accent'),
    (r'bg-\[#7C3AED\]', 'bg-accent'),
    (r'border-\[#7C3AED\]', 'border-accent'),
    (r'shadow-indigo-500/20', 'shadow-accent/20'),
    (r'shadow-purple-500/20', 'shadow-accent/20'),

    # Profit/Green
    (r'text-\[#22C55E\]', 'text-profit'),
    (r'bg-\[#22C55E\]', 'bg-profit'),
    (r'border-\[#22C55E\]', 'border-profit'),

    # Loss/Red
    (r'text-\[#EF4444\]', 'text-loss'),
    (r'bg-\[#EF4444\]', 'bg-loss'),
    (r'border-\[#EF4444\]', 'border-loss'),

    # Warning/Amber
    (r'text-\[#F59E0B\]', 'text-warning'),
    (r'bg-\[#F59E0B\]', 'bg-warning'),
    (r'border-\[#F59E0B\]', 'border-warning'),

    # Info/Blue
    (r'text-\[#3B82F6\]', 'text-info'),
    (r'bg-\[#3B82F6\]', 'bg-info'),
    (r'border-\[#3B82F6\]', 'border-info'),
]

def fix_file(filepath):
    """Fix color tokens in a single file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Target files
web_frontend = Path('/home/hamboo/my-product/stock-agent-idx/web-frontend')
tsx_files = list(web_frontend.glob('src/**/*.tsx'))

fixed_count = 0
for tsx_file in tsx_files:
    if fix_file(tsx_file):
        print(f"✓ Fixed: {tsx_file.relative_to(web_frontend)}")
        fixed_count += 1
    else:
        print(f"- No changes: {tsx_file.relative_to(web_frontend)}")

print(f"\n✅ Fixed {fixed_count} files")
