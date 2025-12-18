#!/usr/bin/env python
import subprocess
import os
import sys

# Устанавливаем рабочую директорию
os.chdir(r"c:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1")

def run_command(cmd, description):
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"Return code: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

# Выполняем команды git
commands = [
    ("git status", "Checking git status"),
    ("git add .", "Adding all files"),
    ('git commit -m "Update all files - full project sync"', "Committing changes"),
    ("git remote remove origin", "Removing old remote (if exists)"),
    ("git remote add origin https://github.com/ValeryMukhin1712/tournaments.git", "Setting remote origin"),
    ("git push -u origin main --force", "Pushing to main with force")
]

for cmd, desc in commands:
    if not run_command(cmd, desc):
        print(f"Failed at: {desc}")
        sys.exit(1)

print("\nAll commands completed successfully!")