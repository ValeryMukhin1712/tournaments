#!/usr/bin/env python
import subprocess
import sys
import os

# Устанавливаем рабочую директорию
os.chdir(r"c:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1")

# Путь к python.exe в виртуальном окружении
python_exe = r"c:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1\venv\Scripts\python.exe"
app_py = r"c:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1\app.py"

# Запускаем приложение
subprocess.run([python_exe, app_py])
