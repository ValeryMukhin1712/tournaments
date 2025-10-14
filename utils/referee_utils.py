"""
Утилиты для интеграции с приложением Referee
"""

def parse_participant_names(left_participant_name, right_participant_name):
    """
    Парсит имена участников для заполнения полей в приложении Referee.
    
    Логика:
    - Если имя не содержит тире, то это имя помещается в оба поля команды
    - Если имя содержит тире, то:
      - Строка до тире - имя нижнего игрока
      - Строка после тире - имя верхнего игрока
    
    Args:
        left_participant_name (str): Имя левого участника из основного приложения
        right_participant_name (str): Имя правого участника из основного приложения
    
    Returns:
        dict: Словарь с именами для 4 полей Referee
        {
            'left_top': str,      # Верхний левый игрок
            'left_bottom': str,   # Нижний левый игрок
            'right_top': str,     # Верхний правый игрок
            'right_bottom': str   # Нижний правый игрок
        }
    """
    
    def parse_single_name(name):
        """Парсит одно имя участника"""
        if not name:
            return {'top': '', 'bottom': ''}
        
        name = name.strip()
        
        if '-' in name:
            # Имя содержит тире - разделяем
            parts = name.split('-', 1)  # Разделяем только по первому тире
            bottom_name = parts[0].strip()
            top_name = parts[1].strip()
        else:
            # Имя не содержит тире - используем для обоих полей
            bottom_name = name
            top_name = name
        
        return {'top': top_name, 'bottom': bottom_name}
    
    # Парсим имена участников
    left_names = parse_single_name(left_participant_name)
    right_names = parse_single_name(right_participant_name)
    
    return {
        'left_top': left_names['top'],
        'left_bottom': left_names['bottom'],
        'right_top': right_names['top'],
        'right_bottom': right_names['bottom']
    }


def generate_referee_html(participant1_name, participant2_name, tournament_name="Турнир"):
    """
    Генерирует HTML для приложения Referee с заполненными именами участников.
    
    Args:
        participant1_name (str): Имя первого участника (левая команда)
        participant2_name (str): Имя второго участника (правая команда)
        tournament_name (str): Название турнира
    
    Returns:
        str: HTML код для приложения Referee
    """
    
    # Парсим имена участников
    names = parse_participant_names(participant1_name, participant2_name)
    
    # Читаем базовый HTML шаблон
    try:
        with open('Referee/badminton_court.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        # Если файл не найден, используем встроенный HTML
        from Referee.badminton_court_ui_html import build_html
        html_content = build_html()
    
    # Заменяем заголовок
    html_content = html_content.replace(
        '<title>Бадминтон-корт</title>',
        f'<title>Судейство: {tournament_name}</title>'
    )
    
    # Заменяем заголовок страницы
    html_content = html_content.replace(
        '<h1>Бадминтон-корт</h1>',
        f'<h1>Судейство: {tournament_name}</h1>'
    )
    
    # Заполняем имена участников
    replacements = {
        'id="name_top_left" value="Алексей"': f'id="name_top_left" value="{names["left_top"]}"',
        'id="name_bottom_left" value="Дмитрий"': f'id="name_bottom_left" value="{names["left_bottom"]}"',
        'id="name_top_right" value="Сергей"': f'id="name_top_right" value="{names["right_top"]}"',
        'id="name_bottom_right" value="Андрей"': f'id="name_bottom_right" value="{names["right_bottom"]}"'
    }
    
    for old_value, new_value in replacements.items():
        html_content = html_content.replace(old_value, new_value)
    
    # Добавляем JavaScript для уведомления родительского окна о результате
    integration_script = """
    // Интеграция с основным приложением
    function notifyParent(result) {
        if (window.parent !== window) {
            window.parent.postMessage({
                type: 'refereeResult',
                scoreLeft: scoreLeft,
                scoreRight: scoreRight,
                participant1: document.getElementById('name_top_left').value + '-' + document.getElementById('name_bottom_left').value,
                participant2: document.getElementById('name_top_right').value + '-' + document.getElementById('name_bottom_right').value,
                leftTop: document.getElementById('name_top_left').value,
                leftBottom: document.getElementById('name_bottom_left').value,
                rightTop: document.getElementById('name_top_right').value,
                rightBottom: document.getElementById('name_bottom_right').value
            }, '*');
        }
    }
    
    // Модифицируем функцию checkVictory для уведомления родительского окна
    const originalCheckVictory = checkVictory;
    checkVictory = function() {
        const result = originalCheckVictory();
        if (result) {
            // Уведомляем родительское окно о завершении матча
            setTimeout(() => {
                notifyParent({
                    scoreLeft: scoreLeft,
                    scoreRight: scoreRight
                });
            }, 3000);
        }
        return result;
    };
    
    // Добавляем кнопку "Завершить матч" в интерфейс
    document.addEventListener('DOMContentLoaded', function() {
        const controls = document.querySelector('.controls');
        if (controls) {
            const finishBtn = document.createElement('button');
            finishBtn.textContent = 'Завершить матч';
            finishBtn.className = 'btn btn-primary';
            finishBtn.style.marginLeft = '10px';
            finishBtn.onclick = function() {
                notifyParent({
                    scoreLeft: scoreLeft,
                    scoreRight: scoreRight
                });
            };
            controls.appendChild(finishBtn);
        }
    });
    """
    
    # Вставляем скрипт интеграции перед закрывающим тегом </script>
    script_end = html_content.rfind('</script>')
    if script_end != -1:
        html_content = html_content[:script_end] + integration_script + '\n' + html_content[script_end:]
    
    return html_content


def test_name_parsing():
    """Тестирует функцию парсинга имен"""
    test_cases = [
        ("Иван", "Петр", "Простые имена"),
        ("Иван-Петр", "Сергей-Андрей", "Имена с тире"),
        ("Алексей", "Мария-Анна", "Смешанный случай"),
        ("", "Петр", "Пустое имя слева"),
        ("Иван-Петр-Сидор", "Мария", "Множественные тире"),
    ]
    
    print("Тестирование парсинга имен для Referee:")
    print("=" * 50)
    
    for left, right, description in test_cases:
        result = parse_participant_names(left, right)
        print(f"\n{description}:")
        print(f"  Входные данные: '{left}' vs '{right}'")
        print(f"  Результат:")
        print(f"    Левый верхний: '{result['left_top']}'")
        print(f"    Левый нижний:  '{result['left_bottom']}'")
        print(f"    Правый верхний: '{result['right_top']}'")
        print(f"    Правый нижний:  '{result['right_bottom']}'")


if __name__ == "__main__":
    test_name_parsing()
