#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 Steam Rental System - Главный файл для Railway
Включает веб-сервер и Telegram бота
"""

import os
import logging
import threading
from flask import Flask, jsonify
from telegram_bot import SteamRentalBot
from steam_rental_system import SteamRentalSystem

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение для Railway
app = Flask(__name__)

# Глобальные переменные для бота и системы
bot = None
system = None

@app.route('/')
def home():
    """Главная страница"""
    return jsonify({
        "status": "running",
        "service": "Steam Rental System",
        "bot": "active" if bot else "inactive",
        "system": "active" if system else "inactive"
    })

@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    return jsonify({
        "status": "healthy",
        "bot_running": bot is not None,
        "system_running": system is not None
    })

@app.route('/status')
def status():
    """Статус системы"""
    if system:
        return jsonify({
            "status": "running",
            "accounts_count": len(system.db.get_all_accounts()),
            "active_rentals": len(system.db.get_active_rentals()),
            "users_count": len(system.db.get_all_users())
        })
    return jsonify({"status": "not_initialized"})

def start_bot():
    """Запуск Telegram бота в отдельном потоке"""
    global bot
    try:
        bot = SteamRentalBot()
        bot.setup()
        logger.info("Telegram бот запущен")
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

def start_system():
    """Запуск основной системы в отдельном потоке"""
    global system
    try:
        system = SteamRentalSystem()
        logger.info("Основная система запущена")
        system.start()
    except Exception as e:
        logger.error(f"Ошибка запуска системы: {e}")

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем основную систему в отдельном потоке
    system_thread = threading.Thread(target=start_system, daemon=True)
    system_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запуск веб-сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
