#!/usr/bin/env python3
"""
Telegram-бот для дистанционного включения ПК через Wake-on-LAN
Работает через интернет на внешний IP роутера
"""
import os
import socket
import logging
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# Загрузка переменных из .env файла
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# Настройки
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '9010016453:AAHqb5qDclXGWSJjGzygZvQ0wPDvByLckZM')
ALLOWED_USER_IDS = [int(uid) for uid in os.environ.get('ALLOWED_USER_IDS', '').split(',') if uid]

# MAC-адрес компьютера
TARGET_MAC = os.environ.get('TARGET_MAC', 'D8:43:AE:69:6C:01')

# Внешний IP роутера для WOL через интернет
ROUTER_IP = os.environ.get('ROUTER_IP', '80.234.76.238')
WOL_PORT = int(os.environ.get('WOL_PORT', '9'))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_magic_packet(mac_address: str) -> bytes:
    """Создаёт магический пакет для Wake-on-LAN"""
    mac_address = mac_address.replace(':', '').replace('-', '')

    if len(mac_address) != 12:
        raise ValueError(f"Неверный MAC-адрес: {mac_address}")

    mac_bytes = bytes.fromhex(mac_address)
    magic_packet = b'\xFF' * 6 + mac_bytes * 16

    return magic_packet


def send_wol_packet(mac_address: str, router_ip: str, port: int = 9) -> bool:
    """Отправляет WoL пакет на роутер через интернет"""
    try:
        magic_packet = create_magic_packet(mac_address)

        # Создаём UDP сокет
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Отправляем магический пакет на внешний IP роутера
        sock.sendto(magic_packet, (router_ip, port))
        sock.close()

        logger.info(f"WoL пакет отправлен на {mac_address} через {router_ip}:{port}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки WoL пакета: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id

    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return

    keyboard = [[KeyboardButton("💻 Включить компьютер")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        "Этот бот включает твой компьютер через Wake-on-LAN.\n\n"
        "Нажми кнопку ниже, когда будешь готов включить ПК.",
        reply_markup=reply_markup
    )


async def handle_wol_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопки включения"""
    user_id = update.effective_user.id

    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return

    await update.message.reply_text("⏳ Отправляю команду включения...")

    success = send_wol_packet(TARGET_MAC, ROUTER_IP, WOL_PORT)

    if success:
        await update.message.reply_text(
            "✅ Команда отправлена!\n\n"
            "Компьютер должен включиться в течение нескольких секунд.\n"
            f"WOL пакет отправлен на {ROUTER_IP}:{WOL_PORT}"
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка отправки команды.\n\n"
            "Проверь логи бота и настройки сети."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")


def main():
    """Основная функция запуска бота"""
    if TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ Ошибка: не установлен токен бота!")
        print("Установи переменную окружения TELEGRAM_BOT_TOKEN")
        return

    logger.info("Запуск Telegram-бота для Wake-on-LAN через интернет...")
    logger.info(f"MAC-адрес: {TARGET_MAC}")
    logger.info(f"IP роутера: {ROUTER_IP}")
    logger.info(f"Порт WoL: {WOL_PORT}")

    # Создаём приложение с увеличенными таймаутами
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )
    application = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("💻 Включить компьютер"), handle_wol_button))
    application.add_error_handler(error_handler)

    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
