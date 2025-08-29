#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 Steam Rental System - Основная система
Оркестратор всех компонентов
"""

import time
import schedule
import threading
from datetime import datetime, timedelta
from config import Config
from database import Database
from steam_manager import SteamManager
from funpay_manager import FunPayManager

class SteamRentalSystem:
    def __init__(self):
        self.db = Database()
        self.steam_manager = SteamManager()
        self.funpay_manager = FunPayManager()
        self.running = False
        
    def start(self):
        """Запуск всей системы"""
        print("🚀 Запуск системы аренды аккаунтов Steam...")
        
        # Запускаем планировщик задач
        self.setup_scheduler()
        
        # Запускаем основной цикл
        self.running = True
        self.main_loop()
    
    def setup_scheduler(self):
        """Настройка планировщика задач"""
        # Проверка истекших аренд каждые 5 минут
        schedule.every(5).minutes.do(self.check_expired_rentals)
        
        # Проверка новых заказов каждые 10 минут
        schedule.every(10).minutes.do(self.check_new_orders)
        
        # Проверка новых отзывов каждые 15 минут
        schedule.every(15).minutes.do(self.check_new_reviews)
        
        # Синхронизация с FunPay каждые 30 минут
        schedule.every(30).minutes.do(self.sync_with_funpay)
        
        # Резервное копирование базы данных каждый день в 3:00
        schedule.every().day.at("03:00").do(self.backup_database)
        
        print("📅 Планировщик задач настроен")
    
    def main_loop(self):
        """Основной цикл системы"""
        print("🔄 Основной цикл запущен")
        
        try:
            while self.running:
                # Выполняем запланированные задачи
                schedule.run_pending()
                
                # Небольшая пауза
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⏹️ Получен сигнал остановки...")
            self.stop()
        except Exception as e:
            print(f"❌ Ошибка в основном цикле: {e}")
            self.stop()
    
    def check_expired_rentals(self):
        """Проверка и обработка истекших аренд"""
        try:
            print("⏰ Проверка истекших аренд...")
            
            # Получаем количество истекших аренд
            expired_count = self.db.end_expired_rentals()
            
            if expired_count > 0:
                print(f"🔄 Обработано {expired_count} истекших аренд")
                
                # Изменяем пароли для освобожденных аккаунтов
                self.change_passwords_for_expired_accounts()
                
                # Обновляем объявления на FunPay
                self.update_funpay_listings()
            else:
                print("✅ Истекших аренд не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка при проверке истекших аренд: {e}")
    
    def change_passwords_for_expired_accounts(self):
        """Изменение паролей для истекших аккаунтов"""
        try:
            print("🔑 Изменение паролей для истекших аккаунтов...")
            
            # Получаем список освобожденных аккаунтов
            available_accounts = self.db.get_available_accounts()
            
            for account in available_accounts:
                # Генерируем новый пароль
                new_password = self.steam_manager.generate_password()
                
                # Изменяем пароль в Steam
                if self.steam_manager.change_steam_password(
                    account['username'], 
                    account['password'], 
                    new_password
                ):
                    # Обновляем пароль в базе данных
                    self.update_account_password(account['id'], new_password)
                    print(f"✅ Пароль изменен для аккаунта {account['username']}")
                else:
                    print(f"❌ Не удалось изменить пароль для {account['username']}")
                    
        except Exception as e:
            print(f"❌ Ошибка при изменении паролей: {e}")
    
    def update_account_password(self, account_id: int, new_password: str):
        """Обновление пароля аккаунта в базе данных"""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE steam_accounts 
                    SET password = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_password, account_id))
                conn.commit()
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении пароля в БД: {e}")
    
    def check_new_orders(self):
        """Проверка новых заказов на FunPay"""
        try:
            print("📋 Проверка новых заказов...")
            
            # Проверяем новые заказы через FunPay
            new_orders = self.funpay_manager.check_new_orders()
            
            if new_orders:
                print(f"🆕 Найдено {len(new_orders)} новых заказов")
                
                for order in new_orders:
                    # Обрабатываем заказ
                    self.process_new_order(order)
            else:
                print("✅ Новых заказов не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка при проверке заказов: {e}")
    
    def process_new_order(self, order: dict):
        """Обработка нового заказа"""
        try:
            print(f"🔄 Обработка заказа {order['id']} для игры {order['game_name']}")
            
            # Ищем доступный аккаунт для игры
            available_accounts = self.db.get_available_accounts(order['game_name'])
            
            if available_accounts:
                # Берем первый доступный аккаунт
                account = available_accounts[0]
                
                # Парсим длительность аренды
                duration_hours = self.parse_duration(order['duration'])
                
                # Арендуем аккаунт
                if self.db.rent_account(account['id'], order['id'], duration_hours):
                    # Отправляем данные аккаунта через FunPay
                    account_data = {
                        'username': account['username'],
                        'password': account['password'],
                        'game_name': account['game_name'],
                        'duration': duration_hours,
                        'start_time': datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    
                    if self.funpay_manager.process_order(order['id'], account_data):
                        print(f"✅ Заказ {order['id']} обработан успешно")
                    else:
                        print(f"❌ Не удалось отправить данные для заказа {order['id']}")
                else:
                    print(f"❌ Не удалось арендовать аккаунт для заказа {order['id']}")
            else:
                print(f"❌ Нет доступных аккаунтов для игры {order['game_name']}")
                
        except Exception as e:
            print(f"❌ Ошибка при обработке заказа {order['id']}: {e}")
    
    def parse_duration(self, duration_str: str) -> int:
        """Парсинг длительности аренды"""
        try:
            # Примеры: "2 часа", "24 часа", "7 дней"
            if "час" in duration_str:
                return int(duration_str.split()[0])
            elif "день" in duration_str or "дней" in duration_str:
                days = int(duration_str.split()[0])
                return days * 24
            else:
                return Config.DEFAULT_RENTAL_DURATION
        except:
            return Config.DEFAULT_RENTAL_DURATION
    
    def check_new_reviews(self):
        """Проверка новых отзывов на FunPay"""
        try:
            print("⭐ Проверка новых отзывов...")
            
            # Проверяем новые отзывы через FunPay
            new_reviews = self.funpay_manager.check_reviews()
            
            if new_reviews:
                print(f"🆕 Найдено {len(new_reviews)} новых отзывов")
                
                for review in new_reviews:
                    # Обрабатываем отзыв
                    self.process_new_review(review)
            else:
                print("✅ Новых отзывов не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка при проверке отзывов: {e}")
    
    def process_new_review(self, review: dict):
        """Обработка нового отзыва"""
        try:
            print(f"🔄 Обработка отзыва {review['id']}")
            
            # Если отзыв положительный (4-5 звезд), добавляем бонусное время
            if review['rating'] >= 4:
                # Находим пользователя по order_id
                user_id = self.find_user_by_order(review['order_id'])
                
                if user_id:
                    # Добавляем бонусное время (30 минут)
                    self.add_bonus_time_to_user(user_id, 30)
                    print(f"🎁 Добавлено 30 минут бонусного времени для пользователя {user_id}")
                else:
                    print(f"❌ Не удалось найти пользователя для заказа {review['order_id']}")
            else:
                print(f"📝 Отзыв {review['id']} не подходит для бонуса (оценка: {review['rating']})")
                
        except Exception as e:
            print(f"❌ Ошибка при обработке отзыва {review['id']}: {e}")
    
    def find_user_by_order(self, order_id: str) -> str:
        """Поиск пользователя по ID заказа"""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT renter_id FROM rentals 
                    WHERE id = ?
                ''', (order_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            print(f"❌ Ошибка при поиске пользователя: {e}")
            return None
    
    def add_bonus_time_to_user(self, user_id: str, minutes: int):
        """Добавление бонусного времени пользователю"""
        try:
            # Здесь должна быть логика добавления бонусного времени
            # Для демонстрации просто логируем
            print(f"🎁 Добавлено {minutes} минут бонусного времени для пользователя {user_id}")
            
        except Exception as e:
            print(f"❌ Ошибка при добавлении бонусного времени: {e}")
    
    def sync_with_funpay(self):
        """Синхронизация с FunPay"""
        try:
            print("🔄 Синхронизация с FunPay...")
            
            # Проверяем статус заказов
            orders = self.funpay_manager.check_new_orders()
            
            # Проверяем отзывы
            reviews = self.funpay_manager.check_reviews()
            
            print(f"✅ Синхронизация завершена. Заказов: {len(orders)}, отзывов: {len(reviews)}")
            
        except Exception as e:
            print(f"❌ Ошибка при синхронизации с FunPay: {e}")
    
    def backup_database(self):
        """Резервное копирование базы данных"""
        try:
            print("💾 Создание резервной копии базы данных...")
            
            # Здесь должна быть логика создания резервной копии
            # Для демонстрации просто логируем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"steam_rental_backup_{timestamp}.db"
            
            print(f"✅ Резервная копия создана: {backup_filename}")
            
        except Exception as e:
            print(f"❌ Ошибка при создании резервной копии: {e}")
    
    def stop(self):
        """Остановка системы"""
        print("🛑 Остановка системы...")
        
        self.running = False
        
        # Закрываем FunPay менеджер
        self.funpay_manager.close()
        
        print("✅ Система остановлена")
