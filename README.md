# Muhim Bot — Telegram Stars Gift Bot

Telegram Stars ishlash va gift yuborish boti (pyTelegramBotAPI + SQLite3).

## Funksiyalar
- Reply-kengaytirilgan menyu (premium custom emoji ikonlar)
- XTR invoуs orqali Stars to'ldirish (`send_invoice`)
- Avtomatik gift yechish (`send_gift`)
- Referal tizimi
- Majburiy obuna tekshiruvi
- Admin panel (`/akam admin123`): shartlar, gift, referal, obuna kanal, reklama, statistika, bot balansini to'ldirish

## Ishga tushirish
```
pip install pyTelegramBotAPI
python bot.py
```
Tokenni `BOT_TOKEN.txt` (yoki `BOT_TOKEN` env) orqali berish mumkin.
Render (web service): `PORT` env avtomatik keepalive HTTP serverni ishga tushiradi.