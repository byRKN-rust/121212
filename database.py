import sqlite3
import datetime
from typing import List, Dict, Optional
from config import Config

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица аккаунтов Steam
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS steam_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    is_rented BOOLEAN DEFAULT FALSE,
                    current_renter_id TEXT,
                    rental_start_time DATETIME,
                    rental_end_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица аренды
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rentals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER,
                    renter_id TEXT NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    duration_hours INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES steam_accounts (id)
                )
            ''')
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # НОВАЯ таблица бонусов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bonuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    bonus_minutes INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # НОВАЯ таблица уведомлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    type TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # НОВАЯ таблица истории операций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # НОВАЯ таблица статистики
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_name TEXT NOT NULL,
                    total_rentals INTEGER DEFAULT 0,
                    total_revenue REAL DEFAULT 0.0,
                    average_rating REAL DEFAULT 0.0,
                    total_reviews INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_steam_account(self, username: str, password: str, game_name: str) -> int:
        """Добавление нового аккаунта Steam"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO steam_accounts (username, password, game_name)
                VALUES (?, ?, ?)
            ''', (username, password, game_name))
            conn.commit()
            return cursor.lastrowid
    
    def get_available_accounts(self, game_name: str = None) -> List[Dict]:
        """Получение доступных аккаунтов"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if game_name:
                cursor.execute('''
                    SELECT * FROM steam_accounts 
                    WHERE is_rented = FALSE AND game_name = ?
                ''', (game_name,))
            else:
                cursor.execute('''
                    SELECT * FROM steam_accounts 
                    WHERE is_rented = FALSE
                ''')
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def rent_account(self, account_id: int, renter_id: str, duration_hours: int) -> bool:
        """Аренда аккаунта"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Проверяем, доступен ли аккаунт
            cursor.execute('''
                SELECT is_rented FROM steam_accounts WHERE id = ?
            ''', (account_id,))
            
            result = cursor.fetchone()
            if not result or result[0]:
                return False
            
            start_time = datetime.datetime.now()
            end_time = start_time + datetime.timedelta(hours=duration_hours)
            
            # Обновляем статус аккаунта
            cursor.execute('''
                UPDATE steam_accounts 
                SET is_rented = TRUE, current_renter_id = ?, 
                    rental_start_time = ?, rental_end_time = ?
                WHERE id = ?
            ''', (renter_id, start_time, end_time, account_id))
            
            # Создаем запись об аренде
            cursor.execute('''
                INSERT INTO rentals (account_id, renter_id, start_time, end_time, duration_hours)
                VALUES (?, ?, ?, ?, ?)
            ''', (account_id, renter_id, start_time, end_time, duration_hours))
            
            # Добавляем в историю операций
            cursor.execute('''
                INSERT INTO operation_history (user_id, operation_type, description)
                VALUES (?, ?, ?)
            ''', (renter_id, 'rental_start', f'Начата аренда аккаунта на {duration_hours} часов'))
            
            conn.commit()
            return True
    
    def get_rental_info(self, renter_id: str) -> Optional[Dict]:
        """Получение информации об аренде пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sa.username, sa.game_name, r.start_time, r.end_time, r.duration_hours
                FROM steam_accounts sa
                JOIN rentals r ON sa.id = r.account_id
                WHERE r.renter_id = ? AND r.status = 'active'
                ORDER BY r.end_time DESC
                LIMIT 1
            ''', (renter_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'username': result[0],
                    'game_name': result[1],
                    'start_time': result[2],
                    'end_time': result[3],
                    'duration_hours': result[4]
                }
            return None
    
    def get_remaining_time(self, renter_id: str) -> Optional[str]:
        """Получение оставшегося времени аренды"""
        rental_info = self.get_rental_info(renter_id)
        if not rental_info:
            return "У вас нет активной аренды"
        
        end_time = datetime.datetime.fromisoformat(rental_info['end_time'])
        now = datetime.datetime.now()
        
        if now >= end_time:
            return "Время аренды истекло"
        
        remaining = end_time - now
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        return f"Осталось: {hours}ч {minutes}м"
    
    def get_accounts_count_by_game(self, game_name: str) -> int:
        """Получение количества доступных аккаунтов для конкретной игры"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM steam_accounts 
                WHERE is_rented = FALSE AND game_name = ?
            ''', (game_name,))
            return cursor.fetchone()[0]
    
    def get_all_games(self) -> List[str]:
        """Получение списка всех игр"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT game_name FROM steam_accounts
            ''')
            return [row[0] for row in cursor.fetchall()]
    
    def end_expired_rentals(self):
        """Завершение истекших аренд"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Находим истекшие аренды
            cursor.execute('''
                SELECT r.id, r.account_id, r.renter_id FROM rentals r
                WHERE r.status = 'active' AND r.end_time < ?
            ''', (datetime.datetime.now(),))
            
            expired_rentals = cursor.fetchall()
            
            for rental_id, account_id, renter_id in expired_rentals:
                # Обновляем статус аренды
                cursor.execute('''
                    UPDATE rentals SET status = 'expired' WHERE id = ?
                ''', (rental_id,))
                
                # Освобождаем аккаунт
                cursor.execute('''
                    UPDATE steam_accounts 
                    SET is_rented = FALSE, current_renter_id = NULL,
                        rental_start_time = NULL, rental_end_time = NULL
                    WHERE id = ?
                ''', (account_id,))
                
                # Добавляем в историю операций
                cursor.execute('''
                    INSERT INTO operation_history (user_id, operation_type, description)
                    VALUES (?, ?, ?)
                ''', (renter_id, 'rental_end', 'Аренда аккаунта завершена'))
                
                # Создаем уведомление
                cursor.execute('''
                    INSERT INTO notifications (user_id, message, type)
                    VALUES (?, ?, ?)
                ''', (renter_id, 'Время аренды аккаунта истекло. Пароль изменен автоматически.', 'rental_expired'))
            
            conn.commit()
            return len(expired_rentals)
    
    def add_user(self, telegram_id: str, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление нового пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name))
            conn.commit()
    
    # НОВЫЕ ПОЛЕЗНЫЕ ФУНКЦИИ
    
    def add_bonus_time(self, user_id: str, minutes: int, reason: str = "Отзыв"):
        """Добавление бонусного времени пользователю"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bonuses (user_id, bonus_minutes, reason)
                VALUES (?, ?, ?)
            ''', (user_id, minutes, reason))
            conn.commit()
    
    def get_user_bonuses(self, user_id: str) -> List[Dict]:
        """Получение бонусов пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bonus_minutes, reason, is_used, created_at
                FROM bonuses 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_total_bonus_time(self, user_id: str) -> int:
        """Получение общего количества бонусного времени пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT SUM(bonus_minutes) FROM bonuses 
                WHERE user_id = ? AND is_used = FALSE
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result[0] else 0
    
    def add_notification(self, user_id: str, message: str, notification_type: str = "info"):
        """Добавление уведомления пользователю"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (user_id, message, type)
                VALUES (?, ?, ?)
            ''', (user_id, message, notification_type))
            conn.commit()
    
    def get_user_notifications(self, user_id: str, unread_only: bool = True) -> List[Dict]:
        """Получение уведомлений пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if unread_only:
                cursor.execute('''
                    SELECT message, type, created_at FROM notifications 
                    WHERE user_id = ? AND is_read = FALSE
                    ORDER BY created_at DESC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT message, type, is_read, created_at FROM notifications 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT 50
                ''', (user_id,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def mark_notification_read(self, notification_id: int):
        """Отметить уведомление как прочитанное"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE notifications SET is_read = TRUE WHERE id = ?
            ''', (notification_id,))
            conn.commit()
    
    def get_operation_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Получение истории операций пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT operation_type, description, created_at
                FROM operation_history 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Получение общей статистики системы"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Общее количество аккаунтов
            cursor.execute('SELECT COUNT(*) FROM steam_accounts')
            total_accounts = cursor.fetchone()[0]
            
            # Активных аренд
            cursor.execute('SELECT COUNT(*) FROM rentals WHERE status = "active"')
            active_rentals = cursor.fetchone()[0]
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Популярные игры
            cursor.execute('''
                SELECT game_name, COUNT(*) as count
                FROM steam_accounts 
                GROUP BY game_name 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            popular_games = [{'game': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return {
                'total_accounts': total_accounts,
                'active_rentals': active_rentals,
                'total_users': total_users,
                'popular_games': popular_games
            }
    
    def get_user_statistics(self, user_id: str) -> Dict:
        """Получение статистики конкретного пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Количество аренд
            cursor.execute('''
                SELECT COUNT(*) FROM rentals WHERE renter_id = ?
            ''', (user_id,))
            total_rentals = cursor.fetchone()[0]
            
            # Активные аренды
            cursor.execute('''
                SELECT COUNT(*) FROM rentals WHERE renter_id = ? AND status = "active"
            ''', (user_id,))
            active_rentals = cursor.fetchone()[0]
            
            # Общее бонусное время
            total_bonus = self.get_total_bonus_time(user_id)
            
            # Любимые игры
            cursor.execute('''
                SELECT sa.game_name, COUNT(*) as count
                FROM rentals r
                JOIN steam_accounts sa ON r.account_id = sa.id
                WHERE r.renter_id = ?
                GROUP BY sa.game_name
                ORDER BY count DESC
                LIMIT 3
            ''', (user_id,))
            favorite_games = [{'game': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            return {
                'total_rentals': total_rentals,
                'active_rentals': active_rentals,
                'total_bonus_minutes': total_bonus,
                'favorite_games': favorite_games
            }
    
    def search_accounts(self, query: str) -> List[Dict]:
        """Поиск аккаунтов по названию игры"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM steam_accounts 
                WHERE game_name LIKE ? AND is_rented = FALSE
            ''', (f'%{query}%',))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Получение последней активности в системе"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, operation_type, description, created_at
                FROM operation_history 
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
