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
    existing_txs = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                existing_txs = json.load(f)
        except Exception as e:
            print(f"Ошибка чтения старых данных: {e}")

    if not VK_TOKEN:
        print("Внимание: VK_TOKEN отсутствует!")
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        return

    seen = {f"{tx.get('amount')}_{tx.get('merchant')}_{tx.get('ts')}": True for tx in existing_txs}

    print("Запрос сообщений из ВК...")
    url = "https://api.vk.com/method/messages.getHistory"
    params = {
        "peer_id": PEER_ID,
        "count": 200,
        "access_token": VK_TOKEN,
        "v": "5.199"
    }

    try:
        resp = requests.get(url, params=params, timeout=15).json()
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return

    if "error" in resp:
        print(f"Ответ с ошибкой от ВК: {resp['error']}")
        # Создаем файл если нет, чтобы Action не падал
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_txs, f)
        return

    items = resp.get("response", {}).get("items", [])
    print(f"Получено сообщений: {len(items)}")

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
            try:
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
            except Exception as e:
                print(f"Ошибка парсинга строки: {e}")

    all_txs = new_txs + existing_txs
    all_txs.sort(key=lambda x: x.get("ts", 0), reverse=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_txs, f, ensure_ascii=False, indent=2)

    print(f"Готово! Новых: {len(new_txs)}. Всего: {len(all_txs)}")

if __name__ == "__main__":
    main()
