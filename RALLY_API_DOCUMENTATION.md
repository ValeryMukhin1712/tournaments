# API для сохранения розыгрышей бадминтона

## Описание

Добавлена функциональность сохранения результатов каждого розыгрыша (rally) в матчах по бадминтону. Это позволяет детально отслеживать ход игры и анализировать статистику.

## Модель данных

### Поля модели Rally:

- `id` - уникальный идентификатор (автоматически)
- `match_id` - ID матча (обязательно)
- `tournament_id` - ID турнира (обязательно)
- `set_number` - номер сета (1, 2, 3) (обязательно)
- `rally_date` - дата розыгрыша (автоматически)
- `rally_time` - время розыгрыша (автоматически)
- `rally_datetime` - дата и время розыгрыша (автоматически)
- `court_number` - номер корта/площадки (опционально)
- `server_name` - имя подающего игрока (обязательно)
- `receiver_name` - имя принимающего игрока (обязательно)
- `server_won` - выиграл ли подающий (true/false) (обязательно)
- `score` - общий счёт после розыгрыша в формате "21:19" (обязательно)
- `notes` - дополнительные заметки (опционально)
- `created_at` - время создания записи (автоматически)

## API Endpoints

### 1. Создание розыгрыша

**POST** `/api/rallies`

**Заголовки:**
```
Content-Type: application/json
X-CSRFToken: <csrf_token>
```

**Тело запроса:**
```json
{
  "match_id": 123,
  "tournament_id": 45,
  "set_number": 1,
  "court_number": 2,
  "server_name": "Иван Иванов",
  "receiver_name": "Петр Петров",
  "server_won": true,
  "score": "21:19",
  "notes": "Отличный розыгрыш"
}
```

**Ответ (успех):**
```json
{
  "success": true,
  "rally": {
    "id": 1,
    "match_id": 123,
    "tournament_id": 45,
    "set_number": 1,
    "rally_date": "2025-11-25",
    "rally_time": "14:30:00",
    "rally_datetime": "2025-11-25T14:30:00",
    "court_number": 2,
    "server_name": "Иван Иванов",
    "receiver_name": "Петр Петров",
    "server_won": true,
    "score": "21:19",
    "notes": "Отличный розыгрыш",
    "created_at": "2025-11-25T14:30:00"
  }
}
```

**Ошибки:**
- `400` - Отсутствует CSRF токен или обязательные поля
- `404` - Матч или турнир не найден
- `400` - Розыгрыши можно сохранять только для бадминтона
- `500` - Внутренняя ошибка сервера

### 2. Получение всех розыгрышей матча

**GET** `/api/matches/<match_id>/rallies`

**Параметры запроса (опционально):**
- `set_number` - фильтр по номеру сета (1, 2, 3)

**Пример:**
```
GET /api/matches/123/rallies
GET /api/matches/123/rallies?set_number=1
```

**Ответ:**
```json
{
  "success": true,
  "match_id": 123,
  "rallies": [
    {
      "id": 1,
      "match_id": 123,
      "tournament_id": 45,
      "set_number": 1,
      "rally_date": "2025-11-25",
      "rally_time": "14:30:00",
      "rally_datetime": "2025-11-25T14:30:00",
      "court_number": 2,
      "server_name": "Иван Иванов",
      "receiver_name": "Петр Петров",
      "server_won": true,
      "score": "21:19",
      "notes": "Отличный розыгрыш",
      "created_at": "2025-11-25T14:30:00"
    }
  ],
  "count": 1
}
```

### 3. Получение конкретного розыгрыша

**GET** `/api/rallies/<rally_id>`

**Ответ:**
```json
{
  "success": true,
  "rally": {
    "id": 1,
    "match_id": 123,
    "tournament_id": 45,
    "set_number": 1,
    ...
  }
}
```

### 4. Удаление розыгрыша

**DELETE** `/api/rallies/<rally_id>`

**Заголовки:**
```
X-CSRFToken: <csrf_token>
```

**Ответ:**
```json
{
  "success": true,
  "message": "Розыгрыш удален"
}
```

## Применение миграции

Для создания таблицы `rally` в базе данных выполните:

```bash
python migrate_add_rally.py
```

Или таблица будет создана автоматически при следующем запуске приложения (через `db.create_all()`).

## Ограничения

- Розыгрыши можно сохранять только для турниров типа "Бадминтон single" или "Бадминтон dbl"
- Все запросы на создание/удаление требуют валидный CSRF токен
- Розыгрыши автоматически сортируются по времени создания при получении

## Пример использования в JavaScript

```javascript
// Получение CSRF токена
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

// Создание розыгрыша
async function saveRally(matchId, tournamentId, setNumber, serverName, receiverName, serverWon, score) {
  const response = await fetch('/api/rallies', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
      match_id: matchId,
      tournament_id: tournamentId,
      set_number: setNumber,
      server_name: serverName,
      receiver_name: receiverName,
      server_won: serverWon,
      score: score
    })
  });
  
  const data = await response.json();
  if (data.success) {
    console.log('Розыгрыш сохранен:', data.rally);
  } else {
    console.error('Ошибка:', data.error);
  }
}

// Получение всех розыгрышей матча
async function getMatchRallies(matchId, setNumber = null) {
  let url = `/api/matches/${matchId}/rallies`;
  if (setNumber) {
    url += `?set_number=${setNumber}`;
  }
  
  const response = await fetch(url);
  const data = await response.json();
  
  if (data.success) {
    console.log(`Найдено розыгрышей: ${data.count}`);
    return data.rallies;
  } else {
    console.error('Ошибка:', data.error);
    return [];
  }
}
```

