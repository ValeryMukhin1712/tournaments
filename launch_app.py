#!/usr/bin/env python
import subprocess
import os
import sys

# Устанавливаем рабочую директорию
project_dir = r"c:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1"
os.chdir(project_dir)

print("Запуск Турнирного Ассистента...")
print(f"Рабочая директория: {os.getcwd()}")

# Путь к python.exe в виртуальном окружении
python_exe = os.path.join(project_dir, "venv", "Scripts", "python.exe")
app_py = os.path.join(project_dir, "app.py")

print(f"Python executable: {python_exe}")
print(f"App file: {app_py}")

# Проверяем существование файлов
if not os.path.exists(python_exe):
    print(f"Ошибка: Python executable не найден: {python_exe}")
    sys.exit(1)

if not os.path.exists(app_py):
    print(f"Ошибка: Файл приложения не найден: {app_py}")
    sys.exit(1)

print("Запускаем приложение...")

# Запускаем приложение
try:
    result = subprocess.run([python_exe, app_py], cwd=project_dir)
    print(f"Приложение завершено с кодом: {result.returncode}")
except KeyboardInterrupt:
    print("Приложение остановлено пользователем")
except Exception as e:
    print(f"Ошибка при запуске приложения: {e}")
    sys.exit(1)
