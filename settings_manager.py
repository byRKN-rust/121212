#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚙️ Менеджер настроек и токенов для Steam Rental System
Управление конфигурацией, токенами, настройками безопасности
"""

import json
import os
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from cryptography.fernet import Fernet
import base64
from pathlib import Path

class SettingsManager:
    """Менеджер настроек и токенов"""
    
    def __init__(self, db_path: str = "steam_rental.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.encryption_key = self._get_or_create_encryption_key()
        self.setup_database()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Получение или создание ключа шифрования"""
        key_file = "encryption.key"
        
        if os.path.exists(key_file):
            try:
                with open(key_file, "rb") as f:
                    return f.read()
            except Exception as e:
                self.logger.error(f"Ошибка чтения ключа шифрования: {e}")
        
        # Создаем новый ключ
        try:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            self.logger.info("Создан новый ключ шифрования")
            return key
        except Exception as e:
            self.logger.error(f"Ошибка создания ключа шифрования: {e}")
            # Возвращаем базовый ключ для совместимости
            return base64.urlsafe_b64encode(b"default_key_32_bytes_long!!")
    
    def setup_database(self):
        """Настройка базы данных для настроек"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS application_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    encrypted BOOLEAN DEFAULT 0,
                    description TEXT,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_by TEXT,
                    UNIQUE(category, key)
                )
            """)
            
            # Таблица токенов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    token_type TEXT NOT NULL,
                    token_value TEXT NOT NULL,
                    encrypted BOOLEAN DEFAULT 1,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    description TEXT
                )
            """)
            
            # Таблица истории изменений настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)
            
            # Таблица профилей настроек
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )
            """)
            
            # Таблица настроек профилей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_settings (
                    profile_id INTEGER,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    encrypted BOOLEAN DEFAULT 0,
                    FOREIGN KEY (profile_id) REFERENCES settings_profiles (id),
                    UNIQUE(profile_id, category, key)
                )
            """)
            
            conn.commit()
            
            # Инициализируем базовые настройки
            self._initialize_default_settings()
    
    def _initialize_default_settings(self):
        """Инициализация базовых настроек"""
        default_settings = {
            "telegram": {
                "bot_token": "",
                "admin_id": "",
                "webhook_url": "",
                "auto_replies": "1",
                "notification_sound": "1"
            },
            "funpay": {
                "login": "",
                "password": "",
                "auto_login": "1",
                "headless_mode": "1",
                "message_delay": "3"
            },
            "steam": {
                "api_key": "",
                "auto_password_change": "1",
                "password_length": "12",
                "backup_accounts": "1"
            },
            "database": {
                "backup_interval": "24",
                "max_backups": "7",
                "auto_cleanup": "1",
                "encryption": "1"
            },
            "security": {
                "session_timeout": "3600",
                "max_login_attempts": "5",
                "two_factor_auth": "0",
                "ip_whitelist": ""
            },
            "notifications": {
                "email_enabled": "0",
                "telegram_enabled": "1",
                "sms_enabled": "0",
                "push_enabled": "1"
            },
            "rental": {
                "auto_extend": "0",
                "bonus_system": "1",
                "review_reminder": "1",
                "maintenance_mode": "0"
            },
            "system": {
                "log_level": "INFO",
                "auto_update": "1",
                "performance_mode": "0",
                "debug_mode": "0"
            }
        }
        
        for category, settings in default_settings.items():
            for key, value in settings.items():
                self.set_setting(category, key, value, description=f"Базовая настройка {category}.{key}")
    
    def set_setting(self, category: str, key: str, value: str, 
                   encrypted: bool = False, description: str = "", user_id: str = "system") -> bool:
        """Установка настройки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем старое значение для истории
                cursor.execute("""
                    SELECT value FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key))
                
                old_value = cursor.fetchone()
                old_value = old_value[0] if old_value else None
                
                # Шифруем значение если нужно
                if encrypted and value:
                    value = self._encrypt_value(value)
                
                # Обновляем или создаем настройку
                cursor.execute("""
                    INSERT OR REPLACE INTO application_settings 
                    (category, key, value, encrypted, description, last_modified, modified_by)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (category, key, value, encrypted, description, user_id))
                
                # Записываем в историю
                if old_value != value:
                    cursor.execute("""
                        INSERT INTO settings_history 
                        (category, key, old_value, new_value, user_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (category, key, old_value, value, user_id))
                
                conn.commit()
                self.logger.info(f"Настройка {category}.{key} обновлена")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка установки настройки {category}.{key}: {e}")
            return False
    
    def get_setting(self, category: str, key: str, default: str = "") -> str:
        """Получение настройки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT value, encrypted FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key))
                
                result = cursor.fetchone()
                if result:
                    value, encrypted = result
                    if encrypted and value:
                        value = self._decrypt_value(value)
                    return value or default
                
                return default
                
        except Exception as e:
            self.logger.error(f"Ошибка получения настройки {category}.{key}: {e}")
            return default
    
    def get_category_settings(self, category: str) -> Dict[str, str]:
        """Получение всех настроек категории"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT key, value, encrypted FROM application_settings 
                    WHERE category = ? ORDER BY key
                """, (category,))
                
                settings = {}
                for row in cursor.fetchall():
                    key, value, encrypted = row
                    if encrypted and value:
                        value = self._decrypt_value(value)
                    settings[key] = value or ""
                
                return settings
                
        except Exception as e:
            self.logger.error(f"Ошибка получения настроек категории {category}: {e}")
            return {}
    
    def get_all_settings(self) -> Dict[str, Dict[str, str]]:
        """Получение всех настроек"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT category, key, value, encrypted FROM application_settings 
                    ORDER BY category, key
                """)
                
                all_settings = {}
                for row in cursor.fetchall():
                    category, key, value, encrypted = row
                    
                    if category not in all_settings:
                        all_settings[category] = {}
                    
                    if encrypted and value:
                        value = self._decrypt_value(value)
                    
                    all_settings[category][key] = value or ""
                
                return all_settings
                
        except Exception as e:
            self.logger.error(f"Ошибка получения всех настроек: {e}")
            return {}
    
    def delete_setting(self, category: str, key: str) -> bool:
        """Удаление настройки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем значение для истории
                cursor.execute("""
                    SELECT value FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key))
                
                old_value = cursor.fetchone()
                if old_value:
                    old_value = old_value[0]
                    
                    # Записываем в историю
                    cursor.execute("""
                        INSERT INTO settings_history 
                        (category, key, old_value, new_value, user_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (category, key, old_value, None, "system"))
                    
                    # Удаляем настройку
                    cursor.execute("""
                        DELETE FROM application_settings 
                        WHERE category = ? AND key = ?
                    """, (category, key))
                    
                    conn.commit()
                    self.logger.info(f"Настройка {category}.{key} удалена")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка удаления настройки {category}.{key}: {e}")
            return False
    
    def set_token(self, service_name: str, token_type: str, token_value: str, 
                  expires_at: Optional[datetime] = None, description: str = "") -> bool:
        """Установка API токена"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Шифруем токен
                encrypted_token = self._encrypt_value(token_value)
                
                # Обновляем или создаем токен
                cursor.execute("""
                    INSERT OR REPLACE INTO api_tokens 
                    (service_name, token_type, token_value, encrypted, expires_at, description)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (service_name, token_type, encrypted_token, expires_at, description))
                
                conn.commit()
                self.logger.info(f"Токен {service_name}.{token_type} обновлен")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка установки токена {service_name}.{token_type}: {e}")
            return False
    
    def get_token(self, service_name: str, token_type: str) -> Optional[str]:
        """Получение API токена"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT token_value, expires_at, is_active FROM api_tokens 
                    WHERE service_name = ? AND token_type = ?
                """, (service_name, token_type))
                
                result = cursor.fetchone()
                if result:
                    token_value, expires_at, is_active = result
                    
                    if not is_active:
                        return None
                    
                    if expires_at:
                        expiry = datetime.fromisoformat(expires_at)
                        if datetime.now() > expiry:
                            self.logger.warning(f"Токен {service_name}.{token_type} истек")
                            return None
                    
                    # Обновляем статистику использования
                    cursor.execute("""
                        UPDATE api_tokens 
                        SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                        WHERE service_name = ? AND token_type = ?
                    """, (service_name, token_type))
                    
                    conn.commit()
                    
                    # Расшифровываем и возвращаем токен
                    return self._decrypt_value(token_value)
                
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка получения токена {service_name}.{token_type}: {e}")
            return None
    
    def get_all_tokens(self) -> List[Dict[str, Any]]:
        """Получение всех токенов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT service_name, token_type, expires_at, created_at, 
                           last_used, usage_count, is_active, description
                    FROM api_tokens ORDER BY service_name, token_type
                """)
                
                tokens = []
                for row in cursor.fetchall():
                    tokens.append({
                        'service_name': row[0],
                        'token_type': row[1],
                        'expires_at': row[2],
                        'created_at': row[3],
                        'last_used': row[4],
                        'usage_count': row[5],
                        'is_active': bool(row[6]),
                        'description': row[7]
                    })
                
                return tokens
                
        except Exception as e:
            self.logger.error(f"Ошибка получения всех токенов: {e}")
            return []
    
    def delete_token(self, service_name: str, token_type: str) -> bool:
        """Удаление API токена"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM api_tokens 
                    WHERE service_name = ? AND token_type = ?
                """, (service_name, token_type))
                
                conn.commit()
                self.logger.info(f"Токен {service_name}.{token_type} удален")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка удаления токена {service_name}.{token_type}: {e}")
            return False
    
    def create_settings_profile(self, name: str, description: str = "", 
                              created_by: str = "system") -> int:
        """Создание профиля настроек"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO settings_profiles (name, description, created_by)
                    VALUES (?, ?, ?)
                """, (name, description, created_by))
                
                profile_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"Профиль настроек {name} создан с ID {profile_id}")
                return profile_id
                
        except Exception as e:
            self.logger.error(f"Ошибка создания профиля настроек {name}: {e}")
            raise
    
    def save_settings_to_profile(self, profile_id: int, settings: Dict[str, Dict[str, str]]) -> bool:
        """Сохранение настроек в профиль"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Очищаем старые настройки профиля
                cursor.execute("DELETE FROM profile_settings WHERE profile_id = ?", (profile_id,))
                
                # Сохраняем новые настройки
                for category, category_settings in settings.items():
                    for key, value in category_settings.items():
                        cursor.execute("""
                            INSERT INTO profile_settings (profile_id, category, key, value)
                            VALUES (?, ?, ?, ?)
                        """, (profile_id, category, key, value))
                
                conn.commit()
                self.logger.info(f"Настройки сохранены в профиль {profile_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка сохранения настроек в профиль {profile_id}: {e}")
            return False
    
    def load_settings_from_profile(self, profile_id: int) -> Dict[str, Dict[str, str]]:
        """Загрузка настроек из профиля"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT category, key, value FROM profile_settings 
                    WHERE profile_id = ? ORDER BY category, key
                """, (profile_id,))
                
                settings = {}
                for row in cursor.fetchall():
                    category, key, value = row
                    
                    if category not in settings:
                        settings[category] = {}
                    
                    settings[category][key] = value or ""
                
                return settings
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки настроек из профиля {profile_id}: {e}")
            return {}
    
    def get_settings_profiles(self) -> List[Dict[str, Any]]:
        """Получение всех профилей настроек"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, name, description, is_default, created_at, created_by
                    FROM settings_profiles ORDER BY name
                """)
                
                profiles = []
                for row in cursor.fetchall():
                    profiles.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'is_default': bool(row[3]),
                        'created_at': row[4],
                        'created_by': row[5]
                    })
                
                return profiles
                
        except Exception as e:
            self.logger.error(f"Ошибка получения профилей настроек: {e}")
            return []
    
    def export_settings(self, file_path: str) -> bool:
        """Экспорт настроек в файл"""
        try:
            settings = self.get_all_settings()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Настройки экспортированы в {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта настроек: {e}")
            return False
    
    def import_settings(self, file_path: str, overwrite: bool = False) -> bool:
        """Импорт настроек из файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            imported_count = 0
            for category, category_settings in settings.items():
                for key, value in category_settings.items():
                    if overwrite or not self.get_setting(category, key):
                        self.set_setting(category, key, value, description=f"Импортировано из {file_path}")
                        imported_count += 1
            
            self.logger.info(f"Импортировано {imported_count} настроек из {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка импорта настроек: {e}")
            return False
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """Валидация настроек"""
        errors = {}
        
        # Проверяем обязательные настройки
        required_settings = {
            "telegram": ["bot_token", "admin_id"],
            "funpay": ["login", "password"],
            "steam": ["api_key"]
        }
        
        for category, required_keys in required_settings.items():
            category_errors = []
            for key in required_keys:
                value = self.get_setting(category, key)
                if not value:
                    category_errors.append(f"Отсутствует обязательная настройка: {key}")
            
            if category_errors:
                errors[category] = category_errors
        
        # Проверяем формат токенов
        telegram_token = self.get_setting("telegram", "bot_token")
        if telegram_token and not telegram_token.startswith("5"):
            if "telegram" not in errors:
                errors["telegram"] = []
            errors["telegram"].append("Неверный формат Telegram токена")
        
        return errors
    
    def _encrypt_value(self, value: str) -> str:
        """Шифрование значения"""
        try:
            fernet = Fernet(self.encryption_key)
            encrypted = fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Ошибка шифрования: {e}")
            return value
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Расшифровка значения"""
        try:
            fernet = Fernet(self.encryption_key)
            decoded = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Ошибка расшифровки: {e}")
            return encrypted_value
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """Получение сводки настроек"""
        try:
            all_settings = self.get_all_settings()
            tokens = self.get_all_tokens()
            profiles = self.get_settings_profiles()
            validation_errors = self.validate_settings()
            
            return {
                'total_categories': len(all_settings),
                'total_settings': sum(len(cat_settings) for cat_settings in all_settings.values()),
                'total_tokens': len(tokens),
                'active_tokens': len([t for t in tokens if t['is_active']]),
                'total_profiles': len(profiles),
                'default_profile': next((p for p in profiles if p['is_default']), None),
                'validation_errors': validation_errors,
                'has_errors': bool(validation_errors),
                'last_modified': self._get_last_modified_setting()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки настроек: {e}")
            return {}
    
    def _get_last_modified_setting(self) -> Optional[str]:
        """Получение времени последнего изменения настроек"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT last_modified FROM application_settings 
                    ORDER BY last_modified DESC LIMIT 1
                """)
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            self.logger.error(f"Ошибка получения времени последнего изменения: {e}")
            return None
