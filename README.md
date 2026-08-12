# TG Name Changer

Автоматическая смена отображаемого имени в Telegram по таймеру. Работает в трее, всё локально.

## Установка

Python 3.10+.

git clone https://github.com/DungeonMaster/tg-name-changer.git

cd tg-name-changer

python -m venv venv

Windows:

venv\Scripts\activate

pip install -r requirements.txt

Linux/Mac:

source venv/bin/activate

pip install -r requirements.txt

API-ключи: зайди на my.telegram.org → API development tools → заполни форму (Short name — только строчные латинские без спецсимволов, Platform — Desktop). Скопируй api_id и api_hash.

Запуск:

Windows без консоли:
venv\Scripts\pythonw.exe main.py

Все платформы:
python main.py

## Первый запуск

Впиши ключи и телефон → «Отправить код» → код придёт в чат «Telegram» внутри самого Telegram (не SMS) → введи код → если 2FA, введи пароль. Готово.

## Управление

Интервал 4ч–3д, разброс ±0–120мин, список имён. Кнопки: «Сменить сейчас», «Старт/Пауза», «Вернуть» (оригинальное имя). Двойной клик по трею — открыть окно. Крестик сворачивает в трей, не закрывает.

## Troubleshooting

ERROR на my.telegram.org: VPN должен быть страны номера (или выключен), Short name без подчёркиваний, попробуй инкогнито без расширений, при лимите попыток подожди 15–20 мин. Код не приходит: он в чате «Telegram» не по SMS, не жми кнопку много раз. database is locked: закрой другие копии приложения.

## Безопасность

Всё локально, ничего не уходит на серверы.

MIT. Только для личного использования.
