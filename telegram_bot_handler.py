"""
Обработчик команд Telegram бота для Quick Score
Запускайте этот скрипт на сервере для обработки команд от пользователей
"""
import requests
import time
import logging
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """Обработчик команд Telegram бота"""
    
    def __init__(self, bot_token, app_api_url='http://127.0.0.1:5000'):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.app_api_url = app_api_url  # URL нашего Flask приложения
        self.last_update_id = 0
        # На всякий случай отключаем webhook, чтобы polling работал без конфликта
        try:
            self.delete_webhook()
        except Exception as e:
            logger.warning(f"Не удалось удалить webhook при старте: {e}")

    def delete_webhook(self):
        """Удаляет webhook, чтобы избежать конфликта с getUpdates (409)."""
        url = f"{self.api_url}/deleteWebhook"
        resp = requests.get(url, params={"drop_pending_updates": False}, timeout=10)
        if resp.status_code == 200:
            logger.info("🔧 Webhook удалён (если был установлен)")
        else:
            logger.warning(f"Не удалось удалить webhook: {resp.status_code} - {resp.text}")
        
    def get_updates(self):
        """Получает новые сообщения от пользователей"""
        try:
            url = f"{self.api_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': 30  # Long polling
            }
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])
            else:
                # Частые причины: 409 (другой экземпляр getUpdates) или webhook активен
                logger.error(f"Ошибка получения обновлений: {response.status_code} - {response.text}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении обновлений: {e}")
            return []
    
    def send_message(self, chat_id, text):
        """Отправляет сообщение пользователю"""
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            logger.info(f"Отправка сообщения пользователю (chat_id={chat_id})...")
            response = requests.post(url, data=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Сообщение успешно отправлено пользователю (chat_id={chat_id})")
                return True
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                logger.error(f"❌ Ошибка отправки сообщения: {response.status_code} - {error_data}")
                return False
        except Exception as e:
            logger.error(f"❌ Исключение при отправке сообщения: {e}")
            return False
    
    def link_token_to_chat(self, token, chat_id):
        """Связывает токен заявки с Chat ID через API приложения"""
        try:
            url = f"{self.app_api_url}/api/telegram/link-token"
            payload = {
                'token': token,
                'chat_id': str(chat_id)
            }
            
            logger.info(f"🔗 Попытка связать токен {token[:8]}... с Chat ID {chat_id}")
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"✅ Токен {token[:8]}... успешно связан с Chat ID {chat_id}")
                    logger.info(f"📋 Участник: {data.get('participant_name')}, Турнир ID: {data.get('tournament_id')}")
                    return True
                else:
                    logger.error(f"❌ API вернул ошибку: {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ Ошибка HTTP {response.status_code} при связывании токена")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Не удалось подключиться к API приложения ({self.app_api_url})")
            logger.error("💡 Убедитесь, что Flask приложение запущено!")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при связывании токена: {e}")
            return False
    
    def handle_command(self, message):
        """Обрабатывает команды от пользователей"""
        chat_id = message['chat']['id']
        username = message['from'].get('username', '')
        first_name = message['from'].get('first_name', 'Друг')
        text = message.get('text', '')
        
        logger.info(f"Получена команда от {first_name} (@{username}, chat_id={chat_id}): {text}")
        
        if text.startswith('/start'):
            # Проверяем, есть ли токен в команде (Deep Link)
            parts = text.split()
            if len(parts) > 1:
                # Это Deep Link с токеном: /start TOKEN
                token = parts[1]
                logger.info(f"🔗 Обнаружен Deep Link с токеном: {token[:8]}...")
                
                # Пытаемся связать токен с Chat ID
                success = self.link_token_to_chat(token, chat_id)
                
                if success:
                    # Токен успешно привязан
                    link_success_message = f"""
✅ <b>Отлично, {first_name}!</b>

Ваш Telegram <b>успешно подключен</b> к заявке на турнир! 

🔔 Теперь вы будете получать уведомления о:
• Одобрении вашей заявки администратором
• Расписании матчей
• Результатах турниров

<b>Что дальше?</b>
Дождитесь, пока администратор одобрит вашу заявку. Мы пришлем вам уведомление сразу после одобрения!

<b>📞 Команды бота:</b>
/id - Получить ваш Chat ID
/help - Справка по использованию

Удачи в турнире! 🏆
"""
                    self.send_message(chat_id, link_success_message)
                else:
                    # Ошибка привязки токена
                    link_error_message = f"""
❌ <b>Ошибка подключения</b>

К сожалению, не удалось подключить Telegram к вашей заявке.

<b>Возможные причины:</b>
• QR-код уже был использован
• Ссылка устарела
• Заявка была удалена

<b>Что делать?</b>
Подайте новую заявку на турнир и отсканируйте новый QR-код.

Если проблема повторяется, обратитесь к организатору турнира.

<b>Ваш Chat ID:</b> <code>{chat_id}</code>
Вы можете указать его вручную при подаче заявки.
"""
                    self.send_message(chat_id, link_error_message)
            else:
                # Обычная команда /start без токена
                welcome_message = f"""
🎉 <b>Привет, {first_name}!</b>

Добро пожаловать в бот <b>Quick Score</b>! 

Этот бот будет отправлять вам уведомления о:
✅ Одобрении заявки на участие в турнире
📅 Расписании ваших матчей
🏆 Результатах турниров

<b>💡 Как подключить уведомления:</b>

<b>Способ 1 (QR-код):</b>
1. Подайте заявку на турнир через веб-приложение
2. Отсканируйте QR-код после подачи заявки
3. Готово! Уведомления подключены автоматически

<b>Способ 2 (Chat ID):</b>
1. Скопируйте ваш Chat ID: <code>{chat_id}</code>
2. Укажите его в поле "Telegram" при подаче заявки

<b>📞 Команды бота:</b>
/start - Показать это сообщение
/id - Получить ваш Chat ID
/help - Помощь по использованию

Удачи в турнирах! 🏆
"""
                success = self.send_message(chat_id, welcome_message)
                if not success:
                    logger.warning(f"⚠️ Не удалось отправить приветственное сообщение пользователю {first_name} (chat_id={chat_id})")
            
        elif text.startswith('/id'):
            # Отправляем только Chat ID
            id_message = f"""
🆔 <b>Ваш Chat ID:</b> <code>{chat_id}</code>

Скопируйте это число и укажите его в поле "Telegram" при подаче заявки на турнир.

{f'🔹 <b>Ваш Username:</b> @{username}' if username else ''}

💡 <b>Совет:</b> Chat ID надёжнее, чем username, так как username может быть изменён.
"""
            self.send_message(chat_id, id_message)
            
        elif text.startswith('/help'):
            # Справка
            help_message = f"""
❓ <b>Справка по боту Quick Score</b>

<b>📋 Команды:</b>
/start - Приветствие и информация
/id - Получить ваш Chat ID
/help - Эта справка

<b>🎯 Как использовать:</b>

1. <b>Получите ваш контакт:</b>
   • Username: @{username if username else 'username'}
   • Chat ID: <code>{chat_id}</code>

2. <b>Подайте заявку на турнир</b> через веб-приложение Quick Score

3. <b>Укажите ваш Telegram контакт</b> в форме заявки

4. <b>Получайте уведомления!</b>

<b>🔔 Типы уведомлений:</b>
• Одобрение заявки администратором
• Расписание матчей
• Результаты турнира

<b>💬 Вопросы?</b>
Свяжитесь с организатором турнира или автором приложения через форму "Связаться с автором" на главной странице.
"""
            self.send_message(chat_id, help_message)
            
        else:
            # Неизвестная команда
            unknown_message = f"""
❓ Неизвестная команда.

<b>Доступные команды:</b>
/start - Начать работу с ботом
/id - Получить ваш Chat ID
/help - Справка

Ваш Chat ID: <code>{chat_id}</code>
"""
            self.send_message(chat_id, unknown_message)
    
    def run(self):
        """Запускает бота в режиме постоянной работы"""
        logger.info("🤖 Бот Quick Score запущен и готов к работе!")
        logger.info("Ожидание команд от пользователей...")
        
        while True:
            try:
                updates = self.get_updates()
                
                for update in updates:
                    self.last_update_id = update['update_id']
                    
                    if 'message' in update:
                        message = update['message']
                        if 'text' in message:
                            self.handle_command(message)
                
                # Небольшая задержка между запросами если нет обновлений
                if not updates:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Остановка бота...")
                break
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                time.sleep(5)  # Пауза перед повторной попыткой


def main():
    """Точка входа для запуска бота"""
    # Получаем токен из конфигурации
    bot_token = Config.TELEGRAM_BOT_TOKEN
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN не настроен в config.py!")
        logger.error("Добавьте токен вашего бота в файл config.py")
        return
    
    # Создаем и запускаем обработчик
    handler = TelegramBotHandler(bot_token)
    
    try:
        handler.run()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")


if __name__ == '__main__':
    print("="*60)
    print("🤖 Quick Score Telegram Bot Handler")
    print("="*60)
    print()
    main()

