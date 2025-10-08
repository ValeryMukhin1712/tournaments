#!/usr/bin/env python3
"""
Тестирование добавления участника через API
"""
import requests
import json

def test_add_participant():
    """Тестирует добавление участника через API"""
    
    url = "http://localhost:5000/api/tournaments/2/participants"
    data = {
        "name": "Тестовый игрок API",
        "is_team": False
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Статус ответа: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Участник успешно добавлен!")
            else:
                print(f"❌ Ошибка: {result.get('error')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    print("Тестирование добавления участника...")
    test_add_participant()


