#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Автоустановщик зависимостей для Steam Rental System
Автоматически устанавливает все необходимые пакеты Python
"""

import subprocess
import sys
import os
import platform
from pathlib import Path

class AutoInstaller:
    def __init__(self):
        self.system = platform.system()
        self.python_version = sys.version_info
        self.requirements_file = "requirements.txt"
        
    def print_banner(self):
        """Печать баннера"""
        print("=" * 60)
        print("🎮 Steam Rental System - Автоустановщик")
        print("=" * 60)
        print(f"💻 Операционная система: {self.system}")
        print(f"🐍 Версия Python: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        print(f"📁 Рабочая директория: {os.getcwd()}")
        print("=" * 60)
        print()
    
    def check_python_version(self):
        """Проверка версии Python"""
        if self.python_version < (3, 8):
            print("❌ Ошибка: Требуется Python 3.8 или выше!")
            print(f"   У вас установлена версия: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
            return False
        
        print("✅ Версия Python подходит")
        return True
    
    def check_pip(self):
        """Проверка наличия pip"""
        try:
            import pip
            print("✅ pip доступен")
            return True
        except ImportError:
            print("❌ pip не найден!")
            return False
    
    def upgrade_pip(self):
        """Обновление pip"""
        print("🔄 Обновление pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            print("✅ pip обновлен")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка обновления pip: {e}")
            return False
    
    def install_requirements(self):
        """Установка зависимостей из requirements.txt"""
        if not os.path.exists(self.requirements_file):
            print(f"❌ Файл {self.requirements_file} не найден!")
            return False
        
        print(f"📦 Установка зависимостей из {self.requirements_file}...")
        
        try:
            # Читаем requirements.txt
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            print(f"📋 Найдено {len(requirements)} пакетов для установки")
            
            # Устанавливаем каждый пакет
            for i, requirement in enumerate(requirements, 1):
                print(f"🔄 [{i}/{len(requirements)}] Установка {requirement}...")
                
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", requirement, "--quiet"
                    ])
                    print(f"✅ {requirement} установлен")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Ошибка установки {requirement}: {e}")
                    return False
            
            print("✅ Все зависимости установлены успешно!")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка чтения {self.requirements_file}: {e}")
            return False
    
    def install_system_dependencies(self):
        """Установка системных зависимостей"""
        print("🔧 Проверка системных зависимостей...")
        
        if self.system == "Windows":
            print("💡 На Windows дополнительные зависимости не требуются")
        elif self.system == "Linux":
            print("🐧 Установка системных зависимостей для Linux...")
            try:
                # Устанавливаем необходимые пакеты для Linux
                subprocess.check_call([
                    "sudo", "apt-get", "update", "-qq"
                ])
                subprocess.check_call([
                    "sudo", "apt-get", "install", "-y", "-qq",
                    "python3-dev", "build-essential", "libssl-dev", "libffi-dev"
                ])
                print("✅ Системные зависимости установлены")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️ Не удалось установить системные зависимости (может потребоваться sudo)")
        elif self.system == "Darwin":  # macOS
            print("🍎 Установка системных зависимостей для macOS...")
            try:
                subprocess.check_call([
                    "brew", "install", "openssl", "readline", "sqlite3", "xz", "zlib"
                ])
                print("✅ Системные зависимости установлены")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️ Homebrew не найден. Установите его с https://brew.sh/")
    
    def create_virtual_environment(self):
        """Создание виртуального окружения"""
        print("🔧 Создание виртуального окружения...")
        
        venv_name = "venv"
        if os.path.exists(venv_name):
            print(f"✅ Виртуальное окружение {venv_name} уже существует")
            return True
        
        try:
            subprocess.check_call([sys.executable, "-m", "venv", venv_name])
            print(f"✅ Виртуальное окружение {venv_name} создано")
            
            # Активация виртуального окружения
            if self.system == "Windows":
                activate_script = os.path.join(venv_name, "Scripts", "activate.bat")
                print(f"💡 Для активации выполните: {activate_script}")
            else:
                activate_script = os.path.join(venv_name, "bin", "activate")
                print(f"💡 Для активации выполните: source {activate_script}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания виртуального окружения: {e}")
            return False
    
    def check_chrome_driver(self):
        """Проверка Chrome Driver"""
        print("🌐 Проверка Chrome Driver...")
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            print(f"✅ Chrome Driver найден: {driver_path}")
            return True
        except Exception as e:
            print(f"⚠️ Chrome Driver не найден: {e}")
            print("💡 Он будет автоматически загружен при первом запуске")
            return False
    
    def create_launcher_scripts(self):
        """Создание скриптов запуска"""
        print("🚀 Создание скриптов запуска...")
        
        # Windows batch файл
        if self.system == "Windows":
            batch_content = """@echo off
