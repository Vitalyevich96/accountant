from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

DATA_FOLDER = 'data'
ADMIN_LOGIN = 'admin'
ADMIN_PASSWORD = 'admin1802'

@app.template_filter('tojson')
def to_json_filter(value):
    return json.dumps(value, ensure_ascii=False)

# Конфигурация услуг
SERVICES = {
    'bookkeeping': {
        'name': 'Ведение бухгалтерии',
        'price_range': 'от 50 000 тенге/месяц',
        'description': 'Полное ведение бухгалтерского и налогового учета'
    },
    'tax_consulting': {
        'name': 'Налоговое консультирование',
        'price_range': 'от 15 000 тенге',
        'description': 'Оптимизация налоговой нагрузки и консультации'
    },
    'reporting': {
        'name': 'Сдача отчетности',
        'price_range': 'от 10 000 тенге',
        'description': 'Подготовка и сдача всей необходимой отчетности'
    },
    'audit': {
        'name': 'Аудит',
        'price_range': 'от 100 000 тенге',
        'description': 'Проверка бухгалтерской и налоговой отчетности'
    },
    'registration': {
        'name': 'Регистрация бизнеса',
        'price_range': 'от 40 000 тенге',
        'description': 'Регистрация ИП и ООО под ключ'
    },
    'salary': {
        'name': 'Расчет заработной платы',
        'price_range': 'от 20 000 тенге/месяц',
        'description': 'Расчет зарплаты, налогов и взносов'
    }
}

def ensure_data_folder():
    """Создать папку data если её нет"""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

def get_filename(year, month):
    """Получить имя файла для месяца"""
    ensure_data_folder()
    return os.path.join(DATA_FOLDER, f'requests_{year}_{month:02d}.json')

def get_current_month_year():
    """Получить текущий месяц и год"""
    now = datetime.now()
    return now.year, now.month

def load_requests(year=None, month=None):
    """Загрузить заявки из файла"""
    if year is None or month is None:
        year, month = get_current_month_year()
    
    filename = get_filename(year, month)
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_all_requests():
    """Загрузить все заявки из всех файлов"""
    ensure_data_folder()
    all_requests = []
    
    for filename in sorted(os.listdir(DATA_FOLDER)):
        if filename.startswith('requests_') and filename.endswith('.json'):
            filepath = os.path.join(DATA_FOLDER, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                month_requests = json.load(f)
                all_requests.extend(month_requests)
    
    return all_requests


def save_requests(requests_list, year=None, month=None):
    """Сохранить заявки в файл"""
    if year is None or month is None:
        year, month = get_current_month_year()
    
    ensure_data_folder()
    filename = get_filename(year, month)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(requests_list, f, ensure_ascii=False, indent=2)

def get_available_months():
    """Получить список доступных месяцев с заявками"""
    ensure_data_folder()
    months = []
    
    for filename in sorted(os.listdir(DATA_FOLDER), reverse=True):
        if filename.startswith('requests_') and filename.endswith('.json'):
            parts = filename.replace('requests_', '').replace('.json', '').split('_')
            if len(parts) == 2:
                year, month = int(parts[0]), int(parts[1])
                months.append((year, month))
    
    return months

def load_clients():
    """Загрузить базу клиентов"""
    filename = os.path.join(DATA_FOLDER, 'clients.json')
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_clients(clients):
    """Сохранить базу клиентов"""
    ensure_data_folder()
    filename = os.path.join(DATA_FOLDER, 'clients.json')
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Пожалуйста, выполните вход', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', services=SERVICES)

@app.route('/services')
def services():
    """Страница с описанием услуг"""
    return render_template('services.html', services=SERVICES)

