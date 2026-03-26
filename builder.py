#!/usr/bin/env python3
"""
AETHER INJECTOR VIP v6.0 - FULL BUILDER
Run: python builder.py
"""

import os
import sys
import json
import uuid
import time
import shutil
import zipfile
import secrets
import datetime
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from functools import wraps
import bcrypt

# ==================== CONFIGURATION ====================
APP_VERSION = "6.0.0"
BASE_DIR = Path(__file__).parent
BUILD_DIR = BASE_DIR / "build"
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cheat_injector.db"

# Create directories
for d in [BUILD_DIR, OUTPUT_DIR, TEMPLATES_DIR, DATA_DIR]:
    d.mkdir(exist_ok=True)

# ==================== DATABASE ====================
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id TEXT UNIQUE NOT NULL,
            app_name TEXT NOT NULL,
            customer_name TEXT,
            customer_email TEXT,
            license_key TEXT UNIQUE NOT NULL,
            expiry_date DATETIME NOT NULL,
            selected_cheats TEXT,
            apk_path TEXT,
            download_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cheats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            risk_level TEXT,
            category TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            device_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode()
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ('admin', password_hash)
        )
        print("[✓] Default admin created: admin / admin")
    
    cursor.execute("SELECT * FROM cheats")
    if not cursor.fetchone():
        cheats = [
            ('mlbb', 'Wall Hack ESP', 'Lihat posisi musuh di balik tembok', 'low', 'visual'),
            ('mlbb', 'Map Hack', 'Seluruh peta terlihat', 'medium', 'visual'),
            ('mlbb', 'No Cooldown', 'Skill tanpa cooldown', 'extreme', 'combat'),
            ('mlbb', 'Damage Multiplier x10', 'Damage 10x lipat', 'extreme', 'combat'),
            ('mlbb', 'God Mode', 'HP tidak berkurang', 'extreme', 'defense'),
            ('mlbb', 'Auto Aim', 'Skill auto target musuh', 'high', 'combat'),
            ('mlbb', 'Speed Hack 2x', 'Gerakan 2x lebih cepat', 'extreme', 'movement'),
            ('mlbb', 'Anti-CC', 'Tidak bisa di-stun/slow', 'medium', 'defense'),
            ('mlbb', 'Skin Unlocker All', 'Semua skin terbuka', 'low', 'cosmetic'),
            ('mlbb', 'Drone View', 'Kamera 360° lihat arena', 'medium', 'camera'),
            ('freefire', 'Wall Hack Yellow ESP', 'Musuh berwarna kuning, tembus tembok', 'medium', 'visual'),
            ('freefire', 'Aimbot Headshot', 'Auto aim ke kepala musuh', 'high', 'combat'),
            ('freefire', 'No Recoil', 'Senjata tanpa getaran', 'medium', 'combat'),
            ('freefire', 'Magic Bullet', 'Peluru auto bidik', 'high', 'combat'),
            ('freefire', 'Fly Hack', 'Terbang di udara', 'extreme', 'movement'),
            ('freefire', 'Damage Hack x5', 'Damage 5x lipat', 'extreme', 'combat'),
            ('freefire', 'ESP Player', 'Lihat nama, HP, jarak musuh', 'medium', 'visual'),
            ('freefire', 'No Grass', 'Semua rumput hilang', 'medium', 'visual'),
            ('freefire', 'Speed Hack', 'Gerakan 50% lebih cepat', 'high', 'movement'),
            ('freefire', 'Unlimited Ammo', 'Ammo tidak pernah habis', 'medium', 'resource'),
        ]
        for cheat in cheats:
            cursor.execute("""
                INSERT INTO cheats (game, name, description, risk_level, category, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, cheat)
        print(f"[✓] Seeded {len(cheats)} cheats")
    
    conn.commit()
    conn.close()

# ==================== FLASK ADMIN PANEL ====================
app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_license_key():
    import random
    import string
    parts = []
    for _ in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        parts.append(part)
    return '-'.join(parts)

# ==================== ROUTES ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        admin = cursor.fetchone()
        conn.close()
        
        if admin and bcrypt.checkpw(password.encode(), admin['password_hash'].encode()):
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = admin['id']
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
@admin_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM apps")
    total_apps = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM apps WHERE is_active = 1")
    active_apps = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM cheats WHERE is_active = 1")
    total_cheats = cursor.fetchone()['count']
    cursor.execute("SELECT * FROM apps ORDER BY created_at DESC LIMIT 5")
    recent_apps = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard.html', 
                         total_apps=total_apps,
                         active_apps=active_apps,
                         total_cheats=total_cheats,
                         recent_apps=recent_apps)

@app.route('/apps')
@admin_required
def apps_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apps ORDER BY created_at DESC")
    apps = cursor.fetchall()
    conn.close()
    return render_template('apps.html', apps=apps, now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/app/create', methods=['GET', 'POST'])
@admin_required
def create_app():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cheats WHERE is_active = 1")
    all_cheats = cursor.fetchall()
    conn.close()
    
    mlbb_cheats = [c for c in all_cheats if c['game'] == 'mlbb']
    ff_cheats = [c for c in all_cheats if c['game'] == 'freefire']
    
    if request.method == 'POST':
        app_name = request.form.get('app_name')
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        expiry_days = int(request.form.get('expiry_days', 30))
        selected_cheats = request.form.getlist('cheats')
        
        app_id = str(uuid.uuid4())[:8]
        license_key = generate_license_key()
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get cheat names for storage
        cheat_names = []
        for cheat_id in selected_cheats:
            cursor.execute("SELECT name FROM cheats WHERE id = ?", (cheat_id,))
            c = cursor.fetchone()
            if c:
                cheat_names.append(c['name'])
        
        cursor.execute("""
            INSERT INTO apps (app_id, app_name, customer_name, customer_email, 
                            license_key, expiry_date, selected_cheats, apk_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (app_id, app_name, customer_name, customer_email, 
              license_key, expiry_date, json.dumps(cheat_names), ""))
        conn.commit()
        conn.close()
        
        flash(f'App created! License: {license_key}', 'success')
        return redirect(url_for('apps_list'))
    
    return render_template('create_app.html', mlbb_cheats=mlbb_cheats, ff_cheats=ff_cheats)

@app.route('/app/delete/<app_id>')
@admin_required
def delete_app(app_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apps WHERE app_id = ?", (app_id,))
    conn.commit()
    conn.close()
    flash('App deleted', 'success')
    return redirect(url_for('apps_list'))

@app.route('/cheats')
@admin_required
def cheats_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cheats WHERE game = 'mlbb'")
    mlbb_cheats = cursor.fetchall()
    cursor.execute("SELECT * FROM cheats WHERE game = 'freefire'")
    ff_cheats = cursor.fetchall()
    conn.close()
    return render_template('cheats.html', mlbb_cheats=mlbb_cheats, ff_cheats=ff_cheats)

@app.route('/cheat/toggle/<int:cheat_id>', methods=['POST'])
@admin_required
def toggle_cheat(cheat_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM cheats WHERE id = ?", (cheat_id,))
    current = cursor.fetchone()
    new_status = 0 if current['is_active'] else 1
    cursor.execute("UPDATE cheats SET is_active = ? WHERE id = ?", (new_status, cheat_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'is_active': new_status})

@app.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if new_password:
            password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE admins SET password_hash = ? WHERE username = ?", 
                         (password_hash, session['username']))
            conn.commit()
            conn.close()
            flash('Password updated', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html')

@app.route('/api/verify_license', methods=['POST'])
def verify_license():
    data = request.json
    license_key = data.get('license_key', '')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT app_name, customer_name, expiry_date, is_active 
        FROM apps 
        WHERE license_key = ?
    """, (license_key,))
    app_data = cursor.fetchone()
    conn.close()
    
    if not app_data:
        return jsonify({'valid': False, 'error': 'License not found'})
    
    if app_data['is_active'] != 1:
        return jsonify({'valid': False, 'error': 'License deactivated'})
    
    expiry = datetime.datetime.strptime(app_data['expiry_date'], '%Y-%m-%d %H:%M:%S')
    if expiry < datetime.datetime.now():
        return jsonify({'valid': False, 'error': 'License expired'})
    
    return jsonify({
        'valid': True,
        'app_name': app_data['app_name'],
        'customer_name': app_data['customer_name'],
        'expiry_date': app_data['expiry_date']
    })

# ==================== TEMPLATES ====================
def create_templates():
    # login.html
    with open(TEMPLATES_DIR / 'login.html', 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Aether Injector</title>
    <style>
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: system-ui, -apple-system, sans-serif;
        }
        .login-card {
            background: rgba(10,10,26,0.95);
            border: 1px solid #0f0;
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }
        .login-card h2 {
            color: #0f0;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-control {
            background: #1a1a2e;
            border: 1px solid #0f0;
            color: #0f0;
            padding: 12px;
            width: 100%;
            margin-bottom: 15px;
            border-radius: 10px;
        }
        .btn {
            background: #0f0;
            color: #000;
            font-weight: bold;
            padding: 12px;
            width: 100%;
            border: none;
            border-radius: 10px;
            cursor: pointer;
        }
        .alert {
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        .alert-success { background: #0a3; color: #fff; }
        .alert-danger { background: #f33; color: #fff; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>⚡ AETHER INJECTOR</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" class="form-control" placeholder="Username" required>
            <input type="password" name="password" class="form-control" placeholder="Password" required>
            <button type="submit" class="btn">LOGIN</button>
        </form>
    </div>
</body>
</html>''')
    
    # base.html
    with open(TEMPLATES_DIR / 'base.html', 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aether Injector Admin</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            font-family: system-ui, sans-serif;
        }
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 260px;
            height: 100%;
            background: #0a0a1a;
            border-right: 1px solid #0f0;
            padding: 20px;
        }
        .sidebar h3 {
            color: #0f0;
            text-align: center;
            margin-bottom: 30px;
        }
        .sidebar a {
            display: block;
            color: #ccc;
            text-decoration: none;
            padding: 12px 15px;
            margin: 5px 0;
            border-radius: 10px;
        }
        .sidebar a:hover, .sidebar a.active {
            background: #1a1a2e;
            color: #0f0;
        }
        .main-content {
            margin-left: 260px;
            padding: 20px;
        }
        .card {
            background: #0a0a1a;
            border: 1px solid #0f0;
            border-radius: 15px;
            margin-bottom: 20px;
            padding: 20px;
        }
        .card-header {
            border-bottom: 1px solid #0f0;
            padding-bottom: 10px;
            margin-bottom: 15px;
            color: #0f0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #333;
            color: #fff;
        }
        th {
            color: #0f0;
        }
        .btn {
            padding: 5px 12px;
            border-radius: 5px;
            text-decoration: none;
            display: inline-block;
        }
        .btn-success {
            background: #0f0;
            color: #000;
        }
        .btn-danger {
            background: #f33;
            color: #fff;
        }
        .alert {
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .alert-success { background: #0a3; color: #fff; }
        .alert-danger { background: #f33; color: #fff; }
        .status-active {
            background: #0a3;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
        }
        .status-expired {
            background: #f33;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>⚡ AETHER</h3>
        <a href="{{ url_for('dashboard') }}" class="{% if request.endpoint == 'dashboard' %}active{% endif %}">Dashboard</a>
        <a href="{{ url_for('apps_list') }}" class="{% if request.endpoint == 'apps_list' %}active{% endif %}">Apps</a>
        <a href="{{ url_for('create_app') }}" class="{% if request.endpoint == 'create_app' %}active{% endif %}">Create App</a>
        <a href="{{ url_for('cheats_list') }}" class="{% if request.endpoint == 'cheats_list' %}active{% endif %}">Cheats</a>
        <a href="{{ url_for('settings') }}" class="{% if request.endpoint == 'settings' %}active{% endif %}">Settings</a>
        <a href="{{ url_for('logout') }}" style="color:#f33; margin-top:30px;">Logout</a>
    </div>
    <div class="main-content">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>''')
    
    # dashboard.html
    with open(TEMPLATES_DIR / 'dashboard.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<div style="display: flex; gap: 20px; margin-bottom: 30px;">
    <div class="card" style="flex:1; text-align:center;">
        <h2 style="color:#0f0">{{ total_apps }}</h2>
        <p>Total Apps</p>
    </div>
    <div class="card" style="flex:1; text-align:center;">
        <h2 style="color:#0f0">{{ active_apps }}</h2>
        <p>Active Licenses</p>
    </div>
    <div class="card" style="flex:1; text-align:center;">
        <h2 style="color:#0f0">{{ total_cheats }}</h2>
        <p>Cheats Available</p>
    </div>
</div>
<div class="card">
    <div class="card-header">Recent Apps</div>
    <table>
        <thead>
            <tr><th>App Name</th><th>Customer</th><th>License</th><th>Expiry</th><th>Downloads</th></tr>
        </thead>
        <tbody>
            {% for app in recent_apps %}
            <tr>
                <td>{{ app.app_name }}</td>
                <td>{{ app.customer_name }}</td>
                <td><code>{{ app.license_key }}</code></td>
                <td>{{ app.expiry_date[:10] }}</td>
                <td>{{ app.download_count }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}''')
    
    # apps.html
    with open(TEMPLATES_DIR / 'apps.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
    <h2 style="color:#0f0">Customer Apps</h2>
    <a href="{{ url_for('create_app') }}" class="btn btn-success">+ Create New App</a>
</div>
<div class="card">
    <table>
        <thead>
            <tr><th>App Name</th><th>Customer</th><th>License</th><th>Expiry</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
            {% for app in apps %}
            <tr>
                <td>{{ app.app_name }}</td>
                <td>{{ app.customer_name }}</td>
                <td><code>{{ app.license_key }}</code></td>
                <td>{{ app.expiry_date[:10] }}</td>
                <td>{% if app.is_active == 1 %}<span class="status-active">Active</span>{% else %}<span class="status-expired">Expired</span>{% endif %}</td>
                <td>
                    <a href="{{ url_for('delete_app', app_id=app.app_id) }}" class="btn btn-danger" onclick="return confirm('Delete?')">Delete</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}''')
    
    # create_app.html
    with open(TEMPLATES_DIR / 'create_app.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<h2 style="color:#0f0; margin-bottom:20px;">Create New App</h2>
<div style="display: flex; gap: 20px;">
    <div class="card" style="flex:1;">
        <form method="POST">
            <div style="margin-bottom:15px;">
                <label style="color:#0f0">App Name</label>
                <input type="text" name="app_name" style="width:100%; padding:10px; background:#1a1a2e; border:1px solid #0f0; color:#0f0; border-radius:8px;" required>
            </div>
            <div style="margin-bottom:15px;">
                <label style="color:#0f0">Customer Name</label>
                <input type="text" name="customer_name" style="width:100%; padding:10px; background:#1a1a2e; border:1px solid #0f0; color:#0f0; border-radius:8px;" required>
            </div>
            <div style="margin-bottom:15px;">
                <label style="color:#0f0">Customer Email</label>
                <input type="email" name="customer_email" style="width:100%; padding:10px; background:#1a1a2e; border:1px solid #0f0; color:#0f0; border-radius:8px;">
            </div>
            <div style="margin-bottom:15px;">
                <label style="color:#0f0">Expiry Days</label>
                <input type="number" name="expiry_days" value="30" style="width:100%; padding:10px; background:#1a1a2e; border:1px solid #0f0; color:#0f0; border-radius:8px;">
            </div>
            <button type="submit" class="btn btn-success" style="width:100%;">CREATE APP</button>
        </form>
    </div>
    <div class="card" style="flex:2;">
        <div class="card-header">Select Cheats</div>
        <div style="display: flex; gap: 20px;">
            <div style="flex:1;">
                <h4 style="color:#ffaa00">⚔️ Mobile Legends</h4>
                {% for cheat in mlbb_cheats %}
                <div style="margin:8px 0;">
                    <input type="checkbox" name="cheats" value="{{ cheat.id }}" id="chk_{{ cheat.id }}">
                    <label for="chk_{{ cheat.id }}" style="color:#fff">{{ cheat.name }}</label>
                    <span style="color:#{{ 'f33' if cheat.risk_level == 'extreme' else 'fa0' if cheat.risk_level == 'high' else '0f0' }}">({{ cheat.risk_level }})</span>
                </div>
                {% endfor %}
            </div>
            <div style="flex:1;">
                <h4 style="color:#ffaa00">🔥 Free Fire</h4>
                {% for cheat in ff_cheats %}
                <div style="margin:8px 0;">
                    <input type="checkbox" name="cheats" value="{{ cheat.id }}" id="chk_{{ cheat.id }}">
                    <label for="chk_{{ cheat.id }}" style="color:#fff">{{ cheat.name }}</label>
                    <span style="color:#{{ 'f33' if cheat.risk_level == 'extreme' else 'fa0' if cheat.risk_level == 'high' else '0f0' }}">({{ cheat.risk_level }})</span>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}''')
    
    # cheats.html
    with open(TEMPLATES_DIR / 'cheats.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<h2 style="color:#0f0; margin-bottom:20px;">Cheats Database</h2>
<div style="display: flex; gap: 20px;">
    <div class="card" style="flex:1;">
        <div class="card-header">⚔️ Mobile Legends</div>
        <table>
            <thead><tr><th>Name</th><th>Risk</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
                {% for cheat in mlbb_cheats %}
                <tr>
                    <td>{{ cheat.name }}</td>
                    <td><span style="color:#{{ 'f33' if cheat.risk_level == 'extreme' else 'fa0' if cheat.risk_level == 'high' else '0f0' }}">{{ cheat.risk_level }}</span></td>
                    <td>{% if cheat.is_active %}✅ Active{% else %}❌ Disabled{% endif %}</td>
                    <td><button class="btn btn-success toggle-cheat" data-id="{{ cheat.id }}" style="padding:3px 10px;">Toggle</button></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <div class="card" style="flex:1;">
        <div class="card-header">🔥 Free Fire</div>
        <table>
            <thead><tr><th>Name</th><th>Risk</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
                {% for cheat in ff_cheats %}
                <tr>
                    <td>{{ cheat.name }}</td>
                    <td><span style="color:#{{ 'f33' if cheat.risk_level == 'extreme' else 'fa0' if cheat.risk_level == 'high' else '0f0' }}">{{ cheat.risk_level }}</span></td>
                    <td>{% if cheat.is_active %}✅ Active{% else %}❌ Disabled{% endif %}</td>
                    <td><button class="btn btn-success toggle-cheat" data-id="{{ cheat.id }}" style="padding:3px 10px;">Toggle</button></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
<script>
document.querySelectorAll('.toggle-cheat').forEach(btn => {
    btn.addEventListener('click', async function() {
        const id = this.dataset.id;
        const resp = await fetch('/cheat/toggle/' + id, {method: 'POST'});
        if (resp.ok) location.reload();
    });
});
</script>
{% endblock %}''')
    
    # settings.html
    with open(TEMPLATES_DIR / 'settings.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<h2 style="color:#0f0; margin-bottom:20px;">Settings</h2>
<div class="card">
    <div class="card-header">Change Password</div>
    <form method="POST">
        <div style="margin-bottom:15px;">
            <label style="color:#0f0">New Password</label>
            <input type="password" name="new_password" style="width:100%; padding:10px; background:#1a1a2e; border:1px solid #0f0; color:#0f0; border-radius:8px;" required>
        </div>
        <button type="submit" class="btn btn-success">Update Password</button>
    </form>
</div>
<div class="card">
    <div class="card-header">System Info</div>
    <p><strong>Version:</strong> 6.0.0</p>
    <p><strong>Database:</strong> {{ db_path }}</p>
    <p><strong>Default Login:</strong> admin / admin</p>
</div>
{% endblock %}''')
    
    print("[✓] Templates created")

# ==================== MAIN ====================
def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                AETHER INJECTOR VIP v6.0                      ║
    ║                  Admin Panel Starting                        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    init_db()
    create_templates()
    
    print("[✓] Database initialized")
    print("[✓] Templates ready")
    print("")
    print("🔗 Admin Panel: http://localhost:5000")
    print("🔑 Default Login: admin / admin")
    print("")
    print("⚠️  For production, change the default password!")
    print("")
    print("Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