echo 🎮 Запуск Steam Rental System...
echo.
python main.py
pause
"""
            with open("start.bat", "w", encoding="cp1251") as f:
                f.write(batch_content)
            print("✅ Создан start.bat")
        
        # Linux/macOS shell скрипт
        else:
            shell_content = """#!/bin/bash
echo "🎮 Запуск Steam Rental System..."
echo
python3 main.py
"""
            with open("start.sh", "w", encoding="utf-8") as f:
                f.write(shell_content)
            
            # Делаем исполняемым
            os.chmod("start.sh", 0o755)
            print("✅ Создан start.sh")
    
    def create_config_template(self):
        """Создание шаблона конфигурации"""
        print("⚙️ Создание шаблона конфигурации...")
        
        if not os.path.exists(".env"):
            if os.path.exists("env_example.txt"):
                import shutil
                shutil.copy("env_example.txt", ".env")
                print("✅ Создан .env из env_example.txt")
                print("💡 Отредактируйте .env файл, указав ваши данные")
            else:
                print("⚠️ Файл env_example.txt не найден")
        else:
            print("✅ Файл .env уже существует")
    
    def run_tests(self):
        """Запуск тестов"""
        print("🧪 Проверка установки...")
        
        try:
            # Проверяем импорт основных модулей
            import config
            import database
            import steam_manager
            import funpay_manager
            import telegram_bot
            print("✅ Все модули импортируются успешно")
            return True
        except ImportError as e:
            print(f"❌ Ошибка импорта: {e}")
            return False
    
    def show_next_steps(self):
        """Показать следующие шаги"""
        print("\n" + "=" * 60)
        print("🎉 Установка завершена!")
        print("=" * 60)
        print("\n📋 Следующие шаги:")
        print("1. Отредактируйте файл .env, указав ваши данные")
        print("2. Получите Telegram токен у @BotFather")
        print("3. Настройте FunPay аккаунт")
        print("4. Получите Steam API ключ")
        print("\n🚀 Запуск:")
        
        if self.system == "Windows":
            print("   • Двойной клик на start.bat")
            print("   • Или: python main.py")
        else:
            print("   • ./start.sh")
            print("   • Или: python3 main.py")
        
        print("\n📚 Документация: README.md")
        print("🆘 Поддержка: создайте issue в репозитории")
        print("\n" + "=" * 60)
    
    def run(self):
        """Основной метод запуска"""
        self.print_banner()
        
        # Проверки
        if not self.check_python_version():
            return False
        
        if not self.check_pip():
            print("💡 Установите pip: https://pip.pypa.io/en/stable/installation/")
            return False
        
        # Обновление pip
        self.upgrade_pip()
        
        # Системные зависимости
        self.install_system_dependencies()
        
        # Виртуальное окружение
        self.create_virtual_environment()
        
        # Установка Python пакетов
        if not self.install_requirements():
            return False
        
        # Проверка Chrome Driver
        self.check_chrome_driver()
        
        # Создание скриптов запуска
        self.create_launcher_scripts()
        
        # Создание конфигурации
        self.create_config_template()
        
        # Тесты
        if not self.run_tests():
            print("⚠️ Установка завершена с предупреждениями")
        
        # Следующие шаги
        self.show_next_steps()
        
        return True

def main():
    """Главная функция"""
    installer = AutoInstaller()
    
    try:
        success = installer.run()
        if success:
            print("\n✅ Автоустановка завершена успешно!")
        else:
            print("\n❌ Автоустановка завершена с ошибками!")
            print("💡 Проверьте сообщения выше и исправьте ошибки")
        
        input("\nНажмите Enter для выхода...")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Установка прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
