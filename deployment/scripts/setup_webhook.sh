#!/bin/bash

###############################################################################
# Setup GitHub Webhook для автоматического деплоя
# 
# Использование:
#   ./setup_webhook.sh
#
# Что делает:
#   1. Создает простой webhook endpoint
#   2. Настраивает автоматическое обновление при push в main
#   3. Создает systemd сервис для webhook
###############################################################################

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

WEBHOOK_DIR="/home/deploy/webhook"
WEBHOOK_PORT=9000

log_info "=== Настройка GitHub Webhook ==="

# Создание директории
mkdir -p "$WEBHOOK_DIR"

# Создание Python скрипта для webhook
cat > "$WEBHOOK_DIR/webhook_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Simple GitHub Webhook Server
Автоматически обновляет приложение при push в репозиторий
"""

from flask import Flask, request, jsonify
import subprocess
import hmac
import hashlib
import os

app = Flask(__name__)

# Секретный токен (настройте в GitHub и здесь)
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'change-me-to-random-secret')
APP_DIR = '/home/deploy/quick-score'
DEPLOY_SCRIPT = f'{APP_DIR}/deployment/scripts/deploy_app.sh'

def verify_signature(payload, signature):
    """Проверка подписи от GitHub"""
    if not signature:
        return False
    
    sha_name, signature = signature.split('=')
    if sha_name != 'sha256':
        return False
    
    mac = hmac.new(
        WEBHOOK_SECRET.encode(),
        msg=payload,
        digestmod=hashlib.sha256
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
    
    # Проверка ветки
    if ref != 'refs/heads/main':
        return jsonify({'message': f'Ignored push to {ref}'}), 200
    
    # Запуск деплоя
    try:
        result = subprocess.run(
            [DEPLOY_SCRIPT, '--update'],
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
    app.run(host='0.0.0.0', port=9000, debug=False)
EOF

chmod +x "$WEBHOOK_DIR/webhook_server.py"

# Создание systemd сервиса для webhook
cat > /tmp/webhook.service << EOF
[Unit]
Description=GitHub Webhook Server
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

sudo mv /tmp/webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webhook
sudo systemctl start webhook

# Открыть порт в firewall
sudo ufw allow $WEBHOOK_PORT/tcp comment 'GitHub Webhook'

log_info "✓ Webhook сервер настроен и запущен на порту $WEBHOOK_PORT"
echo ""
log_warn "⚠️  СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. Сгенерируйте секретный токен:"
echo "   python3 -c 'import secrets; print(secrets.token_hex(32))'"
echo ""
echo "2. Установите токен в systemd сервис:"
echo "   sudo nano /etc/systemd/system/webhook.service"
echo "   Замените 'change-me-to-random-secret' на сгенерированный токен"
echo ""
echo "3. Перезапустите webhook:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart webhook"
echo ""
echo "4. В GitHub репозитории:"
echo "   - Settings → Webhooks → Add webhook"
echo "   - Payload URL: http://YOUR_SERVER_IP:$WEBHOOK_PORT/webhook"
echo "   - Content type: application/json"
echo "   - Secret: (ваш сгенерированный токен)"
echo "   - Events: Just the push event"
echo ""
log_info "Проверка работы: curl http://localhost:$WEBHOOK_PORT/health"
echo ""
log_info "=== Готово! ==="

