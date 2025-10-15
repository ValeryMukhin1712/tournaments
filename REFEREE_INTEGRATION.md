# 🏸 Интеграция с приложением Referee

## 📋 Обзор

Реализована интеграция приложения Referee (судейство бадминтона) с основным турнирным приложением. Приложение Referee позволяет вести счет матча в интерактивном режиме с визуальным отображением корта.

## 🎯 Логика заполнения имен участников

### Правила парсинга имен:

1. **Простое имя** (без тире):
   - `"Иван"` → оба поля команды: `"Иван"`

2. **Имя с тире**:
   - `"Иван-Петр"` → нижний игрок: `"Иван"`, верхний игрок: `"Петр"`

3. **Смешанные случаи**:
   - `"Алексей"` vs `"Мария-Анна"` → левая команда: `"Алексей"` в обоих полях, правая: `"Мария"` (низ) и `"Анна"` (верх)

4. **Множественные тире**:
   - `"Иван-Петр-Сидор"` → нижний: `"Иван"`, верхний: `"Петр-Сидор"`

## 🛠️ Техническая реализация

### Файлы:

- `utils/referee_utils.py` - утилиты для парсинга имен и генерации HTML
- `routes/api.py` - API endpoint `/api/referee/generate`
- `templates/referee_test.html` - тестовая страница
- `test_referee_parsing.py` - тесты функциональности

### API Endpoint:

```http
POST /api/referee/generate
Content-Type: application/json

{
    "participant1": "Иван-Петр",
    "participant2": "Мария",
    "tournament_name": "Турнир"
}
```

**Ответ:**
```json
{
    "success": true,
    "html": "<!DOCTYPE html>..."
}
```

### Функции:

#### `parse_participant_names(left_name, right_name)`
Парсит имена участников для заполнения 4 полей в Referee.

**Возвращает:**
```python
{
    'left_top': str,      # Верхний левый игрок
    'left_bottom': str,   # Нижний левый игрок  
    'right_top': str,     # Верхний правый игрок
    'right_bottom': str   # Нижний правый игрок
}
```

#### `generate_referee_html(participant1, participant2, tournament_name)`
Генерирует HTML с заполненными именами и интеграцией.

## 🧪 Тестирование

### Запуск тестов:
```bash
python test_referee_parsing.py
```

### Тестовая страница:
```
http://localhost:5000/referee-test
```

## 🔧 Интеграция в основное приложение

### Варианты интеграции:

1. **Модальное окно** (рекомендуемый)
2. **Отдельная страница**
3. **Встроенный компонент**

### Пример использования в форме результата:

```html
<!-- Кнопка для открытия Referee -->
<button type="button" class="btn btn-success" onclick="openRefereeModal()">
    🏸 Открыть судейство
</button>

<!-- Модальное окно -->
<div class="modal fade" id="refereeModal">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-body">
                <iframe id="refereeFrame" width="100%" height="600px"></iframe>
            </div>
        </div>
    </div>
</div>
```

### JavaScript интеграция:

```javascript
function openRefereeModal() {
    const participant1 = document.getElementById('participant1_name').value;
    const participant2 = document.getElementById('participant2_name').value;
    
    // Загружаем Referee через API
    fetch('/api/referee/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            participant1: participant1,
            participant2: participant2,
            tournament_name: 'Турнир'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('refereeFrame').srcdoc = data.html;
            new bootstrap.Modal(document.getElementById('refereeModal')).show();
        }
    });
}

// Обработка результата от Referee
window.addEventListener('message', function(event) {
    if (event.data.type === 'refereeResult') {
        const { scoreLeft, scoreRight } = event.data;
        document.getElementById('sets_score').value = `${scoreLeft}:${scoreRight}`;
        bootstrap.Modal.getInstance(document.getElementById('refereeModal')).hide();
    }
});
```

## 📊 Возможности Referee

- ✅ Интерактивный корт с визуальным счетом
- ✅ Ведение счета кликами по половинам корта
- ✅ Управление подачей с визуальным индикатором
- ✅ Журнал подач с детальной статистикой
- ✅ Автоматическое определение победителя (до 21 очка)
- ✅ Функции отмены и очистки
- ✅ Интеграция с основным приложением через postMessage

## 🎮 Использование

1. Заполните имена участников в форме результата
2. Нажмите кнопку "Открыть судейство"
3. В приложении Referee ведите счет матча
4. По завершении результат автоматически передается в основное приложение

## 🔍 Примеры тестирования

| Входные данные | Левый верхний | Левый нижний | Правый верхний | Правый нижний |
|----------------|---------------|--------------|----------------|---------------|
| `"Иван"` vs `"Петр"` | Иван | Иван | Петр | Петр |
| `"Иван-Петр"` vs `"Мария-Анна"` | Петр | Иван | Анна | Мария |
| `"Алексей"` vs `"Мария-Анна"` | Алексей | Алексей | Анна | Мария |
| `"Иван-Петр-Сидор"` vs `"Мария"` | Петр-Сидор | Иван | Мария | Мария |

## ✅ Статус

- [x] Парсинг имен участников
- [x] Генерация HTML с заполненными именами
- [x] API endpoint для интеграции
- [x] JavaScript интеграция через postMessage
- [x] Тестовая страница
- [x] Автоматические тесты
- [ ] Интеграция в форму результата (требует выбора варианта)


