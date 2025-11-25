#!/bin/bash

###############################################################################
# Setup GitHub Webhook для автоматического деплоя Development окружения
# Настраивает webhook для отслеживания ветки dev
# 
# Использование:
#   ./setup_dev_webhook.sh
#
# Требования:
#   - Запускать от пользователя deploy на сервере
#   - Python 3 установлен
###############################################################################

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Переменные
WEBHOOK_DIR="/home/deploy/webhook-dev"
WEBHOOK_PORT=9001
APP_DIR="/home/deploy/quick-score-dev"
DEPLOY_SCRIPT="$APP_DIR/deployment/scripts/deploy_dev.sh"

log_info "=== Настройка GitHub Webhook для Development ==="

# Проверка, что запущено не от root
if [[ $EUID -eq 0 ]]; then
   log_error "Не запускайте этот скрипт от root! Используйте пользователя deploy"
   exit 1
fi

# Создание директории для webhook
log_info "Создание директории для webhook..."
mkdir -p "$WEBHOOK_DIR"

# Создание Python скрипта для webhook
cat > "$WEBHOOK_DIR/webhook_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Simple GitHub Webhook Server для Development окружения
Отслеживает push в ветку dev
"""
import os
import hmac
import hashlib
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'change-me-to-random-secret')
APP_DIR = '/home/deploy/quick-score-dev'
DEPLOY_SCRIPT = f'{APP_DIR}/deployment/scripts/deploy_dev.sh'

def verify_signature(payload, signature):
    """Проверка подписи webhook"""
    if not signature:
        return False
    
    # Убираем префикс 'sha256='
    signature = signature.replace('sha256=', '')
    
    # Вычисляем ожидаемую подпись
    mac = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    )
    
    return hmac.compare_digest(mac.hexdigest(), signature)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint для GitHub webhook"""
    
    # Проверка подписи
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 403
    
    # Проверка события
    event = request.headers.get('X-GitHub-Event')
    if event != 'push':
        return jsonify({'message': 'Event ignored'}), 200
    
    # Получение данных
    data = request.json
    ref = data.get('ref', '')
    
    # Проверка ветки - только dev
    if ref != 'refs/heads/dev':
        return jsonify({'message': f'Ignored push to {ref}'}), 200
    
    # Запуск деплоя
    try:
        result = subprocess.run(
            [DEPLOY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return jsonify({
            'message': 'Deployment started',
            'output': result.stdout,
            'errors': result.stderr
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001, debug=False)
EOF

chmod +x "$WEBHOOK_DIR/webhook_server.py"

# Создание systemd сервиса для webhook
cat > /tmp/webhook-dev.service << EOF
[Unit]
Description=GitHub Webhook Server for Development
After=network.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=$WEBHOOK_DIR
Environment="WEBHOOK_SECRET=change-me-to-random-secret"
ExecStart=/usr/bin/python3 $WEBHOOK_DIR/webhook_server.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/webhook-dev.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webhook-dev
sudo systemctl start webhook-dev

# Открыть порт в firewall
sudo ufw allow $WEBHOOK_PORT/tcp comment 'GitHub Webhook Dev'

log_info "✓ Webhook сервер для Development настроен и запущен на порту $WEBHOOK_PORT"
echo ""
log_warn "⚠️  ВАЖНО: Настройте webhook в GitHub:"
echo ""
echo "1. Откройте: https://github.com/ValeryMukhin1712/quick-score/settings/hooks"
echo "2. Нажмите 'Add webhook'"
echo "3. Заполните:"
echo "   - Payload URL: http://YOUR_SERVER_IP:$WEBHOOK_PORT/webhook"
echo "   - Content type: application/json"
echo "   - Secret: change-me-to-random-secret (или сгенерируйте новый)"
echo "   - Which events: Just the push event"
echo "4. Нажмите 'Add webhook'"
echo ""
log_info "Проверка работы: curl http://localhost:$WEBHOOK_PORT/health"

