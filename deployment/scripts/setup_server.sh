#!/bin/bash

###############################################################################
# Setup Server Script для Quick Score Tournaments
# Автоматическая настройка Ubuntu 22.04 VDS сервера
# 
# Использование:
#   sudo ./setup_server.sh
#
# Что делает скрипт:
#   1. Обновляет систему
#   2. Устанавливает необходимые пакеты
#   3. Создает пользователя deploy
#   4. Настраивает SSH безопасность
#   5. Настраивает Firewall (UFW)
#   6. Устанавливает Fail2Ban
#   7. Настраивает автообновления
###############################################################################

set -e  # Остановиться при любой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функции для логирования
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   log_error "Этот скрипт должен быть запущен с правами root (sudo)"
   exit 1
fi

log_info "=== Начало настройки сервера ==="

# 1. Обновление системы
log_info "Шаг 1/8: Обновление системы..."
apt update -y
apt upgrade -y
apt autoremove -y
log_info "✓ Система обновлена"

# 2. Установка необходимых пакетов
log_info "Шаг 2/8: Установка необходимых пакетов..."
apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    nginx \
    git \
    curl \
    wget \
    htop \
    ufw \
    fail2ban \
    unattended-upgrades \
    certbot \
    python3-certbot-nginx \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

log_info "✓ Пакеты установлены"

# 3. Создание пользователя deploy
log_info "Шаг 3/8: Создание пользователя deploy..."
if id "deploy" &>/dev/null; then
    log_warn "Пользователь deploy уже существует"
else
    useradd -m -s /bin/bash deploy
    usermod -aG sudo deploy
    log_info "✓ Пользователь deploy создан"
fi

# Создание директорий для пользователя deploy
mkdir -p /home/deploy/.ssh
mkdir -p /home/deploy/logs
mkdir -p /home/deploy/backups

# Настройка прав
chown -R deploy:deploy /home/deploy
chmod 700 /home/deploy/.ssh

log_info "✓ Директории созданы"

# 4. Настройка SSH безопасности
log_info "Шаг 4/8: Настройка SSH..."

# Бэкап оригинального конфига
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Настройки SSH для безопасности
cat > /etc/ssh/sshd_config.d/security.conf << 'EOF'
# SSH Security Settings
Port 22
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 10
EOF

log_warn "⚠️  ВАЖНО: Настройте SSH ключ для пользователя deploy ДО перезапуска SSH!"
log_warn "⚠️  Команда: ssh-copy-id -i ~/.ssh/id_rsa.pub deploy@YOUR_SERVER_IP"
log_warn "⚠️  SSH будет перезапущен в конце скрипта"

# 5. Настройка Firewall (UFW)
log_info "Шаг 5/8: Настройка Firewall..."

# Сброс UFW
ufw --force reset

# Правила по умолчанию
ufw default deny incoming
ufw default allow outgoing

# Разрешить SSH
ufw allow 22/tcp comment 'SSH'

# Разрешить HTTP и HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Включить UFW
ufw --force enable

log_info "✓ Firewall настроен (открыты порты: 22, 80, 443)"

# 6. Настройка Fail2Ban
log_info "Шаг 6/8: Настройка Fail2Ban..."

# Создание локального конфига
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = root@localhost
sendername = Fail2Ban

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400
EOF

# Запуск Fail2Ban
systemctl enable fail2ban
systemctl restart fail2ban

log_info "✓ Fail2Ban настроен и запущен"

# 7. Настройка автообновлений
log_info "Шаг 7/8: Настройка автообновлений..."

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

log_info "✓ Автообновления настроены"

# 8. Настройка Nginx базовой конфигурации
log_info "Шаг 8/8: Настройка Nginx..."

# Удаление дефолтного сайта
rm -f /etc/nginx/sites-enabled/default

# Базовая оптимизация Nginx
cat > /etc/nginx/nginx.conf << 'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
    use epoll;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOF

# Тест конфигурации Nginx
nginx -t

systemctl enable nginx
systemctl restart nginx

log_info "✓ Nginx настроен и запущен"

# Финальные действия
log_info "=== Настройка сервера завершена ==="
echo ""
log_info "✓ Система обновлена"
log_info "✓ Python 3.11, Nginx, Git установлены"
log_info "✓ Пользователь deploy создан"
log_info "✓ SSH настроен (отключен root, только ключи)"
log_info "✓ Firewall настроен (порты 22, 80, 443)"
log_info "✓ Fail2Ban запущен"
log_info "✓ Автообновления настроены"
log_info "✓ Nginx запущен"
echo ""
log_warn "⚠️  ВАЖНЫЕ СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. Установите SSH ключ для пользователя deploy:"
echo "   ssh-copy-id -i ~/.ssh/id_rsa.pub deploy@YOUR_SERVER_IP"
echo ""
echo "2. Проверьте подключение:"
echo "   ssh deploy@YOUR_SERVER_IP"
echo ""
echo "3. Перезапустите SSH (ТОЛЬКО после установки ключа!):"
echo "   sudo systemctl restart sshd"
echo ""
echo "4. Запустите деплой приложения:"
echo "   cd /home/deploy"
echo "   git clone https://github.com/ValeryMukhin1712/quick-score.git app"
echo "   cd app/deployment"
echo "   ./scripts/deploy_app.sh"
echo ""
log_info "Для просмотра статуса сервисов:"
echo "   sudo systemctl status nginx"
echo "   sudo systemctl status fail2ban"
echo "   sudo ufw status"
echo ""
log_info "=== Готово! ==="

