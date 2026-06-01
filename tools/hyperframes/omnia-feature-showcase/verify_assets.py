#!/usr/bin/env python3
"""Verify all HyperFrames scene references are valid."""

import os
import re

BASE_DIR = '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase'
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

def verify_references():
    """Check all scene files for valid image references."""
    errors = []
    warnings = []
    
    compositions_dir = os.path.join(BASE_DIR, 'compositions')
    
    for filename in os.listdir(compositions_dir):
        if not filename.endswith('.html'):
            continue
            
        filepath = os.path.join(compositions_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all background-image references
        matches = re.findall(r"background-image:\s*url\(['\"]?([^'\")\s]+)['\"]?\)", content)
        
        for match in matches:
            # Resolve relative path
            if match.startswith('../'):
                asset_path = os.path.join(BASE_DIR, match[3:])
            elif match.startswith('./'):
                asset_path = os.path.join(BASE_DIR, match[2:])
            else:
                asset_path = os.path.join(ASSETS_DIR, match)
            
            if not os.path.exists(asset_path):
                errors.append(f"{filename}: Missing asset {match}")
            else:
                size_kb = os.path.getsize(asset_path) / 1024
                if size_kb < 1:
                    warnings.append(f"{filename}: Asset {match} is very small ({size_kb:.1f} KB)")
    
    # Report results
    if errors:
        print("❌ Errors found:")
        for err in errors:
            print(f"   {err}")
    else:
        print("✅ All asset references are valid!")
    
    if warnings:
        print("\n⚠️  Warnings:")
        for warn in warnings:
            print(f"   {warn}")
    
    # List all assets
    print(f"\n📁 Assets in {ASSETS_DIR}:")
    for f in sorted(os.listdir(ASSETS_DIR)):
        if f.endswith('.png'):
            path = os.path.join(ASSETS_DIR, f)
            size_kb = os.path.getsize(path) / 1024
            print(f"   {f} ({size_kb:.1f} KB)")
    
    return len(errors) == 0

if __name__ == '__main__':
    success = verify_references()
    exit(0 if success else 1)
