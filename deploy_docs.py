#!/usr/bin/env python3
"""
Скрипт для сборки документации с помощью mkdocs и деплоя на удаленный сервер.
Параметры подключения и пути берутся из файла .env

sudo apt install expect
pip install python-dotenv paramiko mkdocs
"""

import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
import paramiko
import tempfile

def load_environment():
    """Загрузка переменных окружения из .env файла"""
    load_dotenv()
    
    required_vars = [
        'DOCS_HOST', 
        'DOCS_USER', 
        'DOCS_PASSWORD', 
        'DOCS_TARGET_DIR'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Ошибка: Отсутствуют обязательные переменные в .env файле: {', '.join(missing_vars)}")
        sys.exit(1)
    
    return {
        'host': os.getenv('DOCS_HOST'),
        'user': os.getenv('DOCS_USER'),
        'password': os.getenv('DOCS_PASSWORD'),
        'target_dir': os.getenv('DOCS_TARGET_DIR')
    }

def build_docs():
    """Сборка документации с помощью mkdocs"""
    print("Сборка документации...")
    
    try:
        subprocess.run(["mkdocs", "build"], check=True)
        print("Документация успешно собрана.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при сборке документации: {e}")
        return False
    except FileNotFoundError:
        print("Ошибка: mkdocs не найден. Убедитесь, что mkdocs установлен.")
        return False

def clean_remote_directory(ssh_client, target_dir):
    """Очистка целевой директории на удаленном сервере"""
    print(f"Очистка удаленной директории {target_dir}...")
    
    try:
        # Проверяем существование директории
        stdin, stdout, stderr = ssh_client.exec_command(f"test -d {target_dir} && echo 'exists'")
        if 'exists' not in stdout.read().decode():
            # Создаем директорию, если она не существует
            ssh_client.exec_command(f"mkdir -p {target_dir}")
            print(f"Создана директория {target_dir}")
        else:
            # Удаляем содержимое директории
            ssh_client.exec_command(f"rm -rf {target_dir}/*")
            print(f"Директория {target_dir} очищена")
        
        return True
    except Exception as e:
        print(f"Ошибка при очистке удаленной директории: {e}")
        return False

def deploy_docs(config):
    """Деплой документации на удаленный сервер"""
    print(f"Деплой документации на {config['host']}...")
    
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Подключение к серверу
        ssh_client.connect(
            hostname=config['host'],
            username=config['user'],
            password=config['password']
        )
        
        # Очистка удаленной директории
        if not clean_remote_directory(ssh_client, config['target_dir']):
            return False
        
        # Создаем временный скрипт для SCP
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(f"""#!/usr/bin/expect -f
spawn scp -r site/* {config['user']}@{config['host']}:{config['target_dir']}
expect "password:"
send "{config['password']}\r"
expect eof
""")
        
        # Делаем скрипт исполняемым
        os.chmod(temp_file_path, 0o700)
        
        # Выполняем скрипт
        result = subprocess.run(["bash", "-c", temp_file_path], capture_output=True, text=True)
        
        # Удаляем временный файл
        os.unlink(temp_file_path)
        
        if result.returncode != 0:
            print(f"Ошибка при копировании файлов: {result.stderr}")
            return False
        
        print("Документация успешно развернута на удаленном сервере.")
        return True
        
    except Exception as e:
        print(f"Ошибка при деплое документации: {e}")
        return False
    finally:
        ssh_client.close()

def main():
    """Основная функция"""
    print("Запуск процесса деплоя документации...")
    
    # Загрузка переменных окружения
    config = load_environment()
    
    # Сборка документации
    if not build_docs():
        sys.exit(1)
    
    # Деплой документации
    if not deploy_docs(config):
        sys.exit(1)
    
    print("Процесс деплоя документации успешно завершен!")

if __name__ == "__main__":
    main()
