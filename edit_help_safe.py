#!/usr/bin/env python3
"""
Безопасный редактор Help-файла с автоматическим резервным копированием
"""

import os
import shutil
from datetime import datetime
import re

def create_backup(file_path):
    """Создает резервную копию файла с временной меткой"""
    if not os.path.exists(file_path):
        print(f"❌ Файл {file_path} не найден!")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    filename = os.path.basename(file_path)
    backup_path = os.path.join(backup_dir, f"{filename}.backup_{timestamp}")
    
    shutil.copy2(file_path, backup_path)
    print(f"✅ Резервная копия создана: {backup_path}")
    return backup_path

def extract_help_from_base():
    """Извлекает Help-контент из base.html"""
    base_path = "templates/base.html"
    if not os.path.exists(base_path):
        print(f"❌ Файл {base_path} не найден!")
        return None
    
    with open(base_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим блок help-content
    start_marker = '<div class="help-content">'
    end_marker = '</div>'
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("❌ Блок help-content не найден в base.html")
        return None
    
    # Находим закрывающий тег (первый после начала блока)
    end_idx = content.find('</div>', start_idx + len(start_marker))
    if end_idx == -1:
        print("❌ Закрывающий тег не найден")
        return None
    
    help_html = content[start_idx + len(start_marker):end_idx].strip()
    return help_html

def remove_icons(html_content):
    """Удаляет иконки FontAwesome из HTML для упрощения редактирования"""
    # Удаляем <i class="fas ..."></i> теги
    html_content = re.sub(r'<i\s+class="[^"]*"\s*></i>', '', html_content)
    html_content = re.sub(r'<i\s+class="[^"]*"\s*></i>', '', html_content)
    # Удаляем оставшиеся пробелы после удаления иконок
    html_content = re.sub(r'\s+', ' ', html_content)
    html_content = re.sub(r'>\s+<', '><', html_content)
    return html_content.strip()

def add_icons_back(html_content):
    """Добавляет иконки обратно в заголовки (базовая версия)"""
    # Простая замена заголовков с иконками
    icon_map = {
        '<h4>Pet project</h4>': '<h4><i class="fas fa-trophy me-2"></i>Pet project</h4>',
        '<h5>Роли пользователей</h5>': '<h5><i class="fas fa-users me-2"></i>Роли пользователей</h5>',
        '<h5>Администратор турниров</h5>': '<h5><i class="fas fa-crown me-2"></i>Администратор турниров</h5>',
        '<h6>Определение победителей:</h6>': '<h6><i class="fas fa-trophy me-2"></i>Определение победителей:</h6>',
        '<h5>Кнопка "Ваши турниры"</h5>': '<h5><i class="fas fa-eye me-2"></i>Кнопка "Ваши турниры"</h5>',
        '<h5>Кнопка "Все турниры"</h5>': '<h5><i class="fas fa-list me-2"></i>Кнопка "Все турниры"</h5>',
        '<h5>Дополнительная информация</h5>': '<h5><i class="fas fa-info-circle me-2"></i>Дополнительная информация</h5>',
    }
    
    for old, new in icon_map.items():
        html_content = html_content.replace(old, new)
    
    return html_content

def sync_to_base(help_content_html):
    """Синхронизирует изменения из help_content.html обратно в base.html"""
    base_path = "templates/base.html"
    
    # Создаем резервную копию base.html
    create_backup(base_path)
    
    with open(base_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим блок help-content
    start_marker = '<div class="help-content">'
    end_marker = '</div>'
    
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("❌ Блок help-content не найден в base.html")
        return False
    
    end_idx = content.find('</div>', start_idx + len(start_marker))
    if end_idx == -1:
        print("❌ Закрывающий тег не найден")
        return False
    
    # Добавляем иконки обратно
    help_content_with_icons = add_icons_back(help_content_html)
    
    # Заменяем блок
    new_content = (
        content[:start_idx + len(start_marker)] + 
        "\n                        " + help_content_with_icons.replace('\n', '\n                        ') +
        "\n                    " + content[end_idx:]
    )
    
    with open(base_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Изменения синхронизированы в {base_path}")
    return True

def main():
    print("=" * 60)
    print("Безопасный редактор Help-файла")
    print("=" * 60)
    print()
    
    help_html_path = "help_content.html"
    base_path = "templates/base.html"
    
    # Проверяем наличие файлов
    if not os.path.exists(help_html_path):
        print(f"⚠️  Файл {help_html_path} не найден. Создаю из base.html...")
        help_content = extract_help_from_base()
        if help_content:
            # Удаляем иконки для упрощения редактирования
            help_content_clean = remove_icons(help_content)
            
            # Создаем HTML файл
            html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Help информация - Quick Score</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h4 {{
            color: #2E7D32;
            border-bottom: 2px solid #2E7D32;
            padding-bottom: 10px;
        }}
        h5 {{
            color: #1976D2;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        h6 {{
            color: #424242;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        ul, ol {{
            margin-left: 20px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        strong {{
            color: #1976D2;
        }}
        .lead {{
            font-size: 1.1em;
            font-style: italic;
            color: #555;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""
            with open(help_html_path, 'w', encoding='utf-8') as f:
                f.write(html_template.format(content=help_content_clean))
            print(f"✅ Файл {help_html_path} создан")
    
    # Создаем резервную копию
    print(f"\n📋 Создание резервных копий...")
    backup_help = create_backup(help_html_path)
    if os.path.exists(base_path):
        backup_base = create_backup(base_path)
    
    print(f"\n✅ Готово к редактированию!")
    print(f"\n📝 Инструкция:")
    print(f"   1. Откройте файл: {help_html_path}")
    print(f"   2. Отредактируйте содержимое между тегами <body> и </body>")
    print(f"   3. Сохраните файл")
    print(f"   4. Запустите этот скрипт снова с параметром --sync для синхронизации")
    print(f"\n💾 Резервные копии сохранены в папке 'backups/'")
    print(f"\n⚠️  ВАЖНО: Не редактируйте теги <html>, <head>, <body> и стили!")
    print(f"   Редактируйте только контент внутри <body>...</body>")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--sync':
        # Режим синхронизации
        print("=" * 60)
        print("Синхронизация Help-контента в base.html")
        print("=" * 60)
        print()
        
        help_html_path = "help_content.html"
        if not os.path.exists(help_html_path):
            print(f"❌ Файл {help_html_path} не найден!")
            exit(1)
        
        # Извлекаем контент из help_content.html
        with open(help_html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Находим содержимое body
        body_start = content.find('<body>')
        body_end = content.find('</body>')
        
        if body_start == -1 or body_end == -1:
            print("❌ Не найден блок <body> в help_content.html")
            exit(1)
        
        help_content = content[body_start + 6:body_end].strip()
        
        # Синхронизируем в base.html
        if sync_to_base(help_content):
            print("\n✅ Синхронизация завершена успешно!")
            print("   Перезапустите приложение, чтобы увидеть изменения.")
        else:
            print("\n❌ Ошибка синхронизации!")
            exit(1)
    else:
        # Обычный режим - подготовка к редактированию
        main()


