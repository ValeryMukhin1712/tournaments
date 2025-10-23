# ❓ FAQ - Часто задаваемые вопросы

---

## 🌐 Общие вопросы

### Какие требования к серверу?

**Минимальные:**
- Ubuntu 22.04 LTS
- 1 GB RAM
- 10 GB диск
- 1 vCPU

**Рекомендуемые:**
- 2 GB RAM
- 20 GB SSD
- 2 vCPU

### Можно ли использовать другой дистрибутив Linux?

Да, но скрипты оптимизированы для Ubuntu 22.04. Для других дистрибутивов потребуется адаптация команд установки пакетов.

### Нужен ли домен?

Нет, приложение будет работать по IP адресу. Домен нужен только для SSL сертификата.

---

## 🔐 Безопасность

### Как изменить SSH порт?

```bash
sudo nano /etc/ssh/sshd_config.d/security.conf
# Измените Port 22 на Port 2222

sudo systemctl restart sshd
sudo ufw allow 2222/tcp
sudo ufw delete allow 22/tcp
```

### Как проверить заблокированные IP в Fail2Ban?

```bash
sudo fail2ban-client status sshd
```

### Как разблокировать IP?

```bash
sudo fail2ban-client set sshd unbanip YOUR_IP
```

### Нужно ли открывать порт 5000 в firewall?

**Нет!** Nginx работает на портах 80/443 и проксирует запросы к порту 5000. Порт 5000 должен быть закрыт для внешнего доступа.

---

## 📊 База данных

### Можно ли использовать PostgreSQL вместо SQLite?

Да! Для этого:

1. Установите PostgreSQL:
```bash
sudo apt install -y postgresql postgresql-contrib
```

2. Создайте базу данных:
```bash
sudo -u postgres createdb tournaments
sudo -u postgres createuser deploy
sudo -u postgres psql
ALTER USER deploy WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE tournaments TO deploy;
\q
```

3. Измените DATABASE_URL в .env:
```env
DATABASE_URL=postgresql://deploy:your_password@localhost/tournaments
```

4. Установите psycopg2:
```bash
pip install psycopg2-binary
```

5. Перезапустите приложение:
```bash
sudo systemctl restart tournaments
```

### Как сделать бэкап базы данных?

**SQLite:**
```bash
cp /home/deploy/app/instance/tournament.db /home/deploy/backups/tournament_$(date +%Y%m%d).db
```

**PostgreSQL:**
```bash
pg_dump tournaments > /home/deploy/backups/tournaments_$(date +%Y%m%d).sql
```

### Автоматический бэкап?

Создайте cron задачу:

```bash
crontab -e
```

Добавьте:
```
# Бэкап каждый день в 3:00
0 3 * * * cp /home/deploy/app/instance/tournament.db /home/deploy/backups/tournament_$(date +\%Y\%m\%d).db

# Удаление старых бэкапов (старше 30 дней)
0 4 * * * find /home/deploy/backups -name "tournament_*.db" -mtime +30 -delete
```

---

## 🔄 Обновления

### Как обновить приложение?

```bash
cd /home/deploy/app/deployment
./scripts/deploy_app.sh --update
```

### Что делать если обновление сломало приложение?

1. Откатитесь к предыдущей версии:
```bash
cd /home/deploy/app
git log --oneline  # Найдите хороший коммит
git reset --hard COMMIT_HASH
sudo systemctl restart tournaments
```

2. Восстановите базу данных из бэкапа:
```bash
cp /home/deploy/backups/tournament_YYYYMMDD.db /home/deploy/app/instance/tournament.db
```

### Как настроить автоматическое обновление?

Используйте webhook (см. `deployment/scripts/setup_webhook.sh`).

---

## 🚀 Производительность

### Сколько пользователей может обслужить сервер?

**С дефолтными настройками (4 workers Gunicorn):**
- ~50-100 одновременных пользователей
- ~1000-2000 запросов в минуту

Для увеличения измените количество workers в `deployment/systemd/tournaments.service`:
```
--workers 8
```

### Приложение работает медленно

1. **Проверьте ресурсы:**
```bash
htop
```

2. **Оптимизируйте Gunicorn:**
```bash
sudo nano /etc/systemd/system/tournaments.service
# Увеличьте workers и threads
--workers 8 --threads 4
```

3. **Добавьте кэширование Nginx:**
В `/etc/nginx/sites-available/tournaments.conf` добавьте:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m max_size=1g;
proxy_cache my_cache;
```

4. **Перезапустите сервисы:**
```bash
sudo systemctl restart tournaments
sudo systemctl restart nginx
```

---

## 📧 Email

### Нужно ли настраивать email?

Нет, email не является обязательным для работы приложения.

### Как настроить Gmail для отправки?

1. Включите 2FA в Google аккаунте
2. Создайте App Password: https://myaccount.google.com/apppasswords
3. Добавьте в `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

