#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 Менеджер аккаунтов Steam для системы аренды
Управление аккаунтами, сортировка, статистика доходов
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

class AccountStatus(Enum):
    """Статусы аккаунтов"""
    AVAILABLE = "available"
    RENTED = "rented"
    MAINTENANCE = "maintenance"
    BANNED = "banned"
    DELETED = "deleted"

class AccountCategory(Enum):
    """Категории аккаунтов"""
    PREMIUM = "premium"
    STANDARD = "standard"
    ECONOMY = "economy"
    VIP = "vip"

@dataclass
class AccountInfo:
    """Информация об аккаунте"""
    id: int
    login: str
    password: str
    email: str
    email_password: str
    games: List[str]
    status: AccountStatus
    category: AccountCategory
    price_per_hour: float
    total_earnings: float
    total_rental_time: int  # в минутах
    rental_count: int
    created_date: datetime
    last_rental_date: Optional[datetime]
    notes: str
    tags: List[str]

class AccountManager:
    """Менеджер аккаунтов Steam"""
    
    def __init__(self, db_path: str = "steam_rental.db"):
        self.db_path = db_path
        self.setup_database()
        self.logger = logging.getLogger(__name__)
    
    def setup_database(self):
        """Настройка базы данных для аккаунтов"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица аккаунтов с расширенной информацией
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS steam_accounts_extended (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT,
                    email_password TEXT,
                    games TEXT,  -- JSON список игр
                    status TEXT DEFAULT 'available',
                    category TEXT DEFAULT 'standard',
                    price_per_hour REAL DEFAULT 10.0,
                    total_earnings REAL DEFAULT 0.0,
                    total_rental_time INTEGER DEFAULT 0,
                    rental_count INTEGER DEFAULT 0,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_rental_date TIMESTAMP,
                    notes TEXT,
                    tags TEXT,  -- JSON список тегов
                    steam_guard_enabled BOOLEAN DEFAULT 1,
                    phone_number TEXT,
                    backup_codes TEXT,  -- JSON список резервных кодов
                    last_password_change TIMESTAMP,
                    security_questions TEXT,  -- JSON ответы на вопросы безопасности
                    profile_url TEXT,
                    avatar_url TEXT,
                    level INTEGER DEFAULT 0,
                    friends_count INTEGER DEFAULT 0,
                    games_count INTEGER DEFAULT 0,
                    badges_count INTEGER DEFAULT 0,
                    achievements_count INTEGER DEFAULT 0,
                    playtime_total INTEGER DEFAULT 0,  -- в минутах
                    last_online TIMESTAMP,
                    country TEXT,
                    language TEXT,
                    timezone TEXT
                )
            """)
            
            # Таблица истории изменений аккаунтов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER,
                    action TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    details TEXT,
                    FOREIGN KEY (account_id) REFERENCES steam_accounts_extended (id)
                )
            """)
            
            # Таблица статистики аккаунтов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER,
                    date DATE,
                    earnings REAL DEFAULT 0.0,
                    rental_time INTEGER DEFAULT 0,
                    rental_count INTEGER DEFAULT 0,
                    maintenance_time INTEGER DEFAULT 0,
                    issues_count INTEGER DEFAULT 0,
                    FOREIGN KEY (account_id) REFERENCES steam_accounts_extended (id)
                )
            """)
            
            # Таблица тегов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#007bff',
                    description TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица связей аккаунтов с тегами
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_tag_relations (
                    account_id INTEGER,
                    tag_id INTEGER,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (account_id, tag_id),
                    FOREIGN KEY (account_id) REFERENCES steam_accounts_extended (id),
                    FOREIGN KEY (tag_id) REFERENCES account_tags (id)
                )
            """)
            
            conn.commit()
    
    def add_account(self, account_data: Dict) -> int:
        """Добавление нового аккаунта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Подготовка данных
                games_json = json.dumps(account_data.get('games', []), ensure_ascii=False)
                tags_json = json.dumps(account_data.get('tags', []), ensure_ascii=False)
                
                cursor.execute("""
                    INSERT INTO steam_accounts_extended (
                        login, password, email, email_password, games, status, category,
                        price_per_hour, notes, tags, steam_guard_enabled, phone_number,
                        backup_codes, security_questions, profile_url, avatar_url,
                        level, friends_count, games_count, badges_count, achievements_count,
                        playtime_total, country, language, timezone
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_data['login'],
                    account_data['password'],
                    account_data.get('email', ''),
                    account_data.get('email_password', ''),
                    games_json,
                    account_data.get('status', 'available'),
                    account_data.get('category', 'standard'),
                    account_data.get('price_per_hour', 10.0),
                    account_data.get('notes', ''),
                    tags_json,
                    account_data.get('steam_guard_enabled', True),
                    account_data.get('phone_number', ''),
                    json.dumps(account_data.get('backup_codes', []), ensure_ascii=False),
                    json.dumps(account_data.get('security_questions', {}), ensure_ascii=False),
                    account_data.get('profile_url', ''),
                    account_data.get('avatar_url', ''),
                    account_data.get('level', 0),
                    account_data.get('friends_count', 0),
                    account_data.get('games_count', 0),
                    account_data.get('badges_count', 0),
                    account_data.get('achievements_count', 0),
                    account_data.get('playtime_total', 0),
                    account_data.get('country', ''),
                    account_data.get('language', ''),
                    account_data.get('timezone', '')
                ))
                
                account_id = cursor.lastrowid
                
                # Добавляем теги
                if account_data.get('tags'):
                    self._add_account_tags(account_id, account_data['tags'])
                
                # Записываем в историю
                self._log_account_action(account_id, 'account_created', None, json.dumps(account_data))
                
                conn.commit()
                self.logger.info(f"Добавлен аккаунт {account_data['login']} с ID {account_id}")
                return account_id
                
        except Exception as e:
            self.logger.error(f"Ошибка добавления аккаунта: {e}")
            raise
    
    def get_accounts(self, filters: Optional[Dict] = None, sort_by: str = "created_date", 
                    sort_order: str = "DESC", limit: Optional[int] = None) -> List[AccountInfo]:
        """Получение списка аккаунтов с фильтрацией и сортировкой"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Базовый запрос
                query = "SELECT * FROM steam_accounts_extended"
                params = []
                
                # Применяем фильтры
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if key == 'games':
                            conditions.append("games LIKE ?")
                            params.append(f'%{value}%')
                        elif key == 'tags':
                            conditions.append("tags LIKE ?")
                            params.append(f'%{value}%')
                        elif key == 'price_range':
                            conditions.append("price_per_hour BETWEEN ? AND ?")
                            params.extend(value)
                        elif key == 'earnings_range':
                            conditions.append("total_earnings BETWEEN ? AND ?")
                            params.extend(value)
                        elif key == 'status':
                            conditions.append("status = ?")
                            params.append(value)
                        elif key == 'category':
                            conditions.append("category = ?")
                            params.append(value)
                        else:
                            conditions.append(f"{key} = ?")
                            params.append(value)
                    
                    if conditions:
                        query += " WHERE " + " AND ".join(conditions)
                
                # Сортировка
                query += f" ORDER BY {sort_by} {sort_order}"
                
                # Лимит
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                accounts = []
                for row in cursor.fetchall():
                    account = self._row_to_account_info(row)
                    accounts.append(account)
                
                return accounts
                
        except Exception as e:
            self.logger.error(f"Ошибка получения аккаунтов: {e}")
            return []
    
    def update_account(self, account_id: int, updates: Dict) -> bool:
        """Обновление информации об аккаунте"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем старые данные для истории
                cursor.execute("SELECT * FROM steam_accounts_extended WHERE id = ?", (account_id,))
                old_data = cursor.fetchone()
                
                if not old_data:
                    return False
                
                # Подготавливаем обновления
                set_clause = []
                params = []
                
                for key, value in updates.items():
                    if key in ['games', 'tags', 'backup_codes', 'security_questions']:
                        set_clause.append(f"{key} = ?")
                        params.append(json.dumps(value, ensure_ascii=False))
                    else:
                        set_clause.append(f"{key} = ?")
                        params.append(value)
                
                params.append(account_id)
                
                # Обновляем
                query = f"UPDATE steam_accounts_extended SET {', '.join(set_clause)} WHERE id = ?"
                cursor.execute(query, params)
                
                # Обновляем теги если нужно
                if 'tags' in updates:
                    self._update_account_tags(account_id, updates['tags'])
                
                # Записываем в историю
                self._log_account_action(account_id, 'account_updated', 
                                       json.dumps(old_data), json.dumps(updates))
                
                conn.commit()
                self.logger.info(f"Обновлен аккаунт {account_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления аккаунта {account_id}: {e}")
            return False
    
    def delete_account(self, account_id: int) -> bool:
        """Удаление аккаунта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем данные для истории
                cursor.execute("SELECT * FROM steam_accounts_extended WHERE id = ?", (account_id,))
                old_data = cursor.fetchone()
                
                if not old_data:
                    return False
                
                # Удаляем связи с тегами
                cursor.execute("DELETE FROM account_tag_relations WHERE account_id = ?", (account_id,))
                
                # Удаляем статистику
                cursor.execute("DELETE FROM account_statistics WHERE account_id = ?", (account_id,))
                
                # Удаляем историю
                cursor.execute("DELETE FROM account_history WHERE account_id = ?", (account_id,))
                
                # Удаляем аккаунт
                cursor.execute("DELETE FROM steam_accounts_extended WHERE id = ?", (account_id,))
                
                # Записываем в историю
                self._log_account_action(account_id, 'account_deleted', json.dumps(old_data), None)
                
                conn.commit()
                self.logger.info(f"Удален аккаунт {account_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка удаления аккаунта {account_id}: {e}")
            return False
    
    def get_account_statistics(self, account_id: Optional[int] = None) -> Dict:
        """Получение статистики аккаунтов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if account_id:
                    # Статистика конкретного аккаунта
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_accounts,
                            SUM(total_earnings) as total_earnings,
                            SUM(total_rental_time) as total_rental_time,
                            SUM(rental_count) as total_rentals,
                            AVG(price_per_hour) as avg_price,
                            COUNT(CASE WHEN status = 'available' THEN 1 END) as available_count,
                            COUNT(CASE WHEN status = 'rented' THEN 1 END) as rented_count,
                            COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance_count
                        FROM steam_accounts_extended 
                        WHERE id = ?
                    """, (account_id,))
                else:
                    # Общая статистика
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_accounts,
                            SUM(total_earnings) as total_earnings,
                            SUM(total_rental_time) as total_rental_time,
                            SUM(rental_count) as total_rentals,
                            AVG(price_per_hour) as avg_price,
                            COUNT(CASE WHEN status = 'available' THEN 1 END) as available_count,
                            COUNT(CASE WHEN status = 'rented' THEN 1 END) as rented_count,
                            COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance_count
                        FROM steam_accounts_extended
                    """)
                
                row = cursor.fetchone()
                
                # Статистика по категориям
                cursor.execute("""
                    SELECT category, COUNT(*) as count, AVG(total_earnings) as avg_earnings
                    FROM steam_accounts_extended 
                    GROUP BY category
                """)
                category_stats = {row[0]: {'count': row[1], 'avg_earnings': row[2]} for row in cursor.fetchall()}
                
                # Статистика по играм
                cursor.execute("""
                    SELECT games, COUNT(*) as count
                    FROM steam_accounts_extended 
                    WHERE games IS NOT NULL AND games != '[]'
                    GROUP BY games
                    ORDER BY count DESC
                    LIMIT 10
                """)
                game_stats = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    'total_accounts': row[0] or 0,
                    'total_earnings': row[1] or 0.0,
                    'total_rental_time': row[2] or 0,
                    'total_rentals': row[3] or 0,
                    'avg_price': row[4] or 0.0,
                    'available_count': row[5] or 0,
                    'rented_count': row[6] or 0,
                    'maintenance_count': row[7] or 0,
                    'category_stats': category_stats,
                    'game_stats': game_stats
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def search_accounts(self, query: str) -> List[AccountInfo]:
        """Поиск аккаунтов по различным критериям"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                search_query = """
                    SELECT * FROM steam_accounts_extended 
                    WHERE login LIKE ? OR email LIKE ? OR notes LIKE ? 
                    OR games LIKE ? OR tags LIKE ?
                    ORDER BY total_earnings DESC
                """
                
                search_term = f"%{query}%"
                cursor.execute(search_query, (search_term, search_term, search_term, search_term, search_term))
                
                accounts = []
                for row in cursor.fetchall():
                    account = self._row_to_account_info(row)
                    accounts.append(account)
                
                return accounts
                
        except Exception as e:
            self.logger.error(f"Ошибка поиска аккаунтов: {e}")
            return []
    
    def get_top_earning_accounts(self, limit: int = 10) -> List[AccountInfo]:
        """Получение топ аккаунтов по доходу"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM steam_accounts_extended 
                    ORDER BY total_earnings DESC 
                    LIMIT ?
                """, (limit,))
                
                accounts = []
                for row in cursor.fetchall():
                    account = self._row_to_account_info(row)
                    accounts.append(account)
                
                return accounts
                
        except Exception as e:
            self.logger.error(f"Ошибка получения топ аккаунтов: {e}")
            return []
    
    def get_accounts_by_game(self, game_name: str) -> List[AccountInfo]:
        """Получение аккаунтов по игре"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM steam_accounts_extended 
                    WHERE games LIKE ? AND status = 'available'
                    ORDER BY price_per_hour ASC
                """, (f'%{game_name}%',))
                
                accounts = []
                for row in cursor.fetchall():
                    account = self._row_to_account_info(row)
                    accounts.append(account)
                
                return accounts
                
        except Exception as e:
            self.logger.error(f"Ошибка получения аккаунтов по игре {game_name}: {e}")
            return []
    
    def add_tag(self, name: str, color: str = '#007bff', description: str = '') -> int:
        """Добавление нового тега"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO account_tags (name, color, description) 
                    VALUES (?, ?, ?)
                """, (name, color, description))
                
                tag_id = cursor.lastrowid
                conn.commit()
                return tag_id
                
        except Exception as e:
            self.logger.error(f"Ошибка добавления тега: {e}")
            raise
    
    def get_all_tags(self) -> List[Dict]:
        """Получение всех тегов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM account_tags ORDER BY name")
                
                tags = []
                for row in cursor.fetchall():
                    tags.append({
                        'id': row[0],
                        'name': row[1],
                        'color': row[2],
                        'description': row[3],
                        'created_date': row[4]
                    })
                
                return tags
                
        except Exception as e:
            self.logger.error(f"Ошибка получения тегов: {e}")
            return []
    
    def _add_account_tags(self, account_id: int, tags: List[str]):
        """Добавление тегов к аккаунту"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for tag_name in tags:
                    # Получаем или создаем тег
                    cursor.execute("SELECT id FROM account_tags WHERE name = ?", (tag_name,))
                    tag_row = cursor.fetchone()
                    
                    if tag_row:
                        tag_id = tag_row[0]
                    else:
                        cursor.execute("INSERT INTO account_tags (name) VALUES (?)", (tag_name,))
                        tag_id = cursor.lastrowid
                    
                    # Связываем тег с аккаунтом
                    cursor.execute("""
                        INSERT OR IGNORE INTO account_tag_relations (account_id, tag_id) 
                        VALUES (?, ?)
                    """, (account_id, tag_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Ошибка добавления тегов к аккаунту: {e}")
    
    def _update_account_tags(self, account_id: int, new_tags: List[str]):
        """Обновление тегов аккаунта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Удаляем старые связи
                cursor.execute("DELETE FROM account_tag_relations WHERE account_id = ?", (account_id,))
                
                # Добавляем новые теги
                self._add_account_tags(account_id, new_tags)
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления тегов аккаунта: {e}")
    
    def _log_account_action(self, account_id: int, action: str, old_value: Optional[str], 
                           new_value: Optional[str], user_id: Optional[str] = None):
        """Логирование действий с аккаунтом"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO account_history (account_id, action, old_value, new_value, user_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (account_id, action, old_value, new_value, user_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Ошибка логирования действия: {e}")
    
    def _row_to_account_info(self, row: Tuple) -> AccountInfo:
        """Преобразование строки БД в объект AccountInfo"""
        try:
            games = json.loads(row[5]) if row[5] else []
            tags = json.loads(row[16]) if row[16] else []
            
            return AccountInfo(
                id=row[0],
                login=row[1],
                password=row[2],
                email=row[3] or '',
                email_password=row[4] or '',
                games=games,
                status=AccountStatus(row[6]),
                category=AccountCategory(row[7]),
                price_per_hour=row[8] or 0.0,
                total_earnings=row[9] or 0.0,
                total_rental_time=row[10] or 0,
                rental_count=row[11] or 0,
                created_date=datetime.fromisoformat(row[12]) if row[12] else datetime.now(),
                last_rental_date=datetime.fromisoformat(row[13]) if row[13] else None,
                notes=row[14] or '',
                tags=tags
            )
        except Exception as e:
            self.logger.error(f"Ошибка преобразования строки в AccountInfo: {e}")
            # Возвращаем базовый объект
            return AccountInfo(
                id=row[0] if row[0] else 0,
                login=row[1] if row[1] else '',
                password=row[2] if row[2] else '',
                email='',
                email_password='',
                games=[],
                status=AccountStatus.AVAILABLE,
                category=AccountCategory.STANDARD,
                price_per_hour=0.0,
                total_earnings=0.0,
                total_rental_time=0,
                rental_count=0,
                created_date=datetime.now(),
                last_rental_date=None,
                notes='',
                tags=[]
            )
