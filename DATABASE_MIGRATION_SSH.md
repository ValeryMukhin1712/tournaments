# 📦 Копирование базы данных через SSH

## 🔧 Вариант 1: Использование SCP (рекомендуется)

### Предварительные требования

**Windows:**
- Установите [Git for Windows](https://git-scm.com/download/win) (включает Git Bash с командой `scp`)
- Или используйте WSL (Windows Subsystem for Linux)

### Определение файла базы данных

Сначала определите, какой файл использовать:

```powershell
Get-ChildItem -Path "tournament.db","instance\tournament.db" -ErrorAction SilentlyContinue | Select-Object FullName,@{Name="Size(MB)";Expression={[math]::Round($_.Length/1MB,2)}},LastWriteTime
```

Используйте файл с более поздней датой изменения.

### Команда для копирования

**В Git Bash или WSL:**

```bash
# Если файл в корне проекта
scp tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db

# Если файл в папке instance
scp instance/tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

**Или используйте полный путь:**

```bash
scp "C:\Cursor\Tournaments_v.1 — 04598ed коммит в main_1\tournament.db" deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

### Полная процедура

1. **Остановите приложение на сервере:**
```bash
ssh deploy@89.19.44.212
sudo systemctl stop tournaments
exit
```

2. **Скопируйте базу данных:**
```bash
# В Git Bash или WSL
scp tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

3. **Установите права доступа и запустите приложение:**
```bash
ssh deploy@89.19.44.212
cd /home/deploy/quick-score
sudo chmod 644 instance/tournament.db
sudo chown deploy:deploy instance/tournament.db
sudo systemctl start tournaments
sudo systemctl status tournaments
```

---

## 🔧 Вариант 2: Использование PowerShell с OpenSSH

Если у вас установлен OpenSSH в Windows 10/11:

```powershell
# Проверьте наличие scp
Get-Command scp

# Если команда найдена, используйте:
scp tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

---

## 🔧 Вариант 3: Использование rsync (более надежно)

Если на сервере установлен rsync:

```bash
# В Git Bash или WSL
rsync -avz --progress tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

**Преимущества rsync:**
- Показывает прогресс копирования
- Может продолжить при обрыве соединения
- Проверяет целостность данных

---

## 🔧 Вариант 4: Через SSH с перенаправлением

Если scp недоступен, можно использовать SSH с cat:

**На локальной машине (PowerShell):**
```powershell
# Читаем файл и отправляем через SSH
Get-Content tournament.db -Raw | ssh deploy@89.19.44.212 "cat > /home/deploy/quick-score/instance/tournament.db"
```

**Или через Git Bash:**
```bash
cat tournament.db | ssh deploy@89.19.44.212 "cat > /home/deploy/quick-score/instance/tournament.db"
```

---

## 🔧 Вариант 5: Через SSH с base64 (для бинарных файлов)

Для SQLite базы данных (бинарный файл) лучше использовать base64:

**На локальной машине (PowerShell):**
```powershell
# Кодируем в base64 и отправляем
$content = [Convert]::ToBase64String([IO.File]::ReadAllBytes("tournament.db"))
$content | ssh deploy@89.19.44.212 "base64 -d > /home/deploy/quick-score/instance/tournament.db"
```

**Или через Git Bash:**
```bash
base64 tournament.db | ssh deploy@89.19.44.212 "base64 -d > /home/deploy/quick-score/instance/tournament.db"
```

---

## 📋 Полный скрипт для выполнения всех шагов

Создайте файл `migrate_db.sh` в Git Bash:

```bash
#!/bin/bash

# Параметры
SERVER="deploy@89.19.44.212"
REMOTE_PATH="/home/deploy/quick-score/instance/tournament.db"
LOCAL_DB="tournament.db"

# Проверка файла
if [ ! -f "$LOCAL_DB" ]; then
    LOCAL_DB="instance/tournament.db"
fi

if [ ! -f "$LOCAL_DB" ]; then
    echo "ОШИБКА: Файл базы данных не найден!"
    exit 1
fi

echo "Найден файл: $LOCAL_DB"
echo "Размер: $(du -h "$LOCAL_DB" | cut -f1)"

# 1. Остановка приложения
echo "Остановка приложения на сервере..."
ssh $SERVER "sudo systemctl stop tournaments"

# 2. Создание резервной копии на сервере
echo "Создание резервной копии на сервере..."
ssh $SERVER "cd /home/deploy/quick-score/instance && cp tournament.db tournament.db.backup_\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"

# 3. Копирование файла
echo "Копирование базы данных..."
scp "$LOCAL_DB" "$SERVER:$REMOTE_PATH"

# 4. Установка прав доступа
echo "Установка прав доступа..."
ssh $SERVER "sudo chmod 644 $REMOTE_PATH && sudo chown deploy:deploy $REMOTE_PATH"

# 5. Запуск приложения
echo "Запуск приложения..."
ssh $SERVER "sudo systemctl start tournaments"

# 6. Проверка статуса
echo "Проверка статуса..."
sleep 3
ssh $SERVER "sudo systemctl status tournaments --no-pager"

echo "Готово!"
```

**Использование:**
```bash
chmod +x migrate_db.sh
./migrate_db.sh
```

---

## 🔐 Настройка SSH ключей (для упрощения)

Чтобы не вводить пароль каждый раз:

1. **Создайте SSH ключ (если нет):**
```bash
ssh-keygen -t rsa -b 4096
```

2. **Скопируйте ключ на сервер:**
```bash
ssh-copy-id deploy@89.19.44.212
```

3. **Теперь можно копировать без пароля:**
```bash
scp tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

---

## ✅ Проверка после копирования

```bash
# Подключитесь к серверу
ssh deploy@89.19.44.212

# Проверьте размер файла
ls -lh /home/deploy/quick-score/instance/tournament.db

# Проверьте права доступа
ls -la /home/deploy/quick-score/instance/tournament.db

# Проверьте статус сервиса
sudo systemctl status tournaments

# Проверьте логи
sudo journalctl -u tournaments -n 50 --no-pager
```

---

## 🚨 Устранение проблем

### Ошибка "Permission denied"

```bash
# Установите правильные права
ssh deploy@89.19.44.212 "sudo chmod 644 /home/deploy/quick-score/instance/tournament.db && sudo chown deploy:deploy /home/deploy/quick-score/instance/tournament.db"
```

### Ошибка "Connection refused"

- Проверьте доступность сервера: `ping 89.19.44.212`
- Проверьте SSH порт: `telnet 89.19.44.212 22`

### Файл слишком большой

Используйте сжатие:
```bash
scp -C tournament.db deploy@89.19.44.212:/home/deploy/quick-score/instance/tournament.db
```

---

## 📝 Рекомендации

1. **Всегда создавайте резервную копию** на сервере перед заменой
2. **Останавливайте приложение** перед копированием
3. **Проверяйте размер файла** до и после копирования
4. **Проверяйте логи** после запуска приложения



