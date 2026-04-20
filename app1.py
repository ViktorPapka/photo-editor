from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
import os
import uuid
import json
import time
import threading
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter, ImageEnhance
import random
import requests
import re
from database import get_user, create_user, update_balance, add_to_history, get_user_history, test_connection

app = Flask(__name__)
app.secret_key = "ваш_секретный_ключ_например_что-то_случайное_12345"
CORS(app)

# Настройки
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Хранилище задач
tasks = {}

# Словарь с эффектами для демонстрации
EFFECTS = {
    'clothes': {
        'name': 'Смена одежды',
        'effects': ['стиль_кэжуал', 'деловой_стиль', 'спортивный_стиль', 'вечерний_образ']
    },
    'hair': {
        'name': 'Смена прически',
        'effects': ['короткая_стрижка', 'длинные_волосы', 'каре', 'пикси']
    },
    'random': {
        'name': 'Случайный стиль',
        'effects': ['креативный_образ', 'ретро_стиль', 'футуризм', 'натуральный_стиль']
    }
}

def process_photo(task_id, filepath, edit_type, custom_prompt):
    """Имитация обработки фото"""
    try:
        # Обновляем статус
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 30
        print(f"Task {task_id}: Начало обработки (30%)")
        
        # Имитация времени обработки (3-8 секунд)
        time.sleep(random.uniform(3, 6))
        
        tasks[task_id]['progress'] = 70
        print(f"Task {task_id}: Обработка продолжается (70%)")
        
        # Открываем изображение
        img = Image.open(filepath)
        
        # Применяем эффект в зависимости от типа
        if edit_type == 'clothes':
            # Эффект сепия
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.7)
            effect_name = random.choice(EFFECTS['clothes']['effects'])
        elif edit_type == 'hair':
            # Эффект резкости
            img = img.filter(ImageFilter.SHARPEN)
            effect_name = random.choice(EFFECTS['hair']['effects'])
        elif edit_type == 'random':
            # Случайный эффект
            effects_list = [ImageFilter.BLUR, ImageFilter.CONTOUR, ImageFilter.EMBOSS]
            img = img.filter(random.choice(effects_list))
            effect_name = random.choice(EFFECTS['random']['effects'])
        elif edit_type == 'custom':
            # Для ручного запроса - применяем эффект "теплый тон"
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.3)
            effect_name = f"по запросу: {custom_prompt[:50]}"
        else:
            img = img
            effect_name = "оригинал"
        
        tasks[task_id]['progress'] = 90
        print(f"Task {task_id}: Применение эффекта (90%)")
        
        # Сохраняем обработанное изображение
        original_filename = os.path.basename(filepath)
        output_filename = f"{task_id}_{original_filename}"
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        img.save(output_path)
        
        tasks[task_id]['progress'] = 100
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['result_url'] = f'/result/{output_filename}'
        tasks[task_id]['edit_type'] = edit_type
        tasks[task_id]['model_used'] = effect_name
        print(f"Task {task_id}: Завершено успешно")
        
    except Exception as e:
        print(f"Task {task_id}: Ошибка - {str(e)}")
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/me')
def api_me():
    telegram_id = session.get('telegram_id')
    if not telegram_id:
        return jsonify({'authenticated': False})

    user = get_user(telegram_id)
    if not user:
        return jsonify({'authenticated': False})

    return jsonify({
        'authenticated': True,
        'telegram_id': user['telegram_id'],
        'username': user.get('username', ''),
        'first_name': user.get('first_name', ''),
        'balance': user.get('balance', 0)
    })


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/telegram-login', methods=['POST'])
def telegram_login():
    """Упрощённый вход по Telegram ID (без проверки через Telegram API)"""
    data = request.get_json()
    identifier = data.get('identifier', '').strip()

    if not identifier:
        return jsonify({'success': False, 'error': 'Введите Telegram ID или @username'})

    # Определяем telegram_id
    if identifier.isdigit():
        telegram_id = int(identifier)
        username = f'user_{telegram_id}'
        first_name = f'User {telegram_id}'
    else:
        # Если username, удаляем @ если есть
        username = identifier.lstrip('@')
        # Генерируем псевдо-ID из username
        telegram_id = abs(hash(username)) % (10 ** 9)
        first_name = username

    # Ищем пользователя в БД
    user = get_user(telegram_id)

    if not user:
        # Создаём нового пользователя
        create_user(telegram_id, username, first_name)
        user = get_user(telegram_id)
        print(f"✅ Создан новый пользователь: {username} (ID: {telegram_id})")
    else:
        print(f"✅ Найден существующий пользователь: {username} (ID: {telegram_id})")

    # Сохраняем в сессию
    session['telegram_id'] = telegram_id
    session['username'] = username
    session['first_name'] = first_name

    return jsonify({
        'success': True,
        'telegram_id': telegram_id,
        'username': username,
        'first_name': first_name,
        'balance': user.get('balance', 0)
    })

@app.route('/process', methods=['POST'])
def process():
    print("=== Получен запрос на обработку ===")
    
    if 'photo' not in request.files:
        print("Ошибка: нет файла photo")
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        print("Ошибка: пустое имя файла")
        return jsonify({'error': 'Empty filename'}), 400
    
    edit_type = request.form.get('edit_type', 'random')
    custom_prompt = request.form.get('custom_prompt', '')
    
    print(f"Тип обработки: {edit_type}")
    print(f"Промпт: {custom_prompt}")
    print(f"Имя файла: {file.filename}")
    
    # Сохраняем оригинал
    filename = secure_filename(file.filename)
    task_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    saved_filename = f"{timestamp}_{task_id}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)
    
    print(f"Файл сохранен: {filepath}")
    
    # Создаем задачу
    tasks[task_id] = {
        'status': 'queued',
        'progress': 0,
        'filepath': filepath,
        'edit_type': edit_type,
        'custom_prompt': custom_prompt
    }
    
    # Запускаем обработку в отдельном потоке
    thread = threading.Thread(target=process_photo, args=(task_id, filepath, edit_type, custom_prompt))
    thread.daemon = True
    thread.start()
    
    print(f"Задача создана: {task_id}")
    
    return jsonify({'task_id': task_id, 'status': 'queued'})


@app.route('/api/history')
def api_history():
    """Возвращает историю обработок пользователя"""
    telegram_id = session.get('telegram_id')
    if not telegram_id:
        return jsonify({'history': []})

    history = get_user_history(telegram_id)
    return jsonify({'history': history})

@app.route('/status/<task_id>')
def get_status(task_id):
    print(f"Запрос статуса: {task_id}")
    
    if task_id not in tasks:
        print(f"Задача не найдена: {task_id}")
        return jsonify({'status': 'not_found'}), 404
    
    task = tasks[task_id]
    response = {
        'status': task['status'],
        'progress': task.get('progress', 0)
    }
    
    print(f"Статус задачи: {task['status']}, прогресс: {task.get('progress', 0)}")
    
    if task['status'] == 'completed':
        response['result_url'] = task.get('result_url')
        response['edit_type'] = task.get('edit_type')
        response['model_used'] = task.get('model_used')
    elif task['status'] == 'failed':
        response['error'] = task.get('error', 'Unknown error')
    
    return jsonify(response)

@app.route('/result/<filename>')
def get_result(filename):
    filepath = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)