---

## 🔧 Nginx

### 502 Bad Gateway

**Причины:**
1. Gunicorn не запущен
2. Неправильный upstream порт
3. Проблемы с приложением

**Решение:**
```bash
# Проверить статус приложения
sudo systemctl status tournaments

# Проверить логи
sudo journalctl -u tournaments -n 50

# Перезапустить
sudo systemctl restart tournaments
```

### 413 Request Entity Too Large

Увеличьте лимит в Nginx:

```bash
sudo nano /etc/nginx/sites-available/tournaments.conf
# Добавьте:
client_max_body_size 50M;

sudo nginx -t
sudo systemctl restart nginx
```

### Как добавить HTTPS redirect?

После установки SSL certbot делает это автоматически. Или вручную:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 🐛 Отладка

### Где найти логи?

```bash
# Логи приложения
sudo journalctl -u tournaments -f

# Логи Nginx
sudo tail -f /var/log/nginx/tournaments_error.log

# Логи системы
sudo tail -f /var/log/syslog
```

### Приложение не запускается

1. **Проверьте логи:**
```bash
sudo journalctl -u tournaments -n 100 --no-pager
```

2. **Запустите вручную:**
```bash
cd /home/deploy/app
source venv/bin/activate
python app.py
```

3. **Проверьте права:**
```bash
ls -la /home/deploy/app
# Все файлы должны принадлежать deploy:deploy
```

4. **Проверьте .env:**
```bash
cat /home/deploy/app/.env
```

### Как включить режим отладки?

**Только для локального тестирования! Не используйте в продакшене!**

```bash
nano /home/deploy/app/.env
# FLASK_DEBUG=True
# FLASK_ENV=development

sudo systemctl restart tournaments
```

---

## 🌍 Домен и DNS

### Как привязать домен?

1. В настройках DNS вашего регистратора добавьте A-запись:
```
Type: A
Name: @
Value: YOUR_SERVER_IP
TTL: 300
```

2. Для www:
```
Type: A
Name: www
Value: YOUR_SERVER_IP
```

3. Подождите распространения DNS (до 24 часов, обычно 1-2 часа)

4. Измените Nginx конфиг:
```bash
sudo nano /etc/nginx/sites-available/tournaments.conf
# server_name yourdomain.com www.yourdomain.com;

sudo nginx -t
sudo systemctl restart nginx
```

5. Установите SSL:
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 💾 Миграции

### Как добавить новое поле в модель?

1. Измените модель в `models/`
2. Используйте Flask-Migrate (если установлен) или пересоздайте БД

**С Flask-Migrate:**
```bash
cd /home/deploy/app
source venv/bin/activate
flask db migrate -m "Added new field"
flask db upgrade
```

**Без миграций (ПОТЕРЯЕТЕ ДАННЫЕ!):**
```bash
# Бэкап!
cp instance/tournament.db backups/

# Удалить БД
rm instance/tournament.db

# Создать заново
python init_db.py
```

---

## 🔄 Systemd

### Как просмотреть все сервисы приложения?

```bash
systemctl list-units --type=service --all | grep tournaments
```

### Автозапуск при перезагрузке не работает

```bash
sudo systemctl enable tournaments
sudo systemctl is-enabled tournaments  # должен вернуть "enabled"
```

### Как изменить количество workers Gunicorn?

```bash
sudo nano /etc/systemd/system/tournaments.service
# Измените --workers 4 на нужное число

sudo systemctl daemon-reload
sudo systemctl restart tournaments
```

**Формула:** workers = (2 × CPU_cores) + 1

---

## 🎯 Разное

### Можно ли запустить несколько приложений на одном сервере?

Да! Используйте разные порты и настройте Nginx для каждого приложения.

**Пример:**
- App1 на порту 5000
- App2 на порту 5001
- Bot1 без порта (long polling)

### Как мониторить сервер?

Установите дополнительные инструменты:

```bash
# Netdata (веб-интерфейс мониторинга)
bash <(curl -Ss https://my-netdata.io/kickstart.sh)

# Glances (терминальный мониторинг)
sudo apt install glances
glances
```

### Приложение съедает много памяти

1. **Уменьшите workers:**
```bash
sudo nano /etc/systemd/system/tournaments.service
--workers 2 --threads 2
```

2. **Добавьте swap:**
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📞 Поддержка

Если не нашли ответ:

1. Проверьте логи: `sudo journalctl -u tournaments -n 100`
2. Проверьте документацию: `deployment/README.md`
3. Проверьте GitHub Issues в репозитории

---

Дополнительные вопросы? Создайте Issue в репозитории!

