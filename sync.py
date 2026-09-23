import os
import json
import re
import requests
from datetime import datetime

VK_TOKEN = os.environ.get("VK_TOKEN")
PEER_ID = -218837624
SEPT_1_2026_UNIX = 1788220800
DATA_FILE = "data.json"

def main():
    if not VK_TOKEN:
        print("Ошибка: Токен VK_TOKEN не найден в секретах!")
        return

    # Читаем старые транзакции, чтобы не было дублей
    existing_txs = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                existing_txs = json.load(f)
        except:
            pass

    # Создаем словарь для быстрого поиска дубликатов
    seen = {f"{tx['amount']}_{tx['merchant']}_{tx['ts']}": True for tx in existing_txs}

    print("Подключение к API ВКонтакте...")
    url = "https://api.vk.com/method/messages.getHistory"
    params = {
        "peer_id": PEER_ID,
        "count": 200,
        "access_token": VK_TOKEN,
        "v": "5.199"
    }
    
    resp = requests.get(url, params=params).json()
    if "error" in resp:
        print(f"Ошибка ВК: {resp['error']}")
        return

    items = resp.get("response", {}).get("items", [])
    if not items:
        print("Нет сообщений в диалоге.")
        return

    category_map = {
        'Супермаркеты': ['пятерочка', 'магнит', 'перекресток', 'ашан', 'лента', 'спар', 'вкусвилл', 'миндаль', 'пеликан', 'витаград'],
        'Фастфуд': ['вкусно', 'burger king', 'kfc', 'бургер', 'додо', 'пицца', 'шаурма', 'ростикс'],
        'Игры и Софт': ['lis-skins', 'majestic', 'steam', 'epic games', 'playstation', 'vk play'],
        'Подписки': ['vk music', 'yandex', 'яндекс', 'подписка', 'pure', 'twinby', 'mamba', 'telegram', 'премиум'],
        'Развлечения': ['mori cinema', 'кино', 'royal forest', 'парк', 'билет', 'афиша'],
        'Транспорт': ['яндекс.такси', 'такси', 'метро', 'ржд', 'авиа', 'автобус'],
        'Маркетплейсы': ['ozon', 'wildberries', 'aliexpress', 'мегамаркет'],
        'Переводы': ['перевод', 'пополнение', 'sbp', 'сбп']
    }

    new_txs = []
    for msg in items:
        ts = msg.get("date", 0)
        if ts < SEPT_1_2026_UNIX:
            continue
        
        text = msg.get("text", "").replace("\n", " ")
        if not text:
            continue
            
        match = re.search(r'Покупка\s*([\d\s]+(?:[.,]\d+)?)\s*[₽р]\s*,\s*([^.]+)', text, re.IGNORECASE)
        if not match:
            match = re.search(r'(?:Покупка|Оплата)\s*([\d\s]+(?:[.,]\d+)?)\s*[₽р][^A-Za-zА-Яа-я]*([A-Za-zА-Яа-я0-9\s-]+)', text, re.IGNORECASE)
        
        if match:
            amount = float(match.group(1).replace(" ", "").replace(",", "."))
            merchant = match.group(2).strip()
            
            cat = "Другое"
            lower_merch = merchant.lower()
            for c_name, keywords in category_map.items():
                if any(kw in lower_merch for kw in keywords):
                    cat = c_name
                    break
            
            dt = datetime.fromtimestamp(ts)
            date_str = dt.strftime("%d.%m.%Y %H:%M")
            tx_hash = f"{amount}_{merchant}_{ts}"
            
            if tx_hash not in seen:
                new_txs.append({
                    "id": tx_hash,
                    "amount": amount,
                    "merchant": merchant,
                    "category": cat,
                    "date": date_str,
                    "ts": ts
                })
                seen[tx_hash] = True

    all_txs = existing_txs + new_txs
    all_txs.sort(key=lambda x: x["ts"], reverse=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_txs, f, ensure_ascii=False, indent=2)
        
    print(f"Добавлено новых чеков: {len(new_txs)}. Всего чеков в базе: {len(all_txs)}")

if __name__ == "__main__":
    main()
