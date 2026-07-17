"""
Тест анализа покера через Hand History (более точный метод)
"""

import sys
from pathlib import Path as _Path
_manual_dir = _Path(__file__).resolve().parent
if str(_manual_dir) not in sys.path:
    sys.path.insert(0, str(_manual_dir))
from _root import setup_project_root
setup_project_root()

import requests
import json

# Запустите API сначала:
# uvicorn coach_app.api.main:app --reload --port 8000

API_URL = "http://127.0.0.1:8000"

# Пример hand history PokerStars
hand_history_text = """
PokerStars Hand #123456789: Hold'em No Limit ($0.50/$1.00) - 2026/01/18 2:35:24
Table 'Test Table' 6-max Seat #3 is the button
Seat 1: Hero ($100 in chips)
Seat 2: Villain1 ($100 in chips)
Seat 3: Villain2 ($100 in chips) 
Seat 4: Villain3 ($100 in chips)
Seat 5: Villain4 ($100 in chips)
Seat 6: Villain5 ($100 in chips)
Villain3: posts small blind $0.50
Villain4: posts big blind $1
*** HOLE CARDS ***
Dealt to Hero [Ah Kh]
Villain5: folds
Hero: raises $2.50 to $3.50
Villain1: folds
Villain2: folds
Villain3: folds
Villain4: calls $2.50
*** FLOP *** [Qd 8c 2s]
Villain4: checks
Hero: ?
"""

def test_poker_analyze():
    """Тест анализа покера через Hand History API"""
    print("=" * 60)
    print("🎴 ТЕСТ АНАЛИЗА ЧЕРЕЗ HAND HISTORY")
    print("=" * 60)
    
    try:
        # Отправляем запрос к API
        response = requests.post(
            f"{API_URL}/analyze/poker",
            json={"hand_history_text": hand_history_text},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ АНАЛИЗ УСПЕШЕН!\n")
            
            # Решение
            decision = result.get('decision', {})
            print("🎯 РЕКОМЕНДАЦИЯ:")
            print(f"   Действие: {decision.get('action', 'N/A')}")
            print(f"   Сайзинг: {decision.get('sizing', 'N/A')}")
            print(f"   Уверенность: {decision.get('confidence', 0):.0%}")
            
            # Объяснение
            explanation = result.get('explanation', '')
            if explanation:
                print(f"\n📝 ОБЪЯСНЕНИЕ:")
                print(f"   {explanation[:300]}...")
            
            # Ключевые факты
            key_facts = decision.get('key_facts', {})
            if key_facts:
                print(f"\n📊 КЛЮЧЕВЫЕ ФАКТЫ:")
                for key, value in key_facts.items():
                    if isinstance(value, dict):
                        print(f"   {key}:")
                        for k, v in value.items():
                            print(f"      {k}: {v}")
                    else:
                        print(f"   {key}: {value}")
            
            print("\n" + "=" * 60)
            print("✅ ТЕСТ ЗАВЕРШЕН")
            print("=" * 60)
            
        else:
            print(f"\n❌ ОШИБКА API: {response.status_code}")
            print(f"   {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ОШИБКА: Не удается подключиться к API")
        print("\n💡 Запустите API командой:")
        print("   uvicorn coach_app.api.main:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")


if __name__ == '__main__':
    test_poker_analyze()
