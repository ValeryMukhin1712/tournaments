# 📦 Инструкция по переносу базы данных на VDS

## ⚠️ ВАЖНО: Перед переносом

**ВНИМАНИЕ:** Перенос локальной БД на VDS **ЗАМЕНИТ** существующую БД на сервере. Все данные на VDS будут потеряны!

### Обязательные шаги перед переносом:

1. **Сделайте бэкап БД на VDS:**
   ```bash
   ssh deploy@ваш_сервер
   cd ~/quick-score
   mkdir -p ~/backups
   cp instance/tournament.db ~/backups/tournament_backup_$(date +%Y%m%d_%H%M%S).db
   ```

2. **Остановите приложение на VDS:**
   ```bash
   sudo systemctl stop tournaments
   ```

## 📋 Способ 1: Перенос через SCP (рекомендуется)

### На локальном компьютере:

1. **Создайте бэкап локальной БД:**
   ```bash
   # В директории проекта
   cp instance/tournament.db instance/tournament_backup_$(date +%Y%m%d_%H%M%S).db
   ```

2. **Скопируйте БД на VDS:**
   ```bash
   scp instance/tournament.db deploy@ваш_сервер:/home/deploy/quick-score/instance/tournament.db
   ```

3. **На VDS сервере:**
   ```bash
   # Подключитесь к серверу через SSH
   ssh deploy@ваш_сервер
   
   # Перейдите в директорию проекта
   cd ~/quick-score
   # или полный путь:
   # cd /home/deploy/quick-score
   
   # Установите правильные права доступа на файл БД
   chmod 644 instance/tournament.db
   chown deploy:deploy instance/tournament.db
   
   # Проверьте права (опционально)
   ls -lh instance/tournament.db
   # Должно показать: -rw-r--r-- 1 deploy deploy ... tournament.db
   
   # Перезапустите приложение
   sudo systemctl start tournaments
   
   # Проверьте статус
   sudo systemctl status tournaments
   ```
   
   **Пояснение:**
   - Команды выполняются **НА СЕРВЕРЕ** после подключения через SSH
   - `chmod 644` - права: владелец читает/пишет, остальные только читают
   - `chown deploy:deploy` - владелец и группа = `deploy`
   - Путь `instance/tournament.db` - относительно директории `~/quick-score`

## 📋 Способ 2: Применение миграций (альтернатива)

Если вы хотите сохранить данные на VDS и только синхронизировать структуру:

### На VDS сервере:

1. **Примените миграцию для swap_count:**
   ```bash
   ssh deploy@ваш_сервер
   cd ~/quick-score
   source venv/bin/activate
   python migrate_add_swap_count_to_rally.py
   ```

2. **Проверьте структуру таблицы:**
   ```bash
   python -c "from app import app, db; from sqlalchemy import text; with app.app_context(): conn = db.engine.connect(); result = conn.execute(text('PRAGMA table_info(rally)')); cols = result.fetchall(); print('Структура таблицы rally:'); [print(f'  {c[1]} ({c[2]})') for c in cols]"
   ```

3. **Перезапустите приложение:**
   ```bash
   sudo systemctl restart tournaments
   ```

## 📋 Способ 3: Полная замена БД (если нужно)

Если вы уверены, что хотите полностью заменить БД на VDS:

### На локальном компьютере:

1. **Создайте архив БД:**
   ```bash
   tar -czf tournament_db_backup.tar.gz instance/tournament.db
   ```

2. **Скопируйте на VDS:**
   ```bash
   scp tournament_db_backup.tar.gz deploy@ваш_сервер:/tmp/
   ```

### На VDS сервере:

1. **Остановите приложение:**
   ```bash
   sudo systemctl stop tournaments
   ```

2. **Создайте бэкап текущей БД:**
   ```bash
   cd ~/quick-score
   mkdir -p ~/backups
   cp instance/tournament.db ~/backups/tournament_backup_$(date +%Y%m%d_%H%M%S).db
   ```

3. **Распакуйте новую БД:**
   ```bash
   cd ~/quick-score
   tar -xzf /tmp/tournament_db_backup.tar.gz -C instance/
   ```

4. **Установите права (на сервере):**
   ```bash
   # На сервере, в директории ~/quick-score
   chmod 644 instance/tournament.db
   chown deploy:deploy instance/tournament.db
   ```

5. **Запустите приложение:**
   ```bash
   sudo systemctl start tournaments
   sudo systemctl status tournaments
   ```

## ✅ Проверка после переноса

1. **Проверьте структуру таблицы rally:**
   ```bash
   python -c "from app import app, db; from sqlalchemy import text; with app.app_context(): conn = db.engine.connect(); result = conn.execute(text('PRAGMA table_info(rally)')); cols = result.fetchall(); print('Структура таблицы rally:'); [print(f'  {c[1]} ({c[2]})') for c in cols]"
   ```

2. **Проверьте работу приложения:**
   - Откройте сайт в браузере
   - Попробуйте удалить тестовый турнир
   - Проверьте логи: `sudo journalctl -u tournaments -n 50`

## 🔄 Откат (если что-то пошло не так)

Если после переноса возникли проблемы:

```bash
# На VDS сервере
cd ~/quick-score
sudo systemctl stop tournaments
cp ~/backups/tournament_backup_YYYYMMDD_HHMMSS.db instance/tournament.db
# Установите права доступа
chmod 644 instance/tournament.db
chown deploy:deploy instance/tournament.db
sudo systemctl start tournaments
```

## 📝 Рекомендации

1. **Рекомендуется использовать Способ 2** (применение миграций) - это сохранит данные на VDS
2. Если данные на VDS не важны, используйте Способ 1 (SCP)
3. Всегда делайте бэкап перед любыми операциями с БД

