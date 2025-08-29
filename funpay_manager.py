import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from config import Config

class FunPayManager:
    def __init__(self):
        self.base_url = Config.FUNPAY_BASE_URL
        self.login = Config.FUNPAY_LOGIN
        self.password = Config.FUNPAY_PASSWORD
        self.driver = None
        self.session = requests.Session()
        self.is_logged_in = False
    
    def setup_driver(self):
        """Настройка веб-драйвера Chrome"""
        try:
            chrome_options = Options()
            if Config.BROWSER_HEADLESS:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(Config.BROWSER_TIMEOUT)
            return True
            
        except Exception as e:
            print(f"Ошибка при настройке драйвера: {e}")
            return False
    
    def login_to_funpay(self):
        """Вход в аккаунт FunPay"""
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False
            
            # Переходим на страницу входа
            self.driver.get(f"{self.base_url}/account/login")
            time.sleep(2)
            
            # Вводим логин
            login_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "login"))
            )
            login_field.clear()
            login_field.send_keys(self.login)
            
            # Вводим пароль
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Нажимаем кнопку входа
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Ждем успешного входа
            time.sleep(5)
            
            # Проверяем, что мы вошли
            if "account" in self.driver.current_url or "profile" in self.driver.current_url:
                self.is_logged_in = True
                print("Успешный вход в FunPay")
                return True
            else:
                print("Не удалось войти в FunPay")
                return False
                
        except Exception as e:
            print(f"Ошибка при входе в FunPay: {e}")
            return False
    
    def create_rental_listing(self, game_name: str, price_per_hour: float, account_id: str = None):
        """
        Автоматически создает объявление на FunPay для аренды аккаунта
        """
        try:
            if not self.is_logged_in:
                if not self.login_to_funpay():
                    return None
            
            # Переходим на страницу создания объявления
            self.driver.get(f"{self.base_url}/account/sells/add")
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
            
            print(f"Создано объявление для игры {game_name} с ID: {listing_id}")
            return listing_id
            
        except Exception as e:
            print(f"Ошибка при создании объявления для {game_name}: {e}")
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

    def check_new_orders(self):
        """Проверка новых заказов"""
        try:
            if not self.is_logged_in:
                if not self.login_to_funpay():
                    return []
            
            # Переходим на страницу заказов
            self.driver.get(f"{self.base_url}/account/orders")
            time.sleep(3)
            
            # Получаем список заказов
            orders = []
            order_elements = self.driver.find_elements(By.CSS_SELECTOR, ".order-item")
            
            for element in order_elements:
                try:
                    order_id = element.get_attribute("data-order-id")
                    status = element.find_element(By.CSS_SELECTOR, ".status").text
                    game_name = element.find_element(By.CSS_SELECTOR, ".game-name").text
                    duration = element.find_element(By.CSS_SELECTOR, ".duration").text
                    
                    if status == "Ожидает выполнения":
                        orders.append({
                            'id': order_id,
                            'game_name': game_name,
                            'duration': duration,
                            'status': status
                        })
                        
                except Exception as e:
                    print(f"Ошибка при парсинге заказа: {e}")
                    continue
            
            return orders
            
        except Exception as e:
            print(f"Ошибка при проверке заказов: {e}")
            return []
    
    def process_order(self, order_id: str, account_data: dict):
        """Обработка заказа - отправка данных аккаунта"""
        try:
            if not self.is_logged_in:
                if not self.login_to_funpay():
                    return False
            
            # Переходим к заказу
            self.driver.get(f"{self.base_url}/account/orders/{order_id}")
            time.sleep(3)
            
            # Находим поле для отправки данных
            message_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='message']"))
            )
            
            # Формируем сообщение с данными аккаунта
            message = f"""
🎮 Данные аккаунта Steam для игры {account_data['game_name']}:

👤 Логин: {account_data['username']}
🔑 Пароль: {account_data['password']}
⏰ Время аренды: {account_data['duration']} часов
📅 Начало: {account_data['start_time']}

⚠️ ВАЖНО: 
- Не меняйте пароль от аккаунта
- Не добавляйте друзей
- Не используйте аккаунт для мошенничества
- После окончания аренды пароль будет изменен автоматически

💡 Для продления аренды или получения поддержки используйте нашего Telegram бота

Удачной игры! 🎯
            """
            
            message_field.clear()
            message_field.send_keys(message.strip())
            
            # Отправляем сообщение
            send_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            send_button.click()
            
            time.sleep(3)
            print(f"Данные аккаунта отправлены для заказа {order_id}")
            return True
            
        except Exception as e:
            print(f"Ошибка при обработке заказа {order_id}: {e}")
            return False
    
    def check_reviews(self):
        """Проверка новых отзывов"""
        try:
            if not self.is_logged_in:
                if not self.login_to_funpay():
                    return []
            
            # Переходим на страницу отзывов
            self.driver.get(f"{self.base_url}/account/reviews")
            time.sleep(3)
            
            reviews = []
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, ".review-item")
            
            for element in review_elements:
                try:
                    review_id = element.get_attribute("data-review-id")
                    rating = element.find_element(By.CSS_SELECTOR, ".rating").get_attribute("data-rating")
                    comment = element.find_element(By.CSS_SELECTOR, ".comment").text
                    order_id = element.find_element(By.CSS_SELECTOR, ".order-id").text
                    
                    reviews.append({
                        'id': review_id,
                        'rating': int(rating),
                        'comment': comment,
                        'order_id': order_id
                    })
                    
                except Exception as e:
                    print(f"Ошибка при парсинге отзыва: {e}")
                    continue
            
            return reviews
            
        except Exception as e:
            print(f"Ошибка при проверке отзывов: {e}")
            return []
    
    def close(self):
        """Закрытие браузера"""
        if self.driver:
            self.driver.quit()
            self.driver = None