@app.route('/consultation', methods=['GET', 'POST'])
def consultation():
    """Страница заявки на консультацию"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        service_type = request.form.get('service_type', '').strip()
        company_type = request.form.get('company_type', '').strip()
        message = request.form.get('message', '').strip()
        urgency = request.form.get('urgency', 'standard')
        
        if not all([name, email, phone, service_type]):
            flash('Пожалуйста, заполните все обязательные поля', 'error')
            return redirect(url_for('consultation'))
        
        # Добавляем в базу клиентов
        clients = load_clients()
        client_exists = False
        client_id = None

        for client in clients:
            if client['email'] == email:
                client_exists = True
                client_id = client['id']
                # Обновляем счетчик заявок
                client['requests_count'] = client.get('requests_count', 1) + 1
                break

        if not client_exists:
            client_id = str(uuid.uuid4())
            new_client = {
                'id': client_id,
                'name': name,
                'email': email,
                'phone': phone,
                'company_type': company_type,
                'created_date': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'requests_count': 1
            }
            clients.append(new_client)

        save_clients(clients)
        
        # Сохраняем заявку
        year, month = get_current_month_year()
        requests_list = load_requests(year, month)
        
        new_request = {
            'id': len(requests_list) + 1,
            'client_id': client_id,
            'name': name,
            'email': email,
            'phone': phone,
            'service_type': service_type,
            'company_type': company_type,
            'message': message,
            'urgency': urgency,
            'date': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'status': 'новая',
            'assigned_to': '',
            'notes': ''
        }
        requests_list.append(new_request)
        save_requests(requests_list, year, month)
        
        flash('Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('consultation'))
    
    return render_template('consultation.html', services=SERVICES)

@app.route('/pricing')
def pricing():
    """Страница с ценами"""
    return render_template('pricing.html', services=SERVICES)

@app.route('/about')
def about():
    """Страница о компании"""
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в админ панель"""
    if request.method == 'POST':
        login_input = request.form.get('login', '').strip()
        password_input = request.form.get('password', '').strip()
        
        if login_input == ADMIN_LOGIN and password_input == ADMIN_PASSWORD:
            session['user'] = ADMIN_LOGIN
            flash('Вы успешно вошли', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Неверные учетные данные', 'error')
    
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_panel():
    """Админ панель с заявками"""
    status_filter = request.args.get('status', '')
    
    # Загружаем все заявки из всех месяцев
    requests_list = load_all_requests()
    
    # Фильтрация по статусу
    if status_filter:
        requests_list = [r for r in requests_list if r['status'] == status_filter]
    
    # Сортируем по дате в обратном порядке (новые сверху)
    requests_list.sort(key=lambda x: datetime.strptime(x['date'], '%d.%m.%Y %H:%M:%S'), reverse=True)
    
    # Статистика
    stats = {
        'total': len(requests_list),
        'new': len([r for r in requests_list if r['status'] == 'новая']),
        'in_progress': len([r for r in requests_list if r['status'] == 'в_процессе']),
        'completed': len([r for r in requests_list if r['status'] == 'завершена'])
    }
    
    return render_template('admin.html', 
                         requests=requests_list,
                         stats=stats,
                         status_filter=status_filter,
                         services=SERVICES)
@app.route('/admin/delete/<int:request_id>', methods=['POST'])
@login_required
def delete_request(request_id):
    """Удалить заявку"""
    # Ищем заявку во всех файлах
    available_months = get_available_months()
    
    for year, month in available_months:
        requests_list = load_requests(year, month)
        for req in requests_list:
            if req['id'] == request_id:
                # Удаляем заявку из этого месяца
                requests_list = [r for r in requests_list if r['id'] != request_id]
                save_requests(requests_list, year, month)
                flash('Заявка удалена', 'success')
                return redirect(url_for('admin_panel'))
    
    flash('Заявка не найдена', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/admin/update-status/<int:request_id>/<status>', methods=['POST'])
@login_required
def update_status(request_id, status):
    """Обновить статус заявки"""
    valid_statuses = ['новая', 'в_процессе', 'завершена']
    if status not in valid_statuses:
        flash('Неверный статус', 'error')
        return redirect(url_for('admin_panel'))
    
    # Ищем заявку во всех файлах
    available_months = get_available_months()
    
    for year, month in available_months:
        requests_list = load_requests(year, month)
        for req in requests_list:
            if req['id'] == request_id:
                # Обновляем статус в этом месяце
                req['status'] = status
                save_requests(requests_list, year, month)
                flash('Статус обновлен', 'success')
                return redirect(url_for('admin_panel'))
    
    flash('Заявка не найдена', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/admin/add-note/<int:request_id>', methods=['POST'])
@login_required
def add_note(request_id):
    """Добавить заметку к заявке"""
    note = request.form.get('note', '').strip()
    
    # Ищем заявку во всех файлах
    available_months = get_available_months()
    
    for year, month in available_months:
        requests_list = load_requests(year, month)
        for req in requests_list:
            if req['id'] == request_id:
                req['notes'] = note
                save_requests(requests_list, year, month)
                flash('Заметка добавлена', 'success')
                return redirect(url_for('admin_panel'))
    
    flash('Заявка не найдена', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/admin/assign-to/<int:request_id>', methods=['POST'])
@login_required
def assign_request(request_id):
    """Назначить заявку сотруднику"""
    assigned_to = request.form.get('assigned_to', '').strip()
    
    # Ищем заявку во всех файлах
    available_months = get_available_months()
    
    for year, month in available_months:
        requests_list = load_requests(year, month)
        for req in requests_list:
            if req['id'] == request_id:
                req['assigned_to'] = assigned_to
                save_requests(requests_list, year, month)
                flash('Заявка назначена', 'success')
                return redirect(url_for('admin_panel'))
    
    flash('Заявка не найдена', 'error')
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    """Выход из админ панели"""
    session.pop('user', None)
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

@app.route('/admin/export/<int:year>/<int:month>')
@login_required
def export_requests(year, month):
    """Экспорт заявок в CSV"""
    import csv
    from io import StringIO
    
    requests_list = load_requests(year, month)
    
    if not requests_list:
        flash('Нет данных для экспорта', 'error')
        return redirect(url_for('admin_panel', year=year, month=month))
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['ID', 'Имя', 'Email', 'Телефон', 'Услуга', 'Тип компании', 'Сообщение', 'Дата', 'Статус'])
    
    # Данные
    for req in requests_list:
        writer.writerow([
            req['id'],
            req['name'],
            req['email'],
            req['phone'],
            req.get('service_type', ''),
            req.get('company_type', ''),
            req['message'],
            req['date'],
            req['status']
        ])
    
    from flask import Response
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=requests_{year}_{month:02d}.csv"}
    )

@app.route('/api/stats')
@login_required
def api_stats():
    """API для статистики"""
    current_year, current_month = get_current_month_year()
    requests_list = load_requests(current_year, current_month)
    clients = load_clients()
    
    stats = {
        'requests': {
            'total': len(requests_list),
            'new': len([r for r in requests_list if r['status'] == 'новая']),
            'in_progress': len([r for r in requests_list if r['status'] == 'в_процессе']),
            'completed': len([r for r in requests_list if r['status'] == 'завершена'])
        },
        'clients': {
            'total': len(clients),
            'recurring': len([c for c in clients if c.get('requests_count', 0) > 1])
        }
    }
    
    return jsonify(stats)

from flask import send_from_directory

# Добавьте этот маршрут для favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Добавить обработку ошибок
@app.errorhandler(404)
def not_found_error(error):
    if request.path == '/favicon.ico':
        # Для favicon возвращаем пустой ответ вместо ошибки 404
        return '', 204
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return """
    <html>
        <head><title>Ошибка сервера</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #dc3545;">500 - Ошибка сервера</h1>
            <p>Произошла внутренняя ошибка сервера. Пожалуйста, попробуйте позже.</p>
            <a href="/" style="color: #007bff;">Вернуться на главную</a>
        </body>
    </html>
    """, 500

from flask import send_from_directory

@app.route('/googleddd09674c4d97235.html')
def google_verification():
    return send_from_directory('.', 'googleddd09674c4d97235.html')

@app.route('/yandex_d94254384d1d67c8.html')
def yandex_verification():
    return send_from_directory('.', 'yandex_d94254384d1d67c8.html')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt')

if __name__ == '__main__':
    app.run(debug=True)
