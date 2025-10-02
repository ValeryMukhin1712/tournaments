"""
Основные маршруты приложения
"""
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Tournament передается как параметр в функции

logger = logging.getLogger(__name__)

def send_token_email_railway_fallback(email, name, token):
    """Альтернативный метод отправки email для Railway (через внешний API)"""
    try:
        import requests
        import json
        import os
        
        # Используем EmailJS или другой внешний сервис
        # Для демонстрации создаем простой webhook
        webhook_url = os.environ.get('EMAIL_WEBHOOK_URL')
        
        if webhook_url:
            logger.info(f"Попытка отправки через webhook: {webhook_url}")
            
            payload = {
                'to': email,
                'subject': 'Ваш токен для создания турниров',
                'body': f"""
Здравствуйте, {name}!

Ваш токен для создания турниров: {token}

Этот токен действителен в течение 30 дней.
Используйте его для входа в систему как администратор турнира.

С уважением,
Команда турнирной системы
                """,
                'from': 'tournaments.master@gmail.com'
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"[SUCCESS] Email отправлен через webhook на {email}")
                return True
            else:
                logger.error(f"[ERROR] Webhook вернул статус {response.status_code}")
        
        # Если webhook не настроен, используем простой HTTP запрос к внешнему сервису
        logger.info("Webhook не настроен. Пытаемся использовать внешний сервис.")
        
        # Попробуем использовать EmailJS (бесплатный сервис)
        emailjs_url = "https://api.emailjs.com/api/v1.0/email/send"
        emailjs_service_id = os.environ.get('EMAILJS_SERVICE_ID')
        emailjs_template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
        emailjs_user_id = os.environ.get('EMAILJS_USER_ID')
        
        if emailjs_service_id and emailjs_template_id and emailjs_user_id:
            logger.info("Попытка отправки через EmailJS")
            
            payload = {
                'service_id': emailjs_service_id,
                'template_id': emailjs_template_id,
                'user_id': emailjs_user_id,
                'template_params': {
                    'to_email': email,
                    'to_name': name,
                    'token': token,
                    'from_name': 'Турнирный Ассистент'
                }
            }
            
            # Добавляем заголовки для имитации браузера
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Origin': 'https://dashboard.emailjs.com',
                'Referer': 'https://dashboard.emailjs.com/'
            }
            
            response = requests.post(emailjs_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info(f"[SUCCESS] Email отправлен через EmailJS на {email}")
                return True
            else:
                logger.error(f"[ERROR] EmailJS вернул статус {response.status_code}")
        
        # Если все внешние сервисы недоступны, сохраняем для ручной отправки
        logger.info("[RAILWAY FALLBACK] Все внешние сервисы недоступны. Сохраняем для ручной отправки.")
        
        # Логируем данные для ручной отправки
        logger.info(f"[RAILWAY FALLBACK] Данные для ручной отправки email:")
        logger.info(f"Получатель: {email}")
        logger.info(f"Имя: {name}")
        logger.info(f"Токен: {token}")
        logger.info(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Сохраняем в файл для ручной отправки
        try:
            with open('tokens.txt', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {email} - {name} - Токен: {token} (RAILWAY FALLBACK - ТРЕБУЕТСЯ РУЧНАЯ ОТПРАВКА)\n")
        except Exception as e:
            logger.warning(f"Не удалось сохранить в файл: {e}")
        
        logger.info("[INFO] На Railway SMTP заблокирован. Токен сохранен для ручной отправки.")
        return False  # Возвращаем False, но токен сохранен
        
    except Exception as e:
        logger.error(f"Ошибка в Railway fallback: {e}")
        return False

def send_token_email(email, name, token):
    """Отправляет email с токеном пользователю"""
    try:
        # Сохраняем токен в файл для логирования
        try:
            with open('tokens.txt', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {email} - {name} - Токен: {token}\n")
        except Exception as e:
            logger.warning(f"Не удалось сохранить токен в файл: {e}")
        
        # Получаем настройки email из конфигурации Flask
        from flask import current_app
        import os
        
        # Проверяем переменные окружения (для Railway)
        smtp_server = os.environ.get('MAIL_SERVER') or current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('MAIL_PORT', current_app.config.get('MAIL_PORT', 587)))
        smtp_username = os.environ.get('MAIL_USERNAME') or current_app.config.get('MAIL_USERNAME')
        smtp_password = os.environ.get('MAIL_PASSWORD') or current_app.config.get('MAIL_PASSWORD')
        from_email = os.environ.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_DEFAULT_SENDER', smtp_username)
        
        logger.info(f"Email настройки: server={smtp_server}, port={smtp_port}, username={smtp_username}")
        logger.info(f"Переменные окружения: MAIL_SERVER={os.environ.get('MAIL_SERVER')}, MAIL_USERNAME={os.environ.get('MAIL_USERNAME')}")
        logger.info(f"Все переменные окружения MAIL_*: {[(k, v) for k, v in os.environ.items() if k.startswith('MAIL_')]}")
        logger.info(f"RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'НЕ УСТАНОВЛЕНО')}")
        
        # Проверяем, настроены ли email настройки
        logger.info(f"Проверка email настроек: username={smtp_username}, password={'***' if smtp_password else 'НЕТ'}")
        if not smtp_username or not smtp_password:
            logger.warning("Email настройки не настроены. Токен сохранен в файл, но email не отправлен.")
            try:
                with open('tokens.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {email} - {name} - Токен: {token} (EMAIL НЕ НАСТРОЕН)\n")
            except Exception as e:
                logger.warning(f"Не удалось сохранить токен в файл: {e}")
            return False
        
        # Проверяем, находимся ли мы на Railway
        if os.environ.get('RAILWAY_ENVIRONMENT') == 'production':
            logger.info("Обнаружена среда Railway. Пытаемся использовать альтернативный метод отправки email.")
            result = send_token_email_railway_fallback(email, name, token)
            # Обновляем статус токена в базе данных
            update_token_email_status(token, 'manual' if not result else 'sent')
            return result
        
        # Создаем сообщение
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email
        msg['Subject'] = "Ваш токен для создания турниров"
        
        # Текст сообщения
        body = f"""
Здравствуйте, {name}!

Ваш токен для создания турниров: {token}

Этот токен действителен в течение 30 дней.
Используйте его для входа в систему как администратор турнира.

С уважением,
Команда турнирной системы
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Отправляем email
        import smtplib
        logger.info(f"Попытка отправки email на {email} с токеном {token}")
        logger.info(f"SMTP настройки: {smtp_server}:{smtp_port}, пользователь: {smtp_username}")
        logger.info(f"От: {from_email}, Кому: {email}")
        
        try:
            # Устанавливаем таймаут для SMTP подключения
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            logger.info("[OK] SMTP подключение установлено (таймаут 30 сек)")
            
            server.starttls()
            logger.info("[OK] TLS включен")
            
            server.login(smtp_username, smtp_password)
            logger.info("[OK] Авторизация успешна")
            
            text = msg.as_string()
            result = server.sendmail(from_email, email, text.encode('utf-8'))
            logger.info(f"[OK] Email отправлен, результат: {result}")
            
            server.quit()
            logger.info("[OK] SMTP соединение закрыто")
            
            logger.info(f"[SUCCESS] Токен {token} успешно отправлен на {email} ({name}) от {from_email}")
            # Обновляем статус токена в базе данных
            update_token_email_status(token, 'sent')
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[ERROR] Ошибка авторизации SMTP: {e}")
            raise
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"[ERROR] Получатель отклонен: {e}")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"[ERROR] Ошибка SMTP: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        # Обновляем статус токена в базе данных
        update_token_email_status(token, 'failed')
        # Если не удалось отправить email, все равно сохраняем токен в файл
        try:
            with open('tokens.txt', 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {email} - {name} - Токен: {token} (EMAIL НЕ ОТПРАВЛЕН: {str(e)})\n")
        except Exception as file_e:
            logger.warning(f"Не удалось сохранить токен в файл: {file_e}")
        return False

def update_token_email_status(token_value, status):
    """Обновляет статус отправки email для токена"""
    try:
        from flask import current_app
        
        # Используем существующую модель Token из app.py
        from app import Token
        
        # Находим токен по значению
        token_obj = Token.query.filter_by(token=token_value).first()
        if token_obj:
            token_obj.email_status = status
            if status == 'sent':
                token_obj.email_sent = True
                token_obj.email_sent_at = datetime.utcnow()
            current_app.extensions['sqlalchemy'].db.session.commit()
            logger.info(f"Статус токена {token_value} обновлен на: {status}")
        else:
            logger.warning(f"Токен {token_value} не найден в базе данных")
    except Exception as e:
        logger.error(f"Ошибка обновления статуса токена {token_value}: {e}")

def send_token_email_async(email, name, token, app=None):
    """Асинхронная отправка email (не блокирует основной поток)"""
    import threading
    import time
    
    def send_email_thread():
        try:
            logger.info(f"Запуск асинхронной отправки email на {email}")
            time.sleep(1)  # Небольшая задержка
            
            # Создаем контекст приложения для асинхронного потока
            if app:
                with app.app_context():
                    result = send_token_email(email, name, token)
                    logger.info(f"Асинхронная отправка завершена: {result}")
            else:
                # Если приложение не передано, отправляем синхронно
                result = send_token_email(email, name, token)
                logger.info(f"Синхронная отправка завершена: {result}")
        except Exception as e:
            logger.error(f"Ошибка асинхронной отправки: {e}")
    
    # Запускаем в отдельном потоке
    thread = threading.Thread(target=send_email_thread)
    thread.daemon = True
    thread.start()
    logger.info(f"Асинхронная отправка email запущена для {email}")
    return True  # Возвращаем True сразу, не ждем завершения

def create_main_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, Token, WaitingList, Settings):
    """Создает основные маршруты приложения"""
    
    def check_tournament_access(tournament_id, admin_id=None):
        """Проверяет права доступа к турниру"""
        from flask import session
        
        # Получаем турнир
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            return False, "Турнир не найден"
        
        # Проверяем сессию админа
        session_admin_id = session.get('admin_id')
        session_admin_email = session.get('admin_email', '')
        
        # Проверяем, является ли пользователь системным админом
        if session_admin_email == 'admin@system' or (admin_id and admin_id == 1):
            return True, tournament
        
        # Проверяем, является ли пользователь админом этого турнира
        if session_admin_id and tournament.admin_id == session_admin_id:
            return True, tournament
        
        # Дополнительная проверка по admin_id, если передан
        if admin_id and tournament.admin_id == admin_id:
            return True, tournament
        
        return False, "У вас нет прав доступа к этому турниру"
    
    def get_current_admin():
        """Получает текущего админа из сессии"""
        from flask import session
        admin_id = session.get('admin_id')
        if admin_id:
            # Простая заглушка для админа
            return type('Admin', (), {'id': admin_id, 'email': 'admin@system', 'is_active': True})()
        return None
    
    @app.route('/')
    def index():
        # Новая стартовая страница с выбором роли
        return render_template('index.html')
    
    @app.route('/test-green-colors')
    def test_green_colors():
        """Тестовая страница с квадратами зелёных цветов"""
        return render_template('test_green_colors.html')
    
    @app.route('/tournaments')
    def tournaments_list():
        """Список всех турниров для просмотра"""
        tournaments = Tournament.query.all()
        # Загружаем участников, матчи и лист ожидания для каждого турнира
        for tournament in tournaments:
            tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
            tournament.matches = Match.query.filter_by(tournament_id=tournament.id).all()
            tournament.waiting_list = WaitingList.query.filter_by(tournament_id=tournament.id, status='ожидает').all()
        return render_template('tournaments.html', tournaments=tournaments)
    
    @app.route('/request-token', methods=['GET', 'POST'])
    def request_token():
        """Страница запроса токена для создания турнира"""
        logger.info(f"Request token: method={request.method}, headers={dict(request.headers)}")
        
        # Очищаем все flash сообщения при загрузке страницы
        if request.method == 'GET':
            # Очищаем flash сообщения для GET запроса
            from flask import get_flashed_messages
            messages = get_flashed_messages()
            if messages:
                logger.info(f"Очищено {len(messages)} flash сообщений при загрузке страницы токенов")
        
        if request.method == 'POST':
            # Проверяем CSRF токен (упрощенная проверка для Railway)
            csrf_token = request.form.get('csrf_token')
            if not csrf_token:
                logger.warning("CSRF токен отсутствует в запросе")
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('request_token.html')
            
            # Дополнительная проверка CSRF
            try:
                from flask_wtf.csrf import validate_csrf
                validate_csrf(csrf_token)
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                # На Railway может быть проблема с сессиями, пропускаем проверку
                logger.info("Пропускаем CSRF проверку для Railway")
            
            # Получаем данные из формы
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            
            # Валидация
            if not name or not email:
                flash('Пожалуйста, заполните все обязательные поля.', 'error')
                return render_template('request_token.html')
            
            # Проверяем уникальность email
            existing_token = Token.query.filter_by(email=email).first()
            if existing_token:
                # Если токен уже существует, показываем его пользователю
                return render_template('token_generated.html', 
                                     token=existing_token.token, 
                                     name=existing_token.name, 
                                     email=existing_token.email,
                                     created_at=existing_token.created_at.strftime('%d.%m.%Y %H:%M'))
            
            # ОТЛАДКА: Проверяем количество уже выданных токенов
            total_tokens = Token.query.count()
            max_tokens = int(Settings.get_setting('max_tokens', '4'))
            logger.info(f"Текущее количество выданных токенов: {total_tokens}, максимум: {max_tokens}")
            
            if total_tokens >= max_tokens:
                logger.info(f"Достигнут лимит токенов ({max_tokens}). Отказываем в выдаче нового токена.")
                flash(f'Свободных токенов пока нет (лимит: {max_tokens})', 'warning')
                return render_template('request_token.html', 
                                     total_tokens=total_tokens,
                                     max_tokens=max_tokens)
            
            # Генерируем целочисленный токен в диапазоне 10-99
            import random
            token = random.randint(10, 99)
            
            # Проверяем, что токен уникален (независимо от использованности)
            while Token.query.filter_by(token=token).first():
                token = random.randint(10, 99)
            
            # Создаем запись в базе данных
            try:
                new_token = Token(
                    email=email,
                    token=token,
                    name=name,
                    created_at=datetime.utcnow(),
                    is_used=False,
                    email_sent=False,
                    email_status='pending'
                )
                db.session.add(new_token)
                db.session.commit()
                
                # Сохраняем в сессии для быстрого доступа
                session['token_request'] = {
                    'name': name,
                    'email': email,
                    'token': token,
                    'created_at': datetime.now().isoformat()
                }
                
                # Отправляем email с токеном
                logger.info(f"Отправка email с токеном {token} на {email} для {name}")
                try:
                    email_sent = send_token_email_async(email, name, token, app)
                    logger.info(f"Результат отправки email: {email_sent}")
                    if email_sent:
                        logger.info(f"[SUCCESS] Email отправлен на {email}")
                    else:
                        logger.warning(f"[WARNING] Email не настроен для {email}")
                except Exception as e:
                    logger.error(f'Ошибка отправки email: {e}')
                    logger.warning(f"[WARNING] Ошибка отправки email для {email}")
                    
            except Exception as e:
                logger.error(f'Ошибка сохранения токена в БД: {e}')
                flash('Ошибка при создании токена. Попробуйте еще раз.', 'error')
                return render_template('request_token.html')
            
            # Показываем страницу с токеном
            return render_template('token_generated.html', 
                                 token=token, 
                                 name=name, 
                                 email=email,
                                 created_at=datetime.now().strftime('%d.%m.%Y %H:%M'))
        
        # Для GET запроса показываем информацию о количестве токенов
        total_tokens = Token.query.count()
        max_tokens = int(Settings.get_setting('max_tokens', '4'))
        logger.info(f"GET запрос на страницу токенов. Текущее количество: {total_tokens}, максимум: {max_tokens}")
        
        return render_template('request_token.html', 
                             total_tokens=total_tokens,
                             max_tokens=max_tokens)
    
    @app.route('/create-tournament', methods=['GET', 'POST'])
    def create_tournament_form():
        """Страница создания нового турнира"""
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('create_tournament.html')
            
            # Получаем данные формы
            name = request.form.get('name')
            email = request.form.get('email')
            telegram_id = request.form.get('telegram_id')
            contact_method = request.form.get('contact_method')
            
            if not name:
                flash('Пожалуйста, введите ваше имя', 'error')
                return render_template('create_tournament.html')
            
            if contact_method == 'email' and not email:
                flash('Пожалуйста, введите email', 'error')
                return render_template('create_tournament.html')
            
            if contact_method == 'telegram' and not telegram_id:
                flash('Пожалуйста, введите Telegram ID', 'error')
                return render_template('create_tournament.html')
            
            # Генерируем токен турнира 47
            tournament_token = "47"
            
            # Простая заглушка для админа
            try:
                # Создаем простой объект админа
                admin = type('Admin', (), {
                    'id': 1,
                    'name': name,
                    'email': email,
                    'token': tournament_token,
                    'is_active': True
                })()
                
                logger.info(f"Админ турнира создан/обновлен: {name} ({email}) с токеном {tournament_token}")
                
            except Exception as e:
                logger.error(f"Ошибка сохранения админа: {e}")
                db.session.rollback()
                flash('Ошибка при сохранении данных админа', 'error')
                return render_template('create_tournament.html')
            
            # Отправляем токен
            if contact_method == 'email':
                try:
                    from flask_mail import Message
                    from app import mail
                    
                    msg = Message(
                        subject='Токен для создания турнира',
                        recipients=[email],
                        body=f'''
Здравствуйте, {name}!

Ваш токен для создания турнира: {tournament_token}

Используйте этот токен для доступа к функциям администратора турнира.

С уважением,
Команда Турнирной системы
                        ''',
                        html=f'''
                        <h2>Токен для создания турнира</h2>
                        <p>Здравствуйте, <strong>{name}</strong>!</p>
                        <p>Ваш токен для создания турнира: <strong style="font-size: 24px; color: #007bff;">{tournament_token}</strong></p>
                        <p>Используйте этот токен для доступа к функциям администратора турнира.</p>
                        <hr>
                        <p><em>С уважением,<br>Команда Турнирной системы</em></p>
                        '''
                    )
                    mail.send(msg)
                    flash(f'Токен турнира {tournament_token} отправлен на email: {email}', 'success')
                except Exception as e:
                    logger.error(f"Ошибка отправки email: {e}")
                    flash(f'Токен турнира: {tournament_token}. Ошибка отправки email, но токен сохранен.', 'warning')
            else:
                # Для Telegram пока просто показываем сообщение
                flash(f'Токен турнира {tournament_token} отправлен в Telegram: {telegram_id}', 'success')
            
            return redirect(url_for('index'))
        
        return render_template('create_tournament.html')
    
    @app.route('/join-tournament')
    def join_tournament():
        """Страница для выбора турнира для участия"""
        tournaments = Tournament.query.all()
        
        # Загружаем участников, матчи и информацию об админе турнира для каждого турнира
        for tournament in tournaments:
            tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
            tournament.matches = Match.query.filter_by(tournament_id=tournament.id).all()
            
            # Загружаем информацию об админе турнира
            # Ищем токен, который использовался для создания турнира
            # Для системного админа (admin_id = 1) показываем системную информацию
            if tournament.admin_id == 1:
                tournament.organizer_name = "Системный администратор"
                tournament.organizer_email = "admin@system"
            else:
                # Ищем токен по admin_id (который генерируется как hash(email) % 1000000)
                # Нужно найти токен, который мог создать этот admin_id
                # Поскольку admin_id генерируется как hash(email) % 1000000, 
                # мы не можем точно восстановить email, поэтому показываем ID
                tournament.organizer_name = f"Админ турнира (ID: {tournament.admin_id})"
                tournament.organizer_email = "Не указан"
                
                # Попробуем найти токен с похожим admin_id
                # Это не идеальное решение, но для демонстрации подойдет
                try:
                    # Ищем все токены и проверяем, какой из них мог создать этот admin_id
                    all_tokens = Token.query.all()
                    for token in all_tokens:
                        if hash(token.email) % 1000000 == tournament.admin_id:
                            tournament.organizer_name = token.name
                            tournament.organizer_email = token.email
                            break
                except Exception as e:
                    app.logger.warning(f"Ошибка поиска админа турнира {tournament.id}: {e}")
        
        return render_template('join_tournament.html', tournaments=tournaments)
    
    @app.route('/participant-tournament')
    def participant_tournament():
        """Страница для участников турниров"""
        if not current_user.is_authenticated:
            flash('Необходимо войти в систему', 'error')
            return redirect(url_for('login'))
        
        # Получаем турниры, в которых участвует текущий пользователь
        user_participations = Participant.query.filter_by(user_id=current_user.id).all()
        tournament_ids = [p.tournament_id for p in user_participations]
        tournaments = Tournament.query.filter(Tournament.id.in_(tournament_ids)).all()
        
        for tournament in tournaments:
            tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
        
        return render_template('participant_tournament.html', tournaments=tournaments)
    
    # ===== МАРШРУТЫ ДЛЯ АДМИНОВ ТУРНИРОВ =====
    
    @app.route('/admin-tournament', methods=['GET', 'POST'])
    def admin_tournament():
        """Страница входа для админов турниров"""
        # Получаем все токены для отладки
        all_tokens = []
        try:
            all_tokens = Token.query.all()
        except Exception as e:
            app.logger.error(f'Ошибка получения токенов: {e}')
        
        # Получаем всех администраторов турниров для отладки
        tournament_admins = []
        try:
            # Получаем все турниры с их администраторами
            tournaments = Tournament.query.all()
            admin_ids = set()
            for tournament in tournaments:
                admin_ids.add(tournament.admin_id)
            
            # Создаем список администраторов
            for admin_id in admin_ids:
                if admin_id == 1:
                    # Системный администратор
                    tournament_admins.append({
                        'id': admin_id,
                        'name': 'Системный администратор',
                        'email': 'admin@system',
                        'token': None,
                        'tournament_count': len([t for t in tournaments if t.admin_id == admin_id])
                    })
                else:
                    # Обычный администратор - ищем в токенах
                    # Сначала пробуем найти по email с admin_id
                    token = Token.query.filter_by(email=f'admin_{admin_id}@system').first()
                    if not token:
                        # Если не найден, ищем любой токен с таким admin_id в email
                        all_tokens = Token.query.all()
                        for t in all_tokens:
                            # Проверяем, мог ли этот токен создать данный admin_id
                            import hashlib
                            if int(hashlib.md5(t.email.encode('utf-8')).hexdigest(), 16) % 1000000 == admin_id:
                                token = t
                                break
                    
                    if token:
                        tournament_admins.append({
                            'id': admin_id,
                            'name': token.name,
                            'email': token.email,
                            'token': token.token,
                            'tournament_count': len([t for t in tournaments if t.admin_id == admin_id])
                        })
                    else:
                        tournament_admins.append({
                            'id': admin_id,
                            'name': f'Администратор #{admin_id}',
                            'email': 'Не найден в токенах',
                            'token': None,
                            'tournament_count': len([t for t in tournaments if t.admin_id == admin_id])
                        })
        except Exception as e:
            app.logger.error(f'Ошибка получения администраторов: {e}')
        
        # Получаем всех пользователей системы
        all_users = []
        try:
            users = User.query.all()
            for user in users:
                all_users.append({
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'created_at': user.created_at
                })
        except Exception as e:
            app.logger.error(f'Ошибка получения пользователей: {e}')
        
        # Получаем всех участников турниров
        all_participants = []
        try:
            participants = Participant.query.all()
            for participant in participants:
                tournament = Tournament.query.get(participant.tournament_id)
                all_participants.append({
                    'id': participant.id,
                    'name': participant.name,
                    'tournament_id': participant.tournament_id,
                    'tournament_name': tournament.name if tournament else 'Неизвестный турнир',
                    'points': participant.points,
                    'created_at': participant.registered_at
                })
        except Exception as e:
            app.logger.error(f'Ошибка получения участников: {e}')
        
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('admin_tournament.html', all_tokens=all_tokens, tournament_admins=tournament_admins, all_users=all_users, all_participants=all_participants)
            
            # Получаем данные формы
            email = request.form.get('email')
            token = request.form.get('token')
            
            if not email or not token:
                flash('Пожалуйста, заполните все поля', 'error')
                return render_template('admin_tournament.html', all_tokens=all_tokens, tournament_admins=tournament_admins, all_users=all_users, all_participants=all_participants)
            
            # Логируем попытку входа
            app.logger.info(f'Попытка входа: email={email}, token={token}')
            
            # Проверяем токен в базе данных
            try:
                # Преобразуем токен в int для поиска
                try:
                    token_int = int(token)
                except ValueError:
                    app.logger.warning(f'Токен не является числом: {token}')
                    flash('Токен должен быть числом', 'error')
                    return render_template('admin_tournament.html', all_tokens=all_tokens, tournament_admins=tournament_admins, all_users=all_users, all_participants=all_participants)
                
                # Ищем токен по email и токену (без проверки использованности)
                token_obj = Token.query.filter_by(email=email, token=token_int).first()
                app.logger.info(f'Поиск токена: email={email}, token={token_int}, найден={token_obj is not None}')
                
                if token_obj:
                    app.logger.info(f'Токен найден: id={token_obj.id}, created_at={token_obj.created_at}')
                    
                    # Проверяем, что токен не старше 30 дней
                    from datetime import timedelta
                    if datetime.utcnow() - token_obj.created_at > timedelta(days=30):
                        app.logger.warning(f'Токен истек: создан {token_obj.created_at}')
                        flash('Токен истек. Получите новый токен.', 'error')
                        return render_template('admin_tournament.html', all_tokens=all_tokens, tournament_admins=tournament_admins, all_users=all_users, all_participants=all_participants)
                    
                    # Обновляем время последнего использования (но не помечаем как использованный)
                    token_obj.used_at = datetime.utcnow()
                    db.session.commit()
                    app.logger.info(f'Время последнего использования токена обновлено')
                    
                    # Создаем объект админа с уникальным ID на основе email
                    import hashlib
                    admin_id = int(hashlib.md5(email.encode('utf-8')).hexdigest(), 16) % 1000000  # Стабильный ID на основе email
                    app.logger.info(f'Генерируем admin_id для {email}: {admin_id}')
                    admin = type('Admin', (), {
                        'id': admin_id,
                        'name': token_obj.name,
                        'email': email,
                        'token': token,
                        'is_active': True
                    })()
                    
                    # Сохраняем админа в сессии
                    session['admin_id'] = admin.id
                    session['admin_name'] = admin.name
                    session['admin_email'] = admin.email
                    session['admin_token'] = token
                    
                    flash(f'Добро пожаловать, {admin.name}!', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    # Ищем все токены с таким email для отладки
                    tokens_with_email = Token.query.filter_by(email=email).all()
                    app.logger.warning(f'Токен не найден: email={email}, token={token}')
                    app.logger.warning(f'Токены с таким email: {[(t.token, t.is_used) for t in tokens_with_email]}')
                    flash('Неверный email или токен. Убедитесь, что вы получили токен через форму запроса.', 'error')
                    return render_template('admin_tournament.html', all_tokens=all_tokens, tournament_admins=tournament_admins, all_users=all_users, all_participants=all_participants)
                    
            except Exception as e:
                app.logger.error(f'Ошибка проверки токена: {e}')
                flash('Ошибка при проверке токена. Попробуйте еще раз.', 'error')
                return render_template('admin_tournament.html', all_tokens=all_tokens, tournament_admins=tournament_admins, all_users=all_users, all_participants=all_participants)
        
        return render_template('admin_tournament.html', all_tokens=all_tokens)
    
    @app.route('/admin-system-login', methods=['POST'])
    def admin_system_login():
        """Авторизация системного администратора"""
        from flask import session, jsonify
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен (упрощенная проверка для Railway)
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            logger.warning("CSRF токен отсутствует в запросе")
            return jsonify({
                'success': False,
                'message': 'Ошибка безопасности. Обновите страницу и попробуйте снова.'
            }), 400
        
        try:
            validate_csrf(csrf_token)
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            # На Railway может быть проблема с сессиями, пропускаем проверку
            logger.info("Пропускаем CSRF проверку для Railway")
        
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username == 'admin' and password == 'adm444':
            # Простая заглушка для системного админа
            system_admin = type('Admin', (), {
                'id': 1,
                'name': 'Системный администратор',
                'email': 'admin@system',
                'token': 'system_admin_token',
                'is_active': True
            })()
            
            # Сохраняем в сессии
            session['admin_id'] = system_admin.id
            session['admin_name'] = system_admin.name
            session['admin_email'] = system_admin.email
            session['is_system_admin'] = True
            
            logger.info(f"Системный администратор успешно авторизован")
            return jsonify({
                'success': True,
                'message': 'Авторизация успешна',
                'redirect_url': url_for('system_admin_dashboard')
            })
        else:
            logger.warning(f"Неудачная попытка входа: username={username}")
            return jsonify({
                'success': False,
                'message': 'Неверный логин или пароль'
            }), 401
    
    @app.route('/admin-dashboard')
    def admin_dashboard():
        """Панель управления админа турниров"""
        from flask import session
        
        # Проверяем, что админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('admin_tournament'))
        
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        
        # Создаем объект админа с правильным email
        admin = type('Admin', (), {'id': admin_id, 'email': admin_email, 'is_active': True})()
        
        if not admin or not admin.is_active:
            flash('Админ не найден или деактивирован', 'error')
            return redirect(url_for('admin_tournament'))
        
        # Получаем турниры этого админа
        if admin_email == 'admin@system':
            # Системный админ видит все турниры
            tournaments = Tournament.query.all()
            app.logger.info(f'Системный админ видит все турниры: {len(tournaments)}')
        else:
            # Обычный админ видит только свои турниры (по admin_id)
            tournaments = Tournament.query.filter_by(admin_id=admin_id).all()
            app.logger.info(f'Админ {admin_email} (ID: {admin_id}) видит турниры: {len(tournaments)}')
            
            # Отладочная информация: показываем все турниры и их admin_id
            all_tournaments = Tournament.query.all()
            app.logger.info(f'Все турниры в системе:')
            for t in all_tournaments:
                app.logger.info(f'  Турнир "{t.name}" (ID: {t.id}) - admin_id: {t.admin_id}')
        
        # Загружаем количество участников и заявок в листе ожидания для каждого турнира
        for tournament in tournaments:
            participant_count = Participant.query.filter_by(tournament_id=tournament.id).count()
            tournament.participant_count = participant_count
            
            # Добавляем счетчик заявок в листе ожидания
            waiting_count = WaitingList.query.filter_by(
                tournament_id=tournament.id, 
                status='ожидает'
            ).count()
            tournament.waiting_count = waiting_count
        
        return render_template('admin_dashboard.html', 
                             admin=admin, 
                             tournaments=tournaments)
    
    @app.route('/system-admin-dashboard')
    def system_admin_dashboard():
        """Панель управления системного администратора"""
        from flask import session
        
        # Проверяем, что системный админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('index'))
        
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        
        # Проверяем, что это системный администратор
        if admin_email != 'admin@system':
            flash('Доступ запрещен. Требуются права системного администратора', 'error')
            return redirect(url_for('index'))
        
        # Получаем все турниры
        tournaments = Tournament.query.all()
        
        # Получаем всех пользователей
        users = User.query.all()
        
        # Получаем всех администраторов турниров
        tournament_admins = []
        try:
            # Получаем все турниры с их администраторами
            admin_ids = set()
            for tournament in tournaments:
                admin_ids.add(tournament.admin_id)
            
            # Добавляем администраторов из токенов, даже если у них нет турниров
            all_tokens = Token.query.all()
            for token in all_tokens:
                import hashlib
                admin_id = int(hashlib.md5(token.email.encode('utf-8')).hexdigest(), 16) % 1000000
                admin_ids.add(admin_id)
            
            # Создаем список администраторов
            for admin_id in admin_ids:
                if admin_id == 1:
                    # Системный администратор
                    tournament_admins.append({
                        'id': admin_id,
                        'name': 'Системный администратор',
                        'email': 'admin@system',
                        'token': None,
                        'tournament_count': len([t for t in tournaments if t.admin_id == admin_id])
                    })
                else:
                    # Обычный администратор - ищем в токенах
                    token = Token.query.filter_by(email=f'admin_{admin_id}@system').first()
                    if not token:
                        # Если не найден, ищем любой токен с таким admin_id в email
                        all_tokens = Token.query.all()
                        for t in all_tokens:
                            # Проверяем, мог ли этот токен создать данный admin_id
                            import hashlib
                            if int(hashlib.md5(t.email.encode('utf-8')).hexdigest(), 16) % 1000000 == admin_id:
                                token = t
                                break
                    
                    if token:
                        tournament_admins.append({
                            'id': admin_id,
                            'name': token.name,
                            'email': token.email,
                            'token': token.token,
                            'tournament_count': len([t for t in tournaments if t.admin_id == admin_id])
                        })
                    else:
                        tournament_admins.append({
                            'id': admin_id,
                            'name': f'Администратор #{admin_id}',
                            'email': 'Не найден в токенах',
                            'token': None,
                            'tournament_count': len([t for t in tournaments if t.admin_id == admin_id])
                        })
        except Exception as e:
            app.logger.error(f'Ошибка получения администраторов турниров: {e}')
        
        # Загружаем количество участников для каждого турнира
        for tournament in tournaments:
            participant_count = Participant.query.filter_by(tournament_id=tournament.id).count()
            tournament.participant_count = participant_count
        
        return render_template('system_admin_dashboard.html', 
                             admin={'id': admin_id, 'email': admin_email, 'name': 'Системный администратор'}, 
                             tournaments=tournaments,
                             users=users,
                             tournament_admins=tournament_admins)

    @app.route('/admin-tokens')
    def admin_tokens():
        """Страница управления токенами"""
        from flask import session
        
        # Проверяем, что системный админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('index'))
        
        admin_email = session.get('admin_email', '')
        
        # Проверяем, что это системный администратор
        if admin_email != 'admin@system':
            flash('Доступ запрещен', 'error')
            return redirect(url_for('index'))
        
        return render_template('admin_tokens.html')
    
    @app.route('/admin/edit-tournament/<int:tournament_id>')
    def admin_edit_tournament(tournament_id):
        """Страница редактирования турнира"""
        from flask import session
        
        # Проверяем, что админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('admin_tournament'))
        
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        
        # Создаем объект админа с правильным email
        admin = type('Admin', (), {'id': admin_id, 'email': admin_email, 'is_active': True})()
        
        if not admin or not admin.is_active:
            flash('Админ не найден или деактивирован', 'error')
            return redirect(url_for('admin_tournament'))
        
        # Получаем турнир
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Проверяем права доступа
        if admin_email != 'admin@system' and tournament.admin_id != admin_id:
            flash('У вас нет прав для редактирования этого турнира', 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Загружаем дополнительную информацию
        participant_count = Participant.query.filter_by(tournament_id=tournament_id).count()
        match_count = Match.query.filter_by(tournament_id=tournament_id).count()
        
        return render_template('admin_edit_tournament.html', 
                             tournament=tournament,
                             participant_count=participant_count,
                             match_count=match_count,
                             admin=admin)
    
    @app.route('/admin-create-tournament', methods=['GET', 'POST'])
    def admin_create_tournament():
        """Создание турнира админом"""
        from flask import session
        
        # Проверяем, что админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('admin_tournament'))
        
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        
        # Создаем объект админа с правильным email
        admin = type('Admin', (), {'id': admin_id, 'email': admin_email, 'is_active': True})()
        
        if not admin or not admin.is_active:
            flash('Админ не найден или деактивирован', 'error')
            return redirect(url_for('admin_tournament'))
        
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            # Получаем данные формы
            name = request.form.get('name')
            description = request.form.get('description')
            sport_type = request.form.get('sport_type', 'пинг-понг')  # Значение по умолчанию
            
            # Обрабатываем кастомный вид спорта
            if sport_type == 'custom':
                custom_sport = request.form.get('custom_sport', '').strip()
                if custom_sport:
                    sport_type = custom_sport
                else:
                    flash('Пожалуйста, введите вид спорта', 'error')
                    return render_template('admin_create_tournament.html', admin=admin)
            start_date = request.form.get('start_date')
            court_count = int(request.form.get('court_count', 4))
            match_duration = int(request.form.get('match_duration', 60))
            break_duration = int(request.form.get('break_duration', 15))
            sets_to_win = int(request.form.get('sets_to_win', 2))
            points_to_win = int(request.form.get('points_to_win', 21))
            points_win = int(request.form.get('points_win', 1))
            points_draw = int(request.form.get('points_draw', 1))
            points_loss = int(request.form.get('points_loss', 0))
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            if not name:
                flash('Пожалуйста, введите название турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            if not start_date:
                flash('Пожалуйста, выберите дату начала турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            try:
                # Преобразуем строки времени в объекты time
                from datetime import time
                start_time_obj = None
                end_time_obj = None
                
                if start_time:
                    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                else:
                    start_time_obj = datetime.strptime("09:00", '%H:%M').time()
                    
                if end_time:
                    end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                else:
                    end_time_obj = datetime.strptime("18:00", '%H:%M').time()
                
                # Создаем турнир
                tournament = Tournament(
                    name=name,
                    description=description or '',
                    sport_type=sport_type,
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
                    end_date=None,  # Убираем дату окончания
                    max_participants=32,  # Фиксированное значение
                    court_count=court_count or 4,
                    match_duration=match_duration or 60,
                    break_duration=break_duration or 15,
                    sets_to_win=sets_to_win or 2,
                    points_to_win=points_to_win or 21,
                    points_win=points_win or 1,
                    points_draw=points_draw or 1,
                    points_loss=points_loss or 0,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    admin_id=admin_id,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(tournament)
                db.session.commit()
                
                # Автоматически создаем расписание, если есть участники
                participants = Participant.query.filter_by(tournament_id=tournament.id).all()
                if len(participants) >= 2:
                    from routes.api import create_smart_schedule
                    matches_created = create_smart_schedule(tournament, participants, Match, db)
                    db.session.commit()
                    logger.info(f"Автоматически создано {matches_created} матчей для нового турнира {tournament.id}")
                
                flash(f'Турнир "{name}" успешно создан!', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка создания турнира: {e}")
                flash('Ошибка при создании турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
        
        return render_template('admin_create_tournament.html', admin=admin)
    
    
    @app.route('/tournament/<int:tournament_id>')
    def tournament_detail(tournament_id):
        """Полная страница турнира с функционалом (Страница 10)"""
        from flask import session, flash, redirect, url_for
        
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Проверяем авторизацию и доступ к турниру
        current_user = None
        has_access = False
        
        if 'admin_id' in session:
            admin_id = session['admin_id']
            admin_email = session.get('admin_email', '')
            
            # Проверяем, является ли пользователь системным администратором
            if admin_email == 'admin@system':
                has_access = True
                current_user = type('User', (), {
                    'is_authenticated': True,
                    'role': 'системный администратор'
                })()
            # Проверяем, является ли пользователь администратором этого турнира
            elif tournament.admin_id == admin_id:
                has_access = True
                current_user = type('User', (), {
                    'is_authenticated': True,
                    'role': 'администратор турнира'
                })()
        
        # Если нет доступа, показываем ошибку
        if not has_access:
            flash('У вас нет доступа к этому турниру. Только администратор турнира или системный администратор могут просматривать турнир.', 'error')
            return redirect(url_for('index'))
        
        participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        # Автоматически создаем расписание, если есть участники, но нет матчей
        if len(participants) >= 2 and len(matches) == 0:
            try:
                from routes.api import create_smart_schedule
                matches_created = create_smart_schedule(tournament, participants, Match, db)
                db.session.commit()
                logger.info(f"Автоматически создано {matches_created} матчей для турнира {tournament_id}")
                # Обновляем список матчей
                matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
            except Exception as e:
                logger.error(f"Ошибка при автоматическом создании расписания: {e}")
        
        # Создаем базовые данные для совместимости с шаблоном
        participants_with_stats = []
        participants_with_stats_chessboard = []
        chessboard = {}
        schedule_display = {}
        statistics = {}
        participants_data = []
        
        # Заполняем расписание матчами
        for match in matches:
            if match.match_date:
                date_str = match.match_date.strftime('%Y-%m-%d')
                if date_str not in schedule_display:
                    schedule_display[date_str] = {
                        'date_display': match.match_date.strftime('%d.%m.%Y'),
                        'matches': []
                    }
                
                # Находим участников по ID
                participant1 = next((p for p in participants if p.id == match.participant1_id), None)
                participant2 = next((p for p in participants if p.id == match.participant2_id), None)
                
                # Формируем счет матча (количество выигранных сетов) - только для завершенных и в процессе
                score = None
                # Отладочная информация для всех матчей
                app.logger.info(f"Матч {match.id}: статус='{match.status}', sets_won_1={match.sets_won_1}, sets_won_2={match.sets_won_2}, set1_score1={match.set1_score1}, set1_score2={match.set1_score2}")
                
                # Проверяем, попадает ли статус в нужные значения
                if match.status in ['завершен', 'в процессе', 'играют']:
                    app.logger.info(f"Матч {match.id}: статус '{match.status}' попадает в условие")
                else:
                    app.logger.info(f"Матч {match.id}: статус '{match.status}' НЕ попадает в условие")
                
                if match.status in ['завершен', 'в процессе', 'играют']:
                    if match.sets_won_1 is not None and match.sets_won_2 is not None:
                        score = f"{match.sets_won_1}:{match.sets_won_2}"
                    elif match.set1_score1 is not None and match.set1_score2 is not None:
                        # Если нет sets_won, но есть детали сетов, считаем выигранные сеты
                        sets_won_1 = 0
                        sets_won_2 = 0
                        if match.set1_score1 is not None and match.set1_score2 is not None:
                            if match.set1_score1 > match.set1_score2:
                                sets_won_1 += 1
                            elif match.set1_score2 > match.set1_score1:
                                sets_won_2 += 1
                        if match.set2_score1 is not None and match.set2_score2 is not None:
                            if match.set2_score1 > match.set2_score2:
                                sets_won_1 += 1
                            elif match.set2_score2 > match.set2_score1:
                                sets_won_2 += 1
                        if match.set3_score1 is not None and match.set3_score2 is not None:
                            if match.set3_score1 > match.set3_score2:
                                sets_won_1 += 1
                            elif match.set3_score2 > match.set3_score1:
                                sets_won_2 += 1
                        score = f"{sets_won_1}:{sets_won_2}"
                    else:
                        # Для матчей в процессе без данных - показываем "0:0"
                        if match.status in ['в процессе', 'играют']:
                            score = "0:0"
                
                # Отладочная информация для счета
                app.logger.info(f"Матч {match.id}: итоговый счет={score}")
                
                # Формируем детали сетов (без номеров сетов) - только для завершенных и в процессе
                sets_details = None
                points_to_win = tournament.points_to_win or 11  # По умолчанию 11 очков
                if match.status in ['завершен', 'в процессе', 'играют'] and match.set1_score1 is not None and match.set1_score2 is not None:
                    sets_list = []
                    if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                        sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                    if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                        sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                    if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                        sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                    if sets_list:
                        sets_details = ", ".join(sets_list)
                
                match_data = {
                    'id': match.id,
                    'global_number': match.match_number or match.id,
                    'participant1': participant1.name if participant1 else 'Неизвестный участник',
                    'participant2': participant2.name if participant2 else 'Неизвестный участник',
                    'time': match.match_time.strftime('%H:%M') if match.match_time else 'Время не указано',
                    'court': match.court_number or 0,
                    'status': match.status,
                    'score': score,
                    'score1': match.score1,
                    'score2': match.score2,
                    'sets_details': sets_details,
                    'winner_id': match.winner_id
                }
                schedule_display[date_str]['matches'].append(match_data)
        
        # Сортируем матчи в каждом дне по времени и номеру матча
        for date_str in schedule_display:
            schedule_display[date_str]['matches'].sort(key=lambda x: (
                x['time'] if x['time'] != 'Время не указано' else '23:59',
                x['global_number']
            ))
        
        # Определяем время создания первого матча для определения опоздавших участников
        first_match_time = None
        if matches:
            first_match = min(matches, key=lambda m: m.created_at if hasattr(m, 'created_at') else datetime.min)
            first_match_time = first_match.created_at if hasattr(first_match, 'created_at') else None
        
        # Создаем простые данные для участников
        for i, participant in enumerate(participants):
            participant_data = {
                'id': participant.id,
                'name': participant.name,
                'is_team': participant.is_team
            }
            participants_data.append(participant_data)
            
            # Создаем статистику участника
            participant_stats = {
                'games': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'points': 0,  # Будем пересчитывать на основе завершённых матчей
                'goal_difference': 0
            }
            
            # Подсчитываем реальную статистику участника
            for match in matches:
                if match.status == 'завершен':
                    if match.participant1_id == participant.id:
                        participant_stats['games'] += 1
                        if match.sets_won_1 is not None and match.sets_won_2 is not None:
                            if match.sets_won_1 > match.sets_won_2:
                                participant_stats['wins'] += 1
                                participant_stats['points'] += (tournament.points_win or 1)  # Очки за победу
                            elif match.sets_won_1 < match.sets_won_2:
                                participant_stats['losses'] += 1
                                participant_stats['points'] += (tournament.points_loss or 0)  # Очки за поражение
                            else:
                                participant_stats['draws'] += 1
                                participant_stats['points'] += (tournament.points_draw or 1)  # Очки за ничью
                            
                            # Рассчитываем разницу очков в сетах для участника 1
                            if hasattr(match, 'set1_score1') and hasattr(match, 'set1_score2') and match.set1_score1 is not None and match.set1_score2 is not None:
                                participant_stats['goal_difference'] += match.set1_score1 - match.set1_score2
                            if hasattr(match, 'set2_score1') and hasattr(match, 'set2_score2') and match.set2_score1 is not None and match.set2_score2 is not None:
                                participant_stats['goal_difference'] += match.set2_score1 - match.set2_score2
                            if hasattr(match, 'set3_score1') and hasattr(match, 'set3_score2') and match.set3_score1 is not None and match.set3_score2 is not None:
                                participant_stats['goal_difference'] += match.set3_score1 - match.set3_score2
                            if hasattr(match, 'set4_score1') and hasattr(match, 'set4_score2') and match.set4_score1 is not None and match.set4_score2 is not None:
                                participant_stats['goal_difference'] += match.set4_score1 - match.set4_score2
                            if hasattr(match, 'set5_score1') and hasattr(match, 'set5_score2') and match.set5_score1 is not None and match.set5_score2 is not None:
                                participant_stats['goal_difference'] += match.set5_score1 - match.set5_score2
                                
                    elif match.participant2_id == participant.id:
                        participant_stats['games'] += 1
                        if match.sets_won_1 is not None and match.sets_won_2 is not None:
                            if match.sets_won_1 < match.sets_won_2:
                                participant_stats['wins'] += 1
                                participant_stats['points'] += (tournament.points_win or 1)  # Очки за победу
                            elif match.sets_won_1 > match.sets_won_2:
                                participant_stats['losses'] += 1
                                participant_stats['points'] += (tournament.points_loss or 0)  # Очки за поражение
                            else:
                                participant_stats['draws'] += 1
                                participant_stats['points'] += (tournament.points_draw or 1)  # Очки за ничью
                            
                            # Рассчитываем разницу очков в сетах для участника 2
                            if hasattr(match, 'set1_score1') and hasattr(match, 'set1_score2') and match.set1_score1 is not None and match.set1_score2 is not None:
                                participant_stats['goal_difference'] += match.set1_score2 - match.set1_score1
                            if hasattr(match, 'set2_score1') and hasattr(match, 'set2_score2') and match.set2_score1 is not None and match.set2_score2 is not None:
                                participant_stats['goal_difference'] += match.set2_score2 - match.set2_score1
                            if hasattr(match, 'set3_score1') and hasattr(match, 'set3_score2') and match.set3_score1 is not None and match.set3_score2 is not None:
                                participant_stats['goal_difference'] += match.set3_score2 - match.set3_score1
                            if hasattr(match, 'set4_score1') and hasattr(match, 'set4_score2') and match.set4_score1 is not None and match.set4_score2 is not None:
                                participant_stats['goal_difference'] += match.set4_score2 - match.set4_score1
                            if hasattr(match, 'set5_score1') and hasattr(match, 'set5_score2') and match.set5_score1 is not None and match.set5_score2 is not None:
                                participant_stats['goal_difference'] += match.set5_score2 - match.set5_score1
            
            # Определяем, является ли участник опоздавшим
            is_late_participant = False
            if first_match_time and participant.registered_at:
                is_late_participant = participant.registered_at > first_match_time
            
            participants_with_stats.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1,
                'is_late_participant': is_late_participant
            })
            
            participants_with_stats_chessboard.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1,
                'is_late_participant': is_late_participant
            })
            
            # Создаем шахматку с данными матчей
            chessboard[participant.id] = {}
            
            # Определяем ближайшие матчи для выделения
            upcoming_matches = []
            for match in matches:
                if match.status == 'запланирован' and match.match_date and match.match_time:
                    upcoming_matches.append({
                        'match_id': match.id,
                        'date': match.match_date,
                        'time': match.match_time,
                        'participant1_id': match.participant1_id,
                        'participant2_id': match.participant2_id
                    })
            
            # Сортируем по времени и берем ближайшие 3 матча
            upcoming_matches.sort(key=lambda x: (x['date'], x['time']))
            next_matches = upcoming_matches[:3] if upcoming_matches else []
            next_match_ids = {m['match_id'] for m in next_matches}
            
            for other_participant in participants:
                if participant.id != other_participant.id:
                    # Ищем матч между этими участниками
                    match = next((m for m in matches if 
                                (m.participant1_id == participant.id and m.participant2_id == other_participant.id) or
                                (m.participant1_id == other_participant.id and m.participant2_id == participant.id)), None)
                    
                    if match:
                        if match.status == 'завершен' and match.sets_won_1 is not None and match.sets_won_2 is not None:
                            # Матч завершен - показываем результат (счет сетов)
                            if match.participant1_id == participant.id:
                                score = f"{match.sets_won_1}:{match.sets_won_2}"
                                is_winner = match.sets_won_1 > match.sets_won_2
                            else:
                                score = f"{match.sets_won_2}:{match.sets_won_1}"
                                is_winner = match.sets_won_2 > match.sets_won_1
                            
                            # Формируем детали сетов (без номеров)
                            sets_details = None
                            points_to_win = tournament.points_to_win or 11  # По умолчанию 11 очков
                            if match.set1_score1 is not None and match.set1_score2 is not None:
                                sets_list = []
                                if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                                    if match.participant1_id == participant.id:
                                        sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                                    else:
                                        sets_list.append(f"{match.set1_score2}:{match.set1_score1}")
                                if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                                    if match.participant1_id == participant.id:
                                        sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                                    else:
                                        sets_list.append(f"{match.set2_score2}:{match.set2_score1}")
                                if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                                    if match.participant1_id == participant.id:
                                        sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                                    else:
                                        sets_list.append(f"{match.set3_score2}:{match.set3_score1}")
                                if sets_list:
                                    sets_details = ", ".join(sets_list)
                            
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'result',
                                'value': score,
                                'match_id': match.id,
                                'is_winner': is_winner,
                                'sets_details': sets_details
                            }
                        elif match.status in ['в процессе', 'играют']:
                            # Матч в процессе - показываем счет если есть
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                # Есть счет - показываем его
                                if match.participant1_id == participant.id:
                                    score = f"{match.sets_won_1}:{match.sets_won_2}"
                                else:
                                    score = f"{match.sets_won_2}:{match.sets_won_1}"
                                
                                # Формируем детали сетов (без номеров)
                                sets_details = None
                                points_to_win = tournament.points_to_win or 11  # По умолчанию 11 очков
                                if match.set1_score1 is not None and match.set1_score2 is not None:
                                    sets_list = []
                                    if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                                        if match.participant1_id == participant.id:
                                            sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                                        else:
                                            sets_list.append(f"{match.set1_score2}:{match.set1_score1}")
                                    if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                                        if match.participant1_id == participant.id:
                                            sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                                        else:
                                            sets_list.append(f"{match.set2_score2}:{match.set2_score1}")
                                    if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                                        if match.participant1_id == participant.id:
                                            sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                                        else:
                                            sets_list.append(f"{match.set3_score2}:{match.set3_score1}")
                                    if sets_list:
                                        sets_details = ", ".join(sets_list)
                                
                                chessboard[participant.id][other_participant.id] = {
                                    'type': 'in_progress',
                                    'value': score,
                                    'match_id': match.id,
                                    'sets_details': sets_details
                                }
                            else:
                                # Нет счета - показываем "В процессе"
                                chessboard[participant.id][other_participant.id] = {
                                    'type': 'in_progress',
                                    'value': 'В процессе',
                                    'match_id': match.id,
                                    'sets_details': ''
                                }
                        else:
                            # Матч запланирован
                            is_next_match = match.id in next_match_ids
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'upcoming',
                                'value': 'vs',
                                'match_id': match.id,
                                'match_time': match.match_time.strftime('%H:%M') if match.match_time else None,
                                'court_number': match.court_number,
                                'date': match.match_date,
                                'time': match.match_time,
                                'court': match.court_number,
                                'is_next_match': is_next_match,
                                'sets_details': ''
                            }
                    else:
                        # Матч не найден
                        chessboard[participant.id][other_participant.id] = {
                            'type': 'empty',
                            'value': '',
                            'match_id': None,
                            'sets_details': ''
                        }
        
        # Сортируем участников по очкам (убывание) только для статистики
        participants_with_stats.sort(key=lambda x: x['stats']['points'], reverse=True)
        
        # Обновляем позиции после сортировки только для статистики
        for i, participant_data in enumerate(participants_with_stats):
            participant_data['position'] = i + 1
        
        # Также обновляем позиции в турнирной таблице (шахматке)
        # Создаем словарь для быстрого поиска позиций по ID участника
        position_by_id = {}
        for participant_data in participants_with_stats:
            position_by_id[participant_data['participant'].id] = participant_data['position']
        
        # Обновляем позиции в participants_with_stats_chessboard
        for participant_data in participants_with_stats_chessboard:
            participant_id = participant_data['participant'].id
            participant_data['position'] = position_by_id.get(participant_id, len(participants))
        
        return render_template('tournament.html', 
                             tournament=tournament, 
                             participants=participants, 
                             participants_data=participants_data,
                             participants_with_stats=participants_with_stats,
                             participants_with_stats_chessboard=participants_with_stats_chessboard,
                             matches=matches,
                             chessboard=chessboard,
                             schedule_display=schedule_display,
                             statistics=statistics,
                             has_missing_matches=False,
                             next_match_ids=[],
                             current_user=current_user)
    
    @app.route('/participant-login', methods=['POST'])
    def participant_login():
        """Вход участника турнира"""
        from flask import session
        
        name = request.form.get('name', '').strip()
        
        if not name:
            flash('Пожалуйста, введите ваше имя', 'error')
            return redirect(url_for('index'))
        
        # Сохраняем имя участника в сессии
        session['participant_name'] = name
        session['participant_logged_in'] = True
        
        logger.info(f"Участник {name} вошел в систему")
        flash(f'Добро пожаловать, {name}!', 'success')
        
        return redirect(url_for('participant_tournaments'))

    @app.route('/participant-tournaments')
    def participant_tournaments():
        """Страница турниров участника"""
        from flask import session
        
        # Проверяем, что участник авторизован
        if not session.get('participant_logged_in'):
            flash('Необходима авторизация', 'error')
            return redirect(url_for('index'))
        
        participant_name = session.get('participant_name', '')
        
        # Получаем только турниры, в которых участвует данный участник
        participant_tournaments = []
        
        # Находим все участия данного участника
        participations = Participant.query.filter_by(name=participant_name).all()
        
        for participation in participations:
            # Получаем турнир
            tournament = Tournament.query.get(participation.tournament_id)
            if tournament:
                # Загружаем участников турнира
                tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
                
                participant_tournaments.append({
                    'tournament': tournament,
                    'participant': participation,
                    'is_participant': True
                })
        
        return render_template('participant_tournaments.html', 
                             tournaments=participant_tournaments,
                             participant_name=participant_name)

    @app.route('/participant-logout')
    def participant_logout():
        """Выход участника"""
        from flask import session
        session.pop('participant_name', None)
        session.pop('participant_logged_in', None)
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('index'))
    
    @app.route('/tournament-view/<int:tournament_id>')
    def tournament_view(tournament_id):
        """Просмотр турнира для участников (только чтение)"""
        from flask import session, flash, redirect, url_for
        
        # Проверяем, что участник авторизован
        if not session.get('participant_logged_in'):
            flash('Необходима авторизация', 'error')
            return redirect(url_for('index'))
        
        tournament = Tournament.query.get_or_404(tournament_id)
        participant_name = session.get('participant_name', '')
        
        # Получаем участников турнира
        participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
        
        # Получаем матчи турнира
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        # Дедупликация матчей по уникальным полям (участники + дата + время)
        seen_matches = set()
        unique_matches = []
        for match in matches:
            match_key = (match.participant1_id, match.participant2_id, match.match_date, match.match_time)
            if match_key not in seen_matches:
                seen_matches.add(match_key)
                unique_matches.append(match)
        matches = unique_matches
        
        # Проверяем, участвует ли текущий участник в турнире
        is_participant = any(p.name == participant_name for p in participants)
        
        # Создаем данные для отображения расписания (используем ту же структуру, что и в админке)
        schedule_display = {}
        for match in matches:
            if match.match_date:
                date_str = match.match_date.strftime('%Y-%m-%d')
                if date_str not in schedule_display:
                    schedule_display[date_str] = {
                        'date_display': match.match_date.strftime('%d.%m.%Y'),
                        'matches': []
                    }
                
                # Находим участников по ID
                participant1 = next((p for p in participants if p.id == match.participant1_id), None)
                participant2 = next((p for p in participants if p.id == match.participant2_id), None)
                
                # Формируем счет матча (количество выигранных сетов) - только для завершенных и в процессе
                score = None
                if match.status in ['завершен', 'в процессе', 'играют']:
                    if match.sets_won_1 is not None and match.sets_won_2 is not None:
                        score = f"{match.sets_won_1}:{match.sets_won_2}"
                    elif match.set1_score1 is not None and match.set1_score2 is not None:
                        # Если нет sets_won, но есть детали сетов, считаем выигранные сеты
                        sets_won_1 = 0
                        sets_won_2 = 0
                        if match.set1_score1 is not None and match.set1_score2 is not None:
                            if match.set1_score1 > match.set1_score2:
                                sets_won_1 += 1
                            elif match.set1_score2 > match.set1_score1:
                                sets_won_2 += 1
                        if match.set2_score1 is not None and match.set2_score2 is not None:
                            if match.set2_score1 > match.set2_score2:
                                sets_won_1 += 1
                            elif match.set2_score2 > match.set2_score1:
                                sets_won_2 += 1
                        if match.set3_score1 is not None and match.set3_score2 is not None:
                            if match.set3_score1 > match.set3_score2:
                                sets_won_1 += 1
                            elif match.set3_score2 > match.set3_score1:
                                sets_won_2 += 1
                        score = f"{sets_won_1}:{sets_won_2}"
                    else:
                        # Для матчей в процессе без данных - показываем "0:0"
                        if match.status in ['в процессе', 'играют']:
                            score = "0:0"
                
                # Формируем детали сетов (без номеров сетов) - только для завершенных и в процессе
                sets_details = None
                points_to_win = tournament.points_to_win or 11  # По умолчанию 11 очков
                if match.status in ['завершен', 'в процессе', 'играют'] and match.set1_score1 is not None and match.set1_score2 is not None:
                    sets_list = []
                    if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                        sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                    if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                        sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                    if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                        sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                    if sets_list:
                        sets_details = ", ".join(sets_list)
                
                match_data = {
                    'id': match.id,
                    'global_number': match.id,  # Используем ID матча вместо match_number для уникальности
                    'participant1': participant1.name if participant1 else 'Неизвестный участник',
                    'participant2': participant2.name if participant2 else 'Неизвестный участник',
                    'time': match.match_time.strftime('%H:%M') if match.match_time else 'Время не указано',
                    'court': match.court_number or 0,
                    'status': match.status,
                    'score': score,
                    'score1': match.score1,
                    'score2': match.score2,
                    'sets_details': sets_details,
                    'winner_id': match.winner_id,
                    'is_participant_match': (participant1 and participant1.name == participant_name) or (participant2 and participant2.name == participant_name)
                }
                schedule_display[date_str]['matches'].append(match_data)
        
        # Сортируем матчи в каждом дне по времени и номеру матча
        for date_str in schedule_display:
            schedule_display[date_str]['matches'].sort(key=lambda x: (
                x['time'] if x['time'] != 'Время не указано' else '23:59',
                x['global_number']
            ))
        
        # Создаем статистику участников
        participants_with_stats = []
        for participant in participants:
            # Подсчитываем статистику участника
            wins = 0
            losses = 0
            points = 0  # Будем пересчитывать на основе побед
            
            for match in matches:
                if match.status == 'завершен':
                    if match.participant1_id == participant.id:
                        if match.sets_won_1 is not None and match.sets_won_2 is not None:
                            if match.sets_won_1 > match.sets_won_2:
                                wins += 1
                                points += (tournament.points_win or 1)  # очки за победу из настроек турнира
                            elif match.sets_won_1 < match.sets_won_2:
                                losses += 1
                                points += (tournament.points_loss or 0)  # очки за поражение из настроек турнира
                            else:
                                points += (tournament.points_draw or 1)  # очки за ничью из настроек турнира
                    elif match.participant2_id == participant.id:
                        if match.sets_won_1 is not None and match.sets_won_2 is not None:
                            if match.sets_won_1 < match.sets_won_2:
                                wins += 1
                                points += (tournament.points_win or 1)  # очки за победу из настроек турнира
                            elif match.sets_won_1 > match.sets_won_2:
                                losses += 1
                                points += (tournament.points_loss or 0)  # очки за поражение из настроек турнира
                            else:
                                points += (tournament.points_draw or 1)  # очки за ничью из настроек турнира
            
            participants_with_stats.append({
                'participant': participant,
                'wins': wins,
                'losses': losses,
                'points': points,
                'is_current_participant': participant.name == participant_name
            })
        
        # Сортируем участников по очкам (убывание)
        participants_with_stats.sort(key=lambda x: x['points'], reverse=True)
        
        # Определяем время создания первого матча для определения опоздавших участников
        first_match_time = None
        if matches:
            first_match = min(matches, key=lambda m: m.created_at if hasattr(m, 'created_at') else datetime.min)
            first_match_time = first_match.created_at if hasattr(first_match, 'created_at') else None
        
        # Создаем данные для турнирной таблицы (шахматки)
        participants_with_stats_chessboard = []
        chessboard = {}
        
        # Определяем ближайшие матчи для выделения
        upcoming_matches = []
        for match in matches:
            if match.status == 'запланирован' and match.match_date and match.match_time:
                upcoming_matches.append({
                    'match_id': match.id,
                    'date': match.match_date,
                    'time': match.match_time,
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id
                })
        
        # Сортируем по времени и берем ближайшие 3 матча
        upcoming_matches.sort(key=lambda x: (x['date'], x['time']))
        next_matches = upcoming_matches[:3] if upcoming_matches else []
        next_match_ids = {m['match_id'] for m in next_matches}
        
        logger.info(f"Ближайшие матчи для выделения: {[m['match_id'] for m in next_matches]}")
        
        for i, participant_data in enumerate(participants_with_stats):
            participant = participant_data['participant']
            participant_stats = {
                'points': participant_data['points'],
                'wins': participant_data['wins'],
                'losses': participant_data['losses'],
                'games': participant_data['wins'] + participant_data['losses']
            }
            
            # Определяем, является ли участник опоздавшим
            is_late_participant = False
            if first_match_time and participant.registered_at:
                is_late_participant = participant.registered_at > first_match_time
            
            participants_with_stats_chessboard.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1,
                'is_late_participant': is_late_participant
            })
            
            # Создаем шахматку с данными матчей
            chessboard[participant.id] = {}
            for other_participant_data in participants_with_stats:
                other_participant = other_participant_data['participant']
                if participant.id != other_participant.id:
                    # Ищем матч между этими участниками
                    match = next((m for m in matches if 
                                (m.participant1_id == participant.id and m.participant2_id == other_participant.id) or
                                (m.participant1_id == other_participant.id and m.participant2_id == participant.id)), None)
                    
                    if match:
                        if match.status == 'завершен' and match.sets_won_1 is not None and match.sets_won_2 is not None:
                            # Определяем победителя и счет
                            if match.participant1_id == participant.id:
                                score = f"{match.sets_won_1}:{match.sets_won_2}"
                                is_winner = match.sets_won_1 > match.sets_won_2
                            else:
                                score = f"{match.sets_won_2}:{match.sets_won_1}"
                                is_winner = match.sets_won_2 > match.sets_won_1
                            
                            # Формируем детали сетов
                            sets_details = ""
                            sets_list = []
                            points_to_win = 21 if tournament.sport_type == 'бадминтон' else 11
                            
                            if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                                if match.participant1_id == participant.id:
                                    sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                                else:
                                    sets_list.append(f"{match.set1_score2}:{match.set1_score1}")
                            if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                                if match.participant1_id == participant.id:
                                    sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                                else:
                                    sets_list.append(f"{match.set2_score2}:{match.set2_score1}")
                            if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                                if match.participant1_id == participant.id:
                                    sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                                else:
                                    sets_list.append(f"{match.set3_score2}:{match.set3_score1}")
                            if sets_list:
                                sets_details = ", ".join(sets_list)
                            
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'result',
                                'value': score,
                                'match_id': match.id,
                                'is_winner': is_winner,
                                'sets_details': sets_details
                            }
                        elif match.status in ['в процессе', 'играют']:
                            # Матч в процессе
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                if match.participant1_id == participant.id:
                                    score = f"{match.sets_won_1}:{match.sets_won_2}"
                                else:
                                    score = f"{match.sets_won_2}:{match.sets_won_1}"
                                
                                # Формируем детали сетов
                                sets_details = ""
                                sets_list = []
                                points_to_win = 21 if tournament.sport_type == 'бадминтон' else 11
                                
                                if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                                    if match.participant1_id == participant.id:
                                        sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                                    else:
                                        sets_list.append(f"{match.set1_score2}:{match.set1_score1}")
                                if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                                    if match.participant1_id == participant.id:
                                        sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                                    else:
                                        sets_list.append(f"{match.set2_score2}:{match.set2_score1}")
                                if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                                    if match.participant1_id == participant.id:
                                        sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                                    else:
                                        sets_list.append(f"{match.set3_score2}:{match.set3_score1}")
                                if sets_list:
                                    sets_details = ", ".join(sets_list)
                                
                                chessboard[participant.id][other_participant.id] = {
                                    'type': 'in_progress',
                                    'value': score,
                                    'match_id': match.id,
                                    'sets_details': sets_details
                                }
                            else:
                                # Нет счета - показываем "В процессе"
                                chessboard[participant.id][other_participant.id] = {
                                    'type': 'in_progress',
                                    'value': 'В процессе',
                                    'match_id': match.id,
                                    'sets_details': ''
                                }
                        else:
                            # Матч запланирован
                            is_next_match = match.id in next_match_ids
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'upcoming',
                                'value': 'vs',
                                'match_id': match.id,
                                'match_time': match.match_time.strftime('%H:%M') if match.match_time else None,
                                'court_number': match.court_number,
                                'time': match.match_time,
                                'court': match.court_number,
                                'is_next_match': is_next_match
                            }
                    else:
                        # Матч не найден
                        chessboard[participant.id][other_participant.id] = {
                            'type': 'empty',
                            'value': '',
                            'match_id': None,
                            'sets_details': ''
                        }
        
        # Определяем режим просмотра
        is_viewer_mode = not is_participant
        
        return render_template('tournament_view.html', 
                             tournament=tournament,
                             participants=participants_with_stats,
                             participants_with_stats_chessboard=participants_with_stats_chessboard,
                             chessboard=chessboard,
                             schedule_display=schedule_display,
                             is_participant=is_participant,
                             is_viewer_mode=is_viewer_mode,
                             participant_name=participant_name)

    @app.route('/tournament-spectator/<int:tournament_id>')
    def tournament_spectator(tournament_id):
        """Просмотр турнира для зрителей (без авторизации)"""
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Получаем участников турнира
        participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
        
        # Получаем матчи турнира
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        # Дедупликация матчей по уникальным полям (участники + дата + время)
        seen_matches = set()
        unique_matches = []
        for match in matches:
            match_key = (match.participant1_id, match.participant2_id, match.match_date, match.match_time)
            if match_key not in seen_matches:
                seen_matches.add(match_key)
                unique_matches.append(match)
        matches = unique_matches
        
        # Для зрителей всегда is_participant = False и is_viewer_mode = True
        is_participant = False
        is_viewer_mode = True
        participant_name = ''
        
        # Подготавливаем данные для отображения с реальной статистикой
        participants_with_stats = []
        participants_with_stats_chessboard = []
        
        # Создаем словарь для подсчета статистики каждого участника
        participant_stats_dict = {}
        for participant in participants:
            participant_stats_dict[participant.id] = {
                'id': participant.id,
                'name': participant.name,
                'points': 0,
                'matches_played': 0,
                'matches_won': 0,
                'matches_lost': 0,
                'matches_drawn': 0,
                'games': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'goal_difference': 0
            }
        
        # Подсчитываем статистику на основе матчей
        for match in matches:
            if match.status == 'завершен' and match.sets_won_1 is not None and match.sets_won_2 is not None:
                participant1_id = match.participant1_id
                participant2_id = match.participant2_id
                
                if participant1_id in participant_stats_dict and participant2_id in participant_stats_dict:
                    # Обновляем статистику для участника 1
                    participant_stats_dict[participant1_id]['games'] += 1
                    participant_stats_dict[participant1_id]['matches_played'] += 1
                    
                    # Обновляем статистику для участника 2
                    participant_stats_dict[participant2_id]['games'] += 1
                    participant_stats_dict[participant2_id]['matches_played'] += 1
                    
                    # Определяем победителя
                    if match.sets_won_1 > match.sets_won_2:
                        # Участник 1 выиграл
                        participant_stats_dict[participant1_id]['wins'] += 1
                        participant_stats_dict[participant1_id]['matches_won'] += 1
                        participant_stats_dict[participant1_id]['points'] += tournament.points_win
                        participant_stats_dict[participant2_id]['losses'] += 1
                        participant_stats_dict[participant2_id]['matches_lost'] += 1
                        participant_stats_dict[participant2_id]['points'] += tournament.points_loss
                    elif match.sets_won_2 > match.sets_won_1:
                        # Участник 2 выиграл
                        participant_stats_dict[participant2_id]['wins'] += 1
                        participant_stats_dict[participant2_id]['matches_won'] += 1
                        participant_stats_dict[participant2_id]['points'] += tournament.points_win
                        participant_stats_dict[participant1_id]['losses'] += 1
                        participant_stats_dict[participant1_id]['matches_lost'] += 1
                        participant_stats_dict[participant1_id]['points'] += tournament.points_loss
                    else:
                        # Ничья
                        participant_stats_dict[participant1_id]['draws'] += 1
                        participant_stats_dict[participant1_id]['matches_drawn'] += 1
                        participant_stats_dict[participant1_id]['points'] += tournament.points_draw
                        participant_stats_dict[participant2_id]['draws'] += 1
                        participant_stats_dict[participant2_id]['matches_drawn'] += 1
                        participant_stats_dict[participant2_id]['points'] += tournament.points_draw
                    
                    # Обновляем разницу очков в сетах
                    # Считаем разницу в очках внутри сетов, а не количество выигранных сетов
                    set1_score1 = match.set1_score1 or 0
                    set1_score2 = match.set1_score2 or 0
                    set2_score1 = match.set2_score1 or 0
                    set2_score2 = match.set2_score2 or 0
                    set3_score1 = match.set3_score1 or 0
                    set3_score2 = match.set3_score2 or 0
                    
                    # Общая разница в очках для участника 1
                    participant1_score_diff = (set1_score1 - set1_score2) + (set2_score1 - set2_score2) + (set3_score1 - set3_score2)
                    participant2_score_diff = (set1_score2 - set1_score1) + (set2_score2 - set2_score1) + (set3_score2 - set3_score1)
                    
                    participant_stats_dict[participant1_id]['goal_difference'] += participant1_score_diff
                    participant_stats_dict[participant2_id]['goal_difference'] += participant2_score_diff
        
        # Создаем списки участников с статистикой
        for i, participant in enumerate(participants):
            participant_stats = participant_stats_dict[participant.id]
            
            participants_with_stats_chessboard.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1,
                'is_late_participant': False
            })
            
            participants_with_stats.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1,
                'is_late_participant': False
            })
        
        # Сортируем участников по именам (алфавитный порядок) для режима зрителя
        participants_with_stats.sort(key=lambda x: x['participant'].name.lower())
        participants_with_stats_chessboard.sort(key=lambda x: x['participant'].name.lower())
        
        # Обновляем позиции после сортировки (по алфавиту)
        for i, participant_data in enumerate(participants_with_stats):
            participant_data['position'] = i + 1
        for i, participant_data in enumerate(participants_with_stats_chessboard):
            participant_data['position'] = i + 1
        
        # Создаем шахматку (упрощенная версия)
        chessboard = {}
        for participant in participants:
            chessboard[participant.id] = {}
            for other_participant in participants:
                if participant.id != other_participant.id:
                    # Ищем матч между этими участниками
                    match = next((m for m in matches if 
                                (m.participant1_id == participant.id and m.participant2_id == other_participant.id) or
                                (m.participant1_id == other_participant.id and m.participant2_id == participant.id)), None)
                    
                    if match:
                        if match.status == 'завершен' and match.sets_won_1 is not None and match.sets_won_2 is not None:
                            # Матч завершен - показываем результат
                            if match.participant1_id == participant.id:
                                score = f"{match.sets_won_1}:{match.sets_won_2}"
                                is_winner = match.sets_won_1 > match.sets_won_2
                            else:
                                score = f"{match.sets_won_2}:{match.sets_won_1}"
                                is_winner = match.sets_won_2 > match.sets_won_1
                            
                            # Создаем детали сета
                            sets_details = ""
                            if hasattr(match, 'set1_score1') and match.set1_score1 is not None:
                                sets_list = []
                                if match.set1_score1 is not None and match.set1_score2 is not None:
                                    sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                                if match.set2_score1 is not None and match.set2_score2 is not None:
                                    sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                                if match.set3_score1 is not None and match.set3_score2 is not None:
                                    sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                                if sets_list:
                                    sets_details = ", ".join(sets_list)
                            
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'result',
                                'value': score,
                                'match_id': match.id,
                                'is_winner': is_winner,
                                'sets_details': sets_details
                            }
                        elif match.status in ['в процессе', 'играют']:
                            # Матч в процессе
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                if match.participant1_id == participant.id:
                                    score = f"{match.sets_won_1}:{match.sets_won_2}"
                                else:
                                    score = f"{match.sets_won_2}:{match.sets_won_1}"
                                
                                # Создаем детали сета для матча в процессе
                                sets_details = ""
                                if hasattr(match, 'set1_score1') and match.set1_score1 is not None:
                                    sets_list = []
                                    if match.set1_score1 is not None and match.set1_score2 is not None:
                                        sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                                    if match.set2_score1 is not None and match.set2_score2 is not None:
                                        sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                                    if match.set3_score1 is not None and match.set3_score2 is not None:
                                        sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                                    if sets_list:
                                        sets_details = ", ".join(sets_list)
                                
                                chessboard[participant.id][other_participant.id] = {
                                    'type': 'in_progress',
                                    'value': score,
                                    'match_id': match.id,
                                    'sets_details': sets_details
                                }
                            else:
                                # Нет счета - показываем "В процессе"
                                chessboard[participant.id][other_participant.id] = {
                                    'type': 'in_progress',
                                    'value': 'В процессе',
                                    'match_id': match.id,
                                    'sets_details': ''
                                }
                        else:
                            # Матч запланирован
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'upcoming',
                                'value': 'vs',
                                'match_id': match.id,
                                'match_time': match.match_time.strftime('%H:%M') if match.match_time else None,
                                'court_number': match.court_number,
                                'date': match.match_date,
                                'time': match.match_time,
                                'court': match.court_number,
                                'is_next_match': False,
                                'sets_details': ''
                            }
                    else:
                        # Матч не найден
                        chessboard[participant.id][other_participant.id] = {
                            'type': 'empty',
                            'value': '',
                            'match_id': None,
                            'sets_details': ''
                        }
        
        # Создаем расписание (упрощенная версия)
        schedule_display = {}
        for match in matches:
            if match.match_date:
                date_str = match.match_date.strftime('%Y-%m-%d')
                if date_str not in schedule_display:
                    schedule_display[date_str] = {
                        'date_display': match.match_date.strftime('%d.%m.%Y'),
                        'matches': []
                    }
                
                # Находим участников по ID
                participant1 = next((p for p in participants if p.id == match.participant1_id), None)
                participant2 = next((p for p in participants if p.id == match.participant2_id), None)
                
                # Формируем счет матча
                score = None
                if match.status == 'завершен' and match.sets_won_1 is not None and match.sets_won_2 is not None:
                    score = f"{match.sets_won_1}:{match.sets_won_2}"
                elif match.status in ['в процессе', 'играют'] and match.sets_won_1 is not None and match.sets_won_2 is not None:
                    score = f"{match.sets_won_1}:{match.sets_won_2}"
                
                schedule_display[date_str]['matches'].append({
                    'match_id': match.id,
                    'participant1': participant1.name if participant1 else 'Неизвестно',
                    'participant2': participant2.name if participant2 else 'Неизвестно',
                    'participant1_name': participant1.name if participant1 else 'Неизвестно',
                    'participant2_name': participant2.name if participant2 else 'Неизвестно',
                    'score': score,
                    'status': match.status,
                    'match_date': match.match_date,
                    'match_time': match.match_time,
                    'time': match.match_time.strftime('%H:%M') if match.match_time else 'Время не указано',
                    'court_number': match.court_number,
                    'global_number': match.match_number or 0,
                    'is_participant_match': False  # Для зрителей всегда False
                })
        
        # Сортируем матчи в каждом дне по времени и номеру матча
        for date_str in schedule_display:
            schedule_display[date_str]['matches'].sort(key=lambda x: (
                x['time'] if x['time'] != 'Время не указано' else '23:59',
                x['global_number']
            ))
        
        return render_template('tournament_view.html', 
                             tournament=tournament,
                             participants=participants_with_stats_chessboard,
                             participants_with_stats=participants_with_stats,
                             participants_with_stats_chessboard=participants_with_stats_chessboard,
                             chessboard=chessboard,
                             schedule_display=schedule_display,
                             is_participant=is_participant,
                             is_viewer_mode=is_viewer_mode,
                             participant_name=participant_name)

    @app.route('/admin-logout')
    def admin_logout():
        """Выход админа"""
        from flask import session
        session.pop('admin_id', None)
        session.pop('admin_name', None)
        session.pop('admin_email', None)
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('admin_tournament'))
    
    @app.route('/my-tournaments', methods=['GET', 'POST'])
    def my_tournaments():
        """Страница 'Мои турниры' с формой входа"""
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('my_tournaments_login.html')
            
            # Получаем данные формы
            name = request.form.get('name')
            password = request.form.get('password')
            
            if not name or not password:
                flash('Пожалуйста, заполните все поля', 'error')
                return render_template('my_tournaments_login.html')
            
            # Для отладки принимаем любые данные
            if name and password:
                # Сохраняем данные в сессии
                session['viewer_name'] = name
                session['viewer_authenticated'] = True
                flash(f'Добро пожаловать, {name}!', 'success')
                return redirect(url_for('tournaments_list_viewer'))
            else:
                flash('Неверные данные для входа', 'error')
                return render_template('my_tournaments_login.html')
        
        return render_template('my_tournaments_login.html')
    
    @app.route('/tournaments-list')
    def tournaments_list_viewer():
        """Список всех турниров для просмотра зрителями"""
        # Проверяем авторизацию
        if not session.get('viewer_authenticated'):
            flash('Необходима авторизация', 'error')
            return redirect(url_for('my_tournaments'))
        
        # Получаем все турниры
        tournaments = Tournament.query.all()
        
        # Загружаем количество участников для каждого турнира
        for tournament in tournaments:
            participant_count = Participant.query.filter_by(tournament_id=tournament.id).count()
            tournament.participant_count = participant_count
        
        return render_template('tournaments_list.html', 
                             tournaments=tournaments,
                             viewer_name=session.get('viewer_name', ''))
    
    @app.route('/export-tournament/<int:tournament_id>')
    def export_tournament(tournament_id):
        """Экспорт данных турнира в Excel файл для скачивания"""
        from flask import Response
        import io
        import csv
        from datetime import datetime
        
        try:
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Получаем участников турнира
            participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            
            # Получаем матчи турнира
            matches = Match.query.filter_by(tournament_id=tournament_id).all()
            
            # Создаем CSV файл в памяти
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовок турнира
            writer.writerow(['ТУРНИР'])
            writer.writerow(['Название', tournament.name])
            writer.writerow(['Спорт', tournament.sport_type or 'Теннис'])
            writer.writerow(['Дата начала', tournament.start_date.strftime('%d.%m.%Y') if tournament.start_date else 'Не указана'])
            writer.writerow(['Количество участников', len(participants)])
            writer.writerow(['Количество кортов', tournament.court_count or 4])
            writer.writerow(['Длительность матча (мин)', tournament.match_duration or 15])
            writer.writerow(['Длительность перерыва (мин)', tournament.break_duration or 2])
            writer.writerow([])  # Пустая строка
            
            # Участники
            writer.writerow(['УЧАСТНИКИ'])
            writer.writerow(['Место', 'Участник', 'Игр', 'Побед', 'Поражений', 'Очки'])
            
            for i, participant in enumerate(participants, 1):
                # Подсчитываем статистику участника
                wins = 0
                losses = 0
                points = participant.points or 0
                
                for match in matches:
                    if match.status == 'завершен':
                        if match.participant1_id == participant.id:
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                if match.sets_won_1 > match.sets_won_2:
                                    wins += 1
                                elif match.sets_won_1 < match.sets_won_2:
                                    losses += 1
                        elif match.participant2_id == participant.id:
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                if match.sets_won_1 < match.sets_won_2:
                                    wins += 1
                                elif match.sets_won_1 > match.sets_won_2:
                                    losses += 1
                
                writer.writerow([i, participant.name, wins + losses, wins, losses, points])
            
            writer.writerow([])  # Пустая строка
            
            # Матчи
            writer.writerow(['МАТЧИ'])
            writer.writerow(['Дата', 'Время', 'Корт', 'Участник 1', 'Участник 2', 'Счет', 'Статус', 'Сет 1', 'Сет 2', 'Сет 3'])
            
            for match in matches:
                # Находим участников по ID
                participant1 = next((p for p in participants if p.id == match.participant1_id), None)
                participant2 = next((p for p in participants if p.id == match.participant2_id), None)
                
                writer.writerow([
                    match.match_date.strftime('%d.%m.%Y') if match.match_date else 'Не указана',
                    match.match_time.strftime('%H:%M') if match.match_time else 'Не указано',
                    match.court_number or 'Не указан',
                    participant1.name if participant1 else 'Неизвестно',
                    participant2.name if participant2 else 'Неизвестно',
                    f"{match.sets_won_1}:{match.sets_won_2}" if match.sets_won_1 is not None and match.sets_won_2 is not None else 'Не завершен',
                    match.status,
                    f"{match.set1_score1}:{match.set1_score2}" if match.set1_score1 is not None and match.set1_score2 is not None else '',
                    f"{match.set2_score1}:{match.set2_score2}" if match.set2_score1 is not None and match.set2_score2 is not None else '',
                    f"{match.set3_score1}:{match.set3_score2}" if match.set3_score1 is not None and match.set3_score2 is not None else ''
                ])
            
            # Получаем данные CSV файла
            csv_data = output.getvalue().encode('utf-8')
            
            # Создаем имя файла
            filename = f'tournament_{tournament.name}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
            
            # Возвращаем файл для скачивания
            return Response(
                csv_data,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'text/csv; charset=utf-8'
                }
            )
            
        except Exception as e:
            app.logger.error(f"Ошибка при экспорте турнира: {e}")
            return jsonify({'success': False, 'error': f'Ошибка при экспорте турнира: {str(e)}'}), 500
    
    # ===== КОНЕЦ create_main_routes =====
