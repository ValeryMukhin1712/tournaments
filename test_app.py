#!/usr/bin/env python3
"""
Тест приложения
"""

import requests
import time

def test_app():
    """Тестирует работу приложения"""
    
    print("🔄 Тестируем приложение...")
    
    # Ждем запуска приложения
    time.sleep(2)
    
    try:
        # Тестируем главную страницу
        response = requests.get('http://127.0.0.1:5000', timeout=10)
        
        if response.status_code == 200:
            print("✅ Приложение работает! Статус: 200")
            print(f"Размер ответа: {len(response.text)} байт")
            
            # Проверяем, есть ли в ответе текст о турнирах
            if "Tournament" in response.text or "турнир" in response.text.lower():
                print("✅ Страница содержит информацию о турнирах")
            else:
                print("⚠️ Страница не содержит информацию о турнирах")
                
        else:
            print(f"❌ Ошибка! Статус: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к приложению")
    except requests.exceptions.Timeout:
        print("❌ Таймаут при подключении")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_app()
