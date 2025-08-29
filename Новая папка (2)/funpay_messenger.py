#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💬 Автоматический мессенджер для FunPay
Отправка сообщений, инструкций по Steam Guard, бонусная система
"""

import time
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

class FunPayMessenger:
    """Автоматический мессенджер для FunPay"""
    
    def __init__(self, headless: bool = False):
        self.driver = None
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        self.message_templates = self._load_message_templates()
        self.setup_driver()
    
    def setup_driver(self):
        """Настройка Chrome драйвера"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Отключаем изображения для ускорения
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.logger.info("Chrome драйвер успешно настроен")
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки Chrome драйвера: {e}")
            raise
    
    def create_rental_listing(self, game_name: str, price_per_hour: float, account_id: str = None):
        """
        Автоматически создает объявление на FunPay для аренды аккаунта
        """
        try:
            if not self.driver:
                self.logger.error("Драйвер не инициализирован")
                return None
            
            # Переходим на страницу создания объявления
            self.driver.get("https://funpay.com/account/sells/add")
            time.sleep(3)
            
            # Выбираем категорию "Аккаунты"
            category_dropdown = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='category-select']"))
            )
            category_dropdown.click()
            time.sleep(1)
            
            # Выбираем "Steam"
            steam_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Steam')]"))
            )
            steam_option.click()
            time.sleep(1)
            
            # Заполняем название
            title_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='title-input']"))
            )
            title_input.clear()
            title_input.send_keys(f"Аренда Steam аккаунта | {game_name} | Почасовая оплата")
            
            # Заполняем описание
            description_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='description-input']")
            description_input.clear()
            
            # Шаблонный текст объявления
            listing_text = self._get_listing_template(game_name, price_per_hour)
            description_input.send_keys(listing_text)
            
            # Устанавливаем цену
            price_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='price-input']")
            price_input.clear()
            price_input.send_keys(str(price_per_hour))
            
            # Выбираем валюту (рубли)
            currency_dropdown = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='currency-select']")
            currency_dropdown.click()
            time.sleep(1)
            
            rub_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), '₽')]"))
            )
            rub_option.click()
            
            # Устанавливаем время доставки
            delivery_input = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='delivery-time-input']")
            delivery_input.clear()
            delivery_input.send_keys("1")
            
            # Выбираем единицу времени (минуты)
            delivery_unit = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='delivery-unit-select']")
            delivery_unit.click()
            time.sleep(1)
            
            minutes_option = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'минут')]"))
            )
            minutes_option.click()
            
            # Нажимаем "Создать"
            create_button = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='create-button']")
            create_button.click()
            
            # Ждем подтверждения
            time.sleep(5)
            
            # Получаем ID созданного объявления
            listing_url = self.driver.current_url
            listing_id = listing_url.split('/')[-1]
            
            self.logger.info(f"Создано объявление для игры {game_name} с ID: {listing_id}")
            return listing_id
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании объявления для {game_name}: {e}")
            return None
    
    def _get_listing_template(self, game_name, price_per_hour):
        """
        Возвращает шаблонный текст для объявления
        """
        template = f"""🎮 **Аренда Steam аккаунта | {game_name}**

✅ **Что вы получаете:**
• Полный доступ к Steam аккаунту
• Игра {game_name} уже установлена
• Возможность играть в любое время
• Мгновенная доставка после оплаты

💰 **Стоимость:** {price_per_hour}₽/час

⏰ **Как работает аренда:**
1. Оплачиваете нужное количество часов
2. Получаете данные для входа мгновенно
3. Играете в течение оплаченного времени
4. По истечении времени доступ автоматически закрывается

🔐 **Безопасность:**
• Аккаунт проверен и работает стабильно
• Пароль меняется после каждой аренды
• Гарантия возврата средств при проблемах

📱 **Поддержка:**
• Telegram бот для управления арендой
• Проверка оставшегося времени
• Техническая поддержка 24/7

🎁 **Бонус за отзыв:**
• Оставьте отзыв на FunPay
• Получите +30 минут бонусного времени
• Бонус применяется к текущей аренде

⚠️ **Важно:**
• Не меняйте пароль от аккаунта
• Не добавляйте друзей
• Не используйте читы
• Соблюдайте правила Steam

🚀 **Начните играть прямо сейчас!**
Оплачивайте и получайте доступ к {game_name} в течение 1 минуты!"""
        
        return template

    def _load_message_templates(self) -> Dict[str, str]:
        """Загрузка шаблонов сообщений"""
        return {
            "steam_guard_instructions": """Здравствуйте! Я бот-помощник Steam Rental System.

🎮 Ваш аккаунт Steam готов к использованию!

📱 **Steam Guard Mobile App:**
1. Скачайте приложение Steam Guard в App Store или Google Play
2. Войдите в аккаунт Steam
3. В настройках включите Steam Guard Mobile
4. При входе в Steam введите код из приложения

💻 **Steam Guard для ПК:**
1. Откройте Steam
2. Перейдите в Настройки → Безопасность
3. Включите Steam Guard
4. Следуйте инструкциям по настройке

🔑 **Данные для входа:**
Логин: {login}
Пароль: {password}
Email: {email}

⏰ **Время аренды:** {rental_time}

❓ **Нужна помощь?** Напишите в поддержку или используйте команду /support

⭐ **Оставьте отзыв и получите +30 минут бонусного времени!**
Команда для получения бонуса: /bonus

Удачной игры! 🎯""",
            
            "welcome_message": """Здравствуйте! Добро пожаловать в Steam Rental System! 🎮

Я автоматический бот-помощник, который поможет вам:
✅ Получить доступ к Steam аккаунту
✅ Настроить Steam Guard
✅ Получить бонусное время за отзыв
✅ Решить любые вопросы

📱 **Основные команды:**
/start - Главное меню
/help - Справка
/time - Оставшееся время
/accounts - Доступные аккаунты
/support - Поддержка
/bonus - Получить бонус за отзыв

🚀 Готовы начать? Выберите игру и время аренды!""",
            
            "rental_confirmation": """✅ **Аренда подтверждена!**

🎮 Игра: {game}
⏰ Время: {rental_time}
💰 Стоимость: {price} ₽

📱 **Следующий шаг:**
1. Скачайте Steam Guard Mobile
2. Войдите в аккаунт
3. Получите данные для входа

💬 Напишите "готов" когда будете готовы получить данные аккаунта.

⭐ **Не забудьте оставить отзыв для получения +30 минут бонуса!**""",
            
            "steam_guard_ready": """🎯 **Steam Guard готов!**

📱 **Данные аккаунта:**
Логин: {login}
Пароль: {password}
Email: {email}

🔐 **Steam Guard код:**
{steam_guard_code}

⚠️ **Важно:**
• Не передавайте код третьим лицам
• Код действителен 30 секунд
• При проблемах используйте резервные коды

🎮 **Время аренды:** {rental_time}

❓ **Нужна помощь?** Команда /support

⭐ **Оставьте отзыв для бонуса +30 минут!** Команда /bonus""",
            
            "rental_expired": """⏰ **Время аренды истекло!**

🎮 Игра: {game}
📅 Дата окончания: {end_date}

🔒 **Аккаунт заблокирован для изменения пароля**

💡 **Хотите продлить аренду?**
• Используйте команду /extend
• Или арендуйте новый аккаунт

⭐ **Оставьте отзыв о сервисе для получения скидки на следующую аренду!**

Спасибо за использование Steam Rental System! 🎯""",
            
            "bonus_reminder": """🎁 **Напоминание о бонусе!**

⭐ **Оставьте отзыв и получите +30 минут бонусного времени!**

📝 **Как получить бонус:**
1. Напишите команду /review
2. Оцените сервис от 1 до 5 звезд
3. Напишите комментарий
4. Получите +30 минут на следующий аккаунт!

🎯 **Бонус можно использовать:**
• При следующей аренде
• Для продления текущей аренды
• Накопить для VIP аккаунта

💬 Команда: /bonus""",
            
            "support_message": """🆘 **Поддержка Steam Rental System**

📞 **Способы связи:**
• Telegram: @steam_rental_support
• Email: support@steamrental.com
• Чат: /chat

🔧 **Частые проблемы:**
• Steam Guard не работает → /steamguard_help
• Не могу войти → /login_help
• Проблемы с оплатой → /payment_help
• Технические вопросы → /tech_help

⏰ **Время ответа:** до 5 минут

💡 **Пока ждете ответа:**
• Проверьте FAQ: /faq
• Посмотрите видео-инструкции: /tutorials
• Изучите базу знаний: /knowledge

🎯 **Номер обращения:** #{ticket_id}""",
            
            "review_request": """⭐ **Пожалуйста, оставьте отзыв!**

🎮 **Ваша аренда завершена:**
Игра: {game}
Время: {rental_time}
Дата: {date}

📝 **Оцените наш сервис:**
1 ⭐ - Плохо
2 ⭐ - Неудовлетворительно  
3 ⭐ - Удовлетворительно
4 ⭐ - Хорошо
5 ⭐ - Отлично!

🎁 **За отзыв получите:**
• +30 минут бонусного времени
• Скидку 10% на следующую аренду
• Приоритетную поддержку

💬 **Команда для отзыва:** /review

Спасибо за доверие! 🙏""",
            
            "bonus_activated": """🎉 **Бонус активирован!**

⭐ **Ваш отзыв принят!**

🎁 **Получено:**
• +30 минут бонусного времени
• Скидка 10% на следующую аренду
• Статус "Постоянный клиент"

💳 **Бонусное время:** {bonus_time}

📱 **Использовать бонус:**
• При аренде: /rent
• Для продления: /extend
• Обмен на скидку: /exchange

🎯 **Следующая аренда со скидкой!**

Спасибо за отзыв! 🙏""",
            
            "maintenance_notice": """🔧 **Техническое обслуживание**

⚠️ **Внимание!** Система временно недоступна.

🕐 **Время:** {maintenance_time}
📋 **Работы:** {maintenance_type}

💡 **Что происходит:**
• Обновление безопасности
• Улучшение производительности
• Добавление новых функций

📱 **Уведомления:**
• О завершении работ
• О компенсации времени
• О специальных предложениях

⏰ **Ожидаемое время:** {estimated_duration}

🎯 **Следите за обновлениями!**"""
        }
    
    def login_to_funpay(self, username: str, password: str) -> bool:
        """Вход в FunPay"""
        try:
            self.logger.info("Вход в FunPay...")
            
            # Открываем страницу входа
            self.driver.get("https://funpay.com/account/login")
            time.sleep(3)
            
            # Ждем появления формы входа
            wait = WebDriverWait(self.driver, 10)
            
            # Вводим логин
            login_field = wait.until(EC.presence_of_element_located((By.NAME, "login")))
            login_field.clear()
            login_field.send_keys(username)
            
            # Вводим пароль
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)
            
            # Нажимаем кнопку входа
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Ждем входа
            time.sleep(5)
            
            # Проверяем успешность входа
            if "account" in self.driver.current_url or "profile" in self.driver.current_url:
                self.logger.info("Успешный вход в FunPay")
                return True
            else:
                self.logger.error("Не удалось войти в FunPay")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка входа в FunPay: {e}")
            return False
    
    def send_message_to_order(self, order_id: str, message: str) -> bool:
        """Отправка сообщения к заказу"""
        try:
            self.logger.info(f"Отправка сообщения к заказу {order_id}")
            
            # Переходим к заказу
            order_url = f"https://funpay.com/orders/{order_id}"
            self.driver.get(order_url)
            time.sleep(3)
            
            # Ищем поле для сообщения
            wait = WebDriverWait(self.driver, 10)
            message_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder*='сообщение']")))
            
            # Очищаем поле и вводим сообщение
            message_field.clear()
            message_field.send_keys(message)
            
            # Нажимаем кнопку отправки
            send_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            send_button.click()
            
            time.sleep(2)
            self.logger.info(f"Сообщение к заказу {order_id} отправлено")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения к заказу {order_id}: {e}")
            return False
    
    def send_steam_guard_instructions(self, order_id: str, account_data: Dict, rental_time: str) -> bool:
        """Отправка инструкций по Steam Guard"""
        try:
            message = self.message_templates["steam_guard_instructions"].format(
                login=account_data['login'],
                password=account_data['password'],
                email=account_data.get('email', 'Не указан'),
                rental_time=rental_time
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки инструкций Steam Guard: {e}")
            return False
    
    def send_welcome_message(self, order_id: str) -> bool:
        """Отправка приветственного сообщения"""
        try:
            message = self.message_templates["welcome_message"]
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки приветственного сообщения: {e}")
            return False
    
    def send_rental_confirmation(self, order_id: str, game: str, rental_time: str, price: float) -> bool:
        """Отправка подтверждения аренды"""
        try:
            message = self.message_templates["rental_confirmation"].format(
                game=game,
                rental_time=rental_time,
                price=price
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки подтверждения аренды: {e}")
            return False
    
    def send_steam_guard_ready(self, order_id: str, account_data: Dict, steam_guard_code: str, rental_time: str) -> bool:
        """Отправка готовности Steam Guard"""
        try:
            message = self.message_templates["steam_guard_ready"].format(
                login=account_data['login'],
                password=account_data['password'],
                email=account_data.get('email', 'Не указан'),
                steam_guard_code=steam_guard_code,
                rental_time=rental_time
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки готовности Steam Guard: {e}")
            return False
    
    def send_rental_expired(self, order_id: str, game: str, end_date: str) -> bool:
        """Отправка уведомления об истечении аренды"""
        try:
            message = self.message_templates["rental_expired"].format(
                game=game,
                end_date=end_date
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления об истечении аренды: {e}")
            return False
    
    def send_bonus_reminder(self, order_id: str) -> bool:
        """Отправка напоминания о бонусе"""
        try:
            message = self.message_templates["bonus_reminder"]
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки напоминания о бонусе: {e}")
            return False
    
    def send_support_message(self, order_id: str, ticket_id: str) -> bool:
        """Отправка сообщения поддержки"""
        try:
            message = self.message_templates["support_message"].format(
                ticket_id=ticket_id
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения поддержки: {e}")
            return False
    
    def send_review_request(self, order_id: str, game: str, rental_time: str, date: str) -> bool:
        """Отправка запроса на отзыв"""
        try:
            message = self.message_templates["review_request"].format(
                game=game,
                rental_time=rental_time,
                date=date
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки запроса на отзыв: {e}")
            return False
    
    def send_bonus_activated(self, order_id: str, bonus_time: str) -> bool:
        """Отправка уведомления об активации бонуса"""
        try:
            message = self.message_templates["bonus_activated"].format(
                bonus_time=bonus_time
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления об активации бонуса: {e}")
            return False
    
    def send_maintenance_notice(self, order_id: str, maintenance_time: str, 
                               maintenance_type: str, estimated_duration: str) -> bool:
        """Отправка уведомления о техническом обслуживании"""
        try:
            message = self.message_templates["maintenance_notice"].format(
                maintenance_time=maintenance_time,
                maintenance_type=maintenance_type,
                estimated_duration=estimated_duration
            )
            
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления о техобслуживании: {e}")
            return False
    
    def send_custom_message(self, order_id: str, message: str) -> bool:
        """Отправка пользовательского сообщения"""
        try:
            return self.send_message_to_order(order_id, message)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки пользовательского сообщения: {e}")
            return False
    
    def send_bulk_messages(self, order_ids: List[str], message_template: str, 
                          **kwargs) -> Dict[str, bool]:
        """Массовая отправка сообщений"""
        results = {}
        
        for order_id in order_ids:
            try:
                # Форматируем сообщение
                if kwargs:
                    message = message_template.format(**kwargs)
                else:
                    message = message_template
                
                # Отправляем сообщение
                success = self.send_message_to_order(order_id, message)
                results[order_id] = success
                
                # Пауза между отправками
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                self.logger.error(f"Ошибка массовой отправки к заказу {order_id}: {e}")
                results[order_id] = False
        
        return results
    
    def check_unread_messages(self) -> List[Dict]:
        """Проверка непрочитанных сообщений"""
        try:
            unread_messages = []
            
            # Переходим в раздел сообщений
            self.driver.get("https://funpay.com/chat")
            time.sleep(3)
            
            # Ищем непрочитанные сообщения
            unread_elements = self.driver.find_elements(By.CSS_SELECTOR, ".chat-item.unread")
            
            for element in unread_elements:
                try:
                    # Извлекаем информацию о сообщении
                    sender = element.find_element(By.CSS_SELECTOR, ".chat-item__name").text
                    preview = element.find_element(By.CSS_SELECTOR, ".chat-item__message").text
                    time_element = element.find_element(By.CSS_SELECTOR, ".chat-item__time").text
                    
                    unread_messages.append({
                        'sender': sender,
                        'preview': preview,
                        'time': time_element,
                        'element': element
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Не удалось извлечь информацию о сообщении: {e}")
                    continue
            
            return unread_messages
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки непрочитанных сообщений: {e}")
            return []
    
    def auto_reply_to_messages(self, auto_replies: Dict[str, str]) -> Dict[str, bool]:
        """Автоматические ответы на сообщения"""
        results = {}
        
        try:
            unread_messages = self.check_unread_messages()
            
            for message in unread_messages:
                sender = message['sender']
                preview = message['preview'].lower()
                
                # Ищем подходящий автоматический ответ
                for trigger, reply in auto_replies.items():
                    if trigger.lower() in preview:
                        try:
                            # Открываем чат с отправителем
                            message['element'].click()
                            time.sleep(2)
                            
                            # Отправляем ответ
                            message_field = self.driver.find_element(By.CSS_SELECTOR, "textarea[placeholder*='сообщение']")
                            message_field.clear()
                            message_field.send_keys(reply)
                            
                            send_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                            send_button.click()
                            
                            results[sender] = True
                            time.sleep(2)
                            
                        except Exception as e:
                            self.logger.error(f"Ошибка автоматического ответа {sender}: {e}")
                            results[sender] = False
                        
                        break
                
                # Если не нашли подходящий ответ
                if sender not in results:
                    results[sender] = False
            
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка автоматических ответов: {e}")
            return {}
    
    def close(self):
        """Закрытие браузера"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("Браузер закрыт")
        except Exception as e:
            self.logger.error(f"Ошибка закрытия браузера: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
