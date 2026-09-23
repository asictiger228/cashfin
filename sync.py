import os
import json
import re
import time
import requests
from datetime import datetime

VK_TOKEN = os.environ.get("VK_TOKEN")
PEER_ID = -218837624

# Сентябрь 2026 года
SEPT_1_2026_UNIX = int(datetime(2026, 9, 1, 0, 0, 0).timestamp())
DATA_FILE = "data.json"

def main():
    print("=== ЗАПУСК ОБХОДА FLOOD CONTROL ===")

    existing_txs = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                existing_txs = json.load(f)
        except Exception:
            pass

    if not VK_TOKEN:
        print("ОШИБКА: VK_TOKEN отсутствует!")
        return

    seen = {f"{tx.get('amount')}_{tx.get('merchant')}_{tx.get('ts')}": True for tx in existing_txs}

    # Маскируемся под мобильный клиент VK для Android
    headers = {
        "User-Agent": "VKAndroidApp/8.56-17482 (Android 14; SDK 34; arm64-v8a; samsung SM-S928B; ru; 3120x1440)",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Connection": "keep-alive"
    }

    url = "https://api.vk.com/method/messages.getHistory"
    
    # Запрашиваем 60 сообщений вместо 200, чтобы не триггерить лимиты
    params = {
        "peer_id": PEER_ID,
        "count": 60,
        "access_token": VK_TOKEN,
        "v": "5.199"
    }

    time.sleep(1) # Небольшая пауза перед запросом

    try:
        session = requests.Session()
        resp = session.get(url, params=params, headers=headers, timeout=20).json()
    except Exception as e:
        print(f"Ошибка сети: {e}")
        return

    if "error" in resp:
        err = resp["error"]
        print(f"Ошибка ВК: {err.get('error_code')} - {err.get('error_msg')}")
        if err.get("error_code") == 9:
            print("ВК временно держит flood limit. Если ошибка повторяется, пересоздайте токен через Kate Mobile на vkhost.")
        return

    items = resp.get("response", {}).get("items", [])
    print(f"Успех! Получено сообщений: {len(items)}")

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

        raw_text = msg.get("text", "")
        text = raw_text.replace("\n", " ")

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
                    print(f"[+] ЧЕК: {amount} руб | {merchant} | {date_str}")
            except Exception as e:
                print(f"Ошибка парсинга: {e}")

    all_txs = new_txs + existing_txs
    all_txs.sort(key=lambda x: x.get("ts", 0), reverse=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_txs, f, ensure_ascii=False, indent=2)

    print(f"=== ЗАВЕРШЕНО. Найдено: {len(new_txs)}, всего в базе: {len(all_txs)} ===")

if __name__ == "__main__":
    main()
