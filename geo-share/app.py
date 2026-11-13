"""Consent-based, short-lived sharing of a phone's geolocation."""
import math
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, jsonify, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=43200, MAX_CONTENT_LENGTH=4096)
admin_password = os.environ.get('DASHBOARD_PASSWORD', '')
_lock = threading.Lock()
_locations = []
_attempts = {}
TTL = 24 * 60 * 60

def prune(now):
    _locations[:] = [item for item in _locations if now - item['ts'] < TTL]

def too_many(address):
    now = time.time()
    with _lock:
        values = [x for x in _attempts.get(address, []) if now-x < 600]
        if len(values) >= 8:
            _attempts[address] = values
            return True
        values.append(now)
        _attempts[address] = values
        return False

def only_owner(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('owner'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Permissions-Policy'] = 'geolocation=(self), camera=(), microphone=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    return response

@app.get('/')
def home():
    return render_template('index.html')

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/api/share')
def share():
    if request.headers.get('X-Requested-With') != 'geo-share' or not request.is_json:
        return jsonify(error='Некорректный запрос.'), 400
    if request.headers.get('Origin') and request.headers['Origin'].rstrip('/') != request.host_url.rstrip('/'):
        return jsonify(error='Недопустимый источник запроса.'), 403
    if too_many(request.remote_addr or 'unknown'):
        return jsonify(error='Слишком много отправок. Попробуйте позже.'), 429
    data = request.get_json(silent=True) or {}
    if data.get('consent') is not True:
        return jsonify(error='Необходимо явно подтвердить отправку.'), 400
    try:
        lat, lon, accuracy = float(data['latitude']), float(data['longitude']), float(data['accuracy'])
        if not all(math.isfinite(x) for x in (lat, lon, accuracy)) or not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= accuracy <= 100000):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        return jsonify(error='Некорректные координаты.'), 400
    now = time.time()
    with _lock:
        prune(now)
        _locations.insert(0, {'lat': round(lat, 7), 'lon': round(lon, 7), 'accuracy': round(accuracy), 'ts': now, 'datetime': datetime.fromtimestamp(now, timezone.utc).strftime('%d.%m.%Y %H:%M UTC')})
        del _locations[50:]
    return jsonify(ok=True, message='Местоположение отправлено владельцу ссылки.'), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        if too_many('login-'+(request.remote_addr or 'unknown')):
            error = 'Слишком много попыток. Попробуйте позже.'
        elif admin_password and secrets.compare_digest(request.form.get('password', ''), admin_password):
            session.clear()
            session['owner'] = True
            session.permanent = True
            return redirect(url_for('inbox'))
        else:
            error = 'Неверный пароль.'
    return render_template('login.html', error=error)

@app.get('/inbox')
@only_owner
def inbox():
    with _lock:
        prune(time.time())
        items = list(_locations)
    return render_template('inbox.html', items=items)

@app.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=False)
