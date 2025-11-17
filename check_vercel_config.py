#!/usr/bin/env python3
"""
Script to verify Vercel configuration is correct.
"""
import os
import json
from pathlib import Path

print("Checking Vercel Configuration...\n")

# Check vercel.json exists
vercel_json = Path("vercel.json")
if vercel_json.exists():
    print("[OK] vercel.json exists")
    with open(vercel_json) as f:
        config = json.load(f)
        print(f"   Version: {config.get('version', 'Not specified')}")
        print(f"   Builds: {len(config.get('builds', []))} configured")
        print(f"   Routes: {len(config.get('routes', []))} configured")
        print(f"   Functions: {len(config.get('functions', {}))} configured")
else:
    print("[ERROR] vercel.json not found")

# Check api/index.py exists
api_index = Path("api/index.py")
if api_index.exists():
    print("[OK] api/index.py exists")
    with open(api_index) as f:
        content = f.read()
        if "from app import app" in content:
            print("   [OK] Imports Flask app correctly")
        if "app" in content:
            print("   [OK] Contains app variable")
else:
    print("[ERROR] api/index.py not found")

# Check app.py exists
app_py = Path("app.py")
if app_py.exists():
    print("[OK] app.py exists")
else:
    print("[ERROR] app.py not found")

# Check requirements.txt exists
requirements = Path("requirements.txt")
if requirements.exists():
    print("[OK] requirements.txt exists")
    with open(requirements) as f:
        deps = f.read()
        if "flask" in deps.lower():
            print("   [OK] Contains Flask dependency")
else:
    print("[ERROR] requirements.txt not found")

# Check static and templates directories
static_dir = Path("static")
templates_dir = Path("templates")
if static_dir.exists():
    print("[OK] static/ directory exists")
if templates_dir.exists():
    print("[OK] templates/ directory exists")

# Try importing the app
print("\n🧪 Testing app import...")
try:
    import sys
    sys.path.insert(0, str(Path.cwd()))
    from api.index import app
    print(f"[OK] App imported successfully: {type(app).__name__}")
    print(f"   App routes: {len(app.url_map._rules)}")
except Exception as e:
    print(f"[ERROR] Failed to import app: {e}")

print("\n[OK] Configuration check complete!")

