#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 Steam Rental System - Простая версия для Railway
"""

import os
import logging
import threading
import time
from flask import Flask, jsonify

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
    return jsonify({
        "status": "running",
        "message": "Steam Rental System готов к работе"
    })

def start_bot():
    """Запуск Telegram бота в отдельном потоке"""
    global bot
    try:
        # Импортируем здесь, чтобы избежать ошибок при деплое
        from telegram_bot import SteamRentalBot
        bot = SteamRentalBot()
        bot.setup()
        logger.info("Telegram бот запущен")
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        # Не останавливаем приложение при ошибке бота

def start_system():
    """Запуск основной системы в отдельном потоке"""
    global system
    try:
        # Импортируем здесь, чтобы избежать ошибок при деплое
        from steam_rental_system import SteamRentalSystem
        system = SteamRentalSystem()
        logger.info("Основная система запущена")
        system.start()
    except Exception as e:
        logger.error(f"Ошибка запуска системы: {e}")
        # Не останавливаем приложение при ошибке системы

if __name__ == '__main__':
    logger.info("🚀 Запуск Steam Rental System...")
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем основную систему в отдельном потоке
    system_thread = threading.Thread(target=start_system, daemon=True)
    system_thread.start()
    
    # Ждем немного для инициализации
    time.sleep(3)
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запуск веб-сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
