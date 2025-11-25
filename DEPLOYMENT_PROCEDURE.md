# 🚀 Процедура деплоя Production и Dev окружений

Этот документ описывает процедуры деплоя для обоих окружений приложения Quick Score Tournaments.

## 📋 Общая информация

- **Production**: `https://quickscore.sytes.net/` → порт 5000 → `/home/deploy/quick-score`
- **Development**: `https://quickscore.sytes.net/new_dev` → порт 5001 → `/home/deploy/quick-score-dev`

## 🔄 Деплой Production окружения

### Способ 1: Автоматический деплой (рекомендуется)

```bash
# Подключитесь к серверу
ssh deploy@89.19.44.212

# Перейдите в директорию production
cd /home/deploy/quick-score

# Обновите код из репозитория
git fetch origin
git pull origin main

# Активируйте виртуальное окружение
source venv/bin/activate

# Обновите зависимости (если requirements.txt изменился)
pip install -r requirements.txt

# Перезапустите сервис
sudo systemctl restart tournaments

# Проверьте статус
sudo systemctl status tournaments
```

### Способ 2: Полное обновление (если нужен hard reset)

```bash
cd /home/deploy/quick-score

# Сохраните текущую версию (опционально)
git stash

# Получите последние изменения
git fetch origin
git reset --hard origin/main

# Активируйте виртуальное окружение
source venv/bin/activate

# Обновите зависимости
pip install -r requirements.txt

# Перезапустите сервис
sudo systemctl restart tournaments

# Проверьте статус
sudo systemctl status tournaments
```

### Проверка после деплоя Production

```bash
# Проверьте статус сервиса
sudo systemctl status tournaments

# Проверьте порт
ss -tuln | grep 5000

# Проверьте доступность через curl
curl -I https://quickscore.sytes.net/

# Проверьте логи на ошибки
sudo journalctl -u tournaments -n 50 --no-pager
```

## 🧪 Деплой Dev окружения

### Способ 1: Автоматический деплой (рекомендуется)

```bash
# Подключитесь к серверу
ssh deploy@89.19.44.212

# Перейдите в директорию dev
cd /home/deploy/quick-score-dev

# Обновите код из репозитория
git fetch origin
git pull origin main

# Активируйте виртуальное окружение
source venv/bin/activate

# Обновите зависимости (если requirements.txt изменился)
pip install -r requirements.txt

# Перезапустите сервис
sudo systemctl restart tournaments-dev

# Проверьте статус
sudo systemctl status tournaments-dev
```

### Способ 2: Полное обновление (если нужен hard reset)

```bash
cd /home/deploy/quick-score-dev

# Сохраните текущую версию (опционально)
git stash

# Получите последние изменения
git fetch origin
git reset --hard origin/main

# Активируйте виртуальное окружение
source venv/bin/activate

# Обновите зависимости
pip install -r requirements.txt

# Перезапустите сервис
sudo systemctl restart tournaments-dev

# Проверьте статус
sudo systemctl status tournaments-dev
```

### Проверка после деплоя Dev

```bash
# Проверьте статус сервиса
sudo systemctl status tournaments-dev

# Проверьте порт
ss -tuln | grep 5001

# Проверьте доступность через curl
curl -I https://quickscore.sytes.net/new_dev

# Проверьте логи на ошибки
sudo journalctl -u tournaments-dev -n 50 --no-pager
```

## 📝 Рекомендуемый порядок деплоя

1. **Сначала деплой в Dev** - протестируйте изменения
2. **Проверка работы Dev** - убедитесь, что всё работает
3. **Деплой в Production** - только после успешного тестирования в Dev

### Пример полного цикла деплоя

```bash
# 1. Деплой в Dev
cd /home/deploy/quick-score-dev
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournaments-dev

# 2. Проверка Dev (подождите 10-30 секунд)
sleep 10
curl -I https://quickscore.sytes.net/new_dev
sudo systemctl status tournaments-dev

# 3. Если всё ОК, деплой в Production
cd /home/deploy/quick-score
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tournaments

# 4. Проверка Production
sleep 10
curl -I https://quickscore.sytes.net/
sudo systemctl status tournaments
```

## 🔧 Управление сервисами

### Production

```bash
# Статус
sudo systemctl status tournaments

# Перезапуск
sudo systemctl restart tournaments

# Остановка
sudo systemctl stop tournaments

# Запуск
sudo systemctl start tournaments

# Логи в реальном времени
sudo journalctl -u tournaments -f

# Последние 100 строк логов
sudo journalctl -u tournaments -n 100 --no-pager
```

### Development

```bash
# Статус
sudo systemctl status tournaments-dev

# Перезапуск
sudo systemctl restart tournaments-dev

# Остановка
sudo systemctl stop tournaments-dev

# Запуск
sudo systemctl start tournaments-dev

# Логи в реальном времени
sudo journalctl -u tournaments-dev -f

# Последние 100 строк логов
sudo journalctl -u tournaments-dev -n 100 --no-pager
```

## 🗄️ Работа с базами данных

### Важно!

- **Production БД**: `/home/deploy/quick-score/instance/tournament.db`
- **Dev БД**: `/home/deploy/quick-score-dev/instance/tournament_dev.db`

Базы данных полностью независимы. Изменения в dev не влияют на production.

### Резервное копирование БД

```bash
# Production БД
cp /home/deploy/quick-score/instance/tournament.db /home/deploy/backups/tournament_$(date +%Y%m%d_%H%M%S).db

# Dev БД
cp /home/deploy/quick-score-dev/instance/tournament_dev.db /home/deploy/backups/tournament_dev_$(date +%Y%m%d_%H%M%S).db
```

## ⚠️ Важные замечания

1. **Всегда тестируйте в Dev перед Production** - это основное правило
2. **Не изменяйте .env файлы напрямую** - используйте правильные значения для каждого окружения
3. **Проверяйте логи после деплоя** - убедитесь, что нет ошибок
4. **Делайте резервные копии БД** - перед важными обновлениями
5. **Не останавливайте оба сервиса одновременно** - всегда оставляйте хотя бы один работающим

## 🐛 Решение проблем

### Приложение не запускается после деплоя

```bash
# Проверьте логи
sudo journalctl -u tournaments -n 100 --no-pager
# или
sudo journalctl -u tournaments-dev -n 100 --no-pager

# Проверьте синтаксис Python
cd /home/deploy/quick-score  # или quick-score-dev
source venv/bin/activate
python -m py_compile app.py

# Проверьте зависимости
pip check
```

### Ошибки импорта модулей

```bash
# Переустановите зависимости
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Проблемы с базой данных

```bash
# Проверьте права доступа
ls -la instance/tournament*.db

# Проверьте размер БД
du -h instance/tournament*.db
```

## 📊 Мониторинг

### Проверка использования ресурсов

```bash
# Использование памяти
free -h

# Использование CPU
top

# Использование диска
df -h

# Процессы приложений
ps aux | grep gunicorn
```

### Проверка портов

```bash
# Все слушающие порты
ss -tuln

# Конкретные порты
ss -tuln | grep -E ':(5000|5001)'
```

---

**Последнее обновление**: 2025-11-25

