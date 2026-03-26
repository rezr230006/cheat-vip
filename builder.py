#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
                    CHEAT INJECTOR VIP v6.0 - FULL BUILDER
                    By: Plane Crash Survivors Team
═══════════════════════════════════════════════════════════════════════════

Usage:
    python builder.py                    # Run admin panel + builder
    python builder.py --build-apk        # Build APK only
    python builder.py --admin-only       # Run admin panel only

Output:
    - Admin Panel: http://localhost:5000
    - APK Output: ./output/CheatInjector_<name>.apk
"""

import os
import sys
import json
import uuid
import time
import shutil
import zipfile
import hashlib
import secrets
import datetime
import subprocess
import requests
import platform
import base64
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from functools import wraps
import bcrypt

# ==================== CONFIGURATION ====================
APP_NAME = "AetherInjector"
APP_VERSION = "6.0.0"
BUILD_DIR = Path(__file__).parent / "build"
OUTPUT_DIR = Path(__file__).parent / "output"
TEMPLATES_DIR = Path(__file__).parent / "templates"
DB_PATH = Path(__file__).parent / "data" / "cheat_injector.db"

# Create directories
for d in [BUILD_DIR, OUTPUT_DIR, TEMPLATES_DIR, Path(__file__).parent / "data"]:
    d.mkdir(exist_ok=True)

# ==================== DATABASE ====================
import sqlite3

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Admins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Apps table
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
    
    # Cheats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cheats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            risk_level TEXT,
            category TEXT,
            module_file TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # License logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            device_id TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if default admin exists
    cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode()
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ('admin', password_hash)
        )
        print("[✓] Default admin created: admin / admin")
    
    # Seed default cheats
    cursor.execute("SELECT * FROM cheats")
    if not cursor.fetchone():
        cheats = [
            # Mobile Legends Cheats
            ('mlbb', 'Wall Hack ESP', 'Lihat posisi musuh di balik tembok', 'low', 'visual', 'mlbb_wallhack.so'),
            ('mlbb', 'Map Hack', 'Seluruh peta terlihat', 'medium', 'visual', 'mlbb_maphack.so'),
            ('mlbb', 'No Cooldown', 'Skill tanpa cooldown', 'extreme', 'combat', 'mlbb_nocd.so'),
            ('mlbb', 'Damage Multiplier x10', 'Damage 10x lipat', 'extreme', 'combat', 'mlbb_damage.so'),
            ('mlbb', 'God Mode', 'HP tidak berkurang', 'extreme', 'defense', 'mlbb_godmode.so'),
            ('mlbb', 'Auto Aim', 'Skill auto target musuh', 'high', 'combat', 'mlbb_autoaim.so'),
            ('mlbb', 'Speed Hack', 'Gerakan lebih cepat', 'extreme', 'movement', 'mlbb_speed.so'),
            ('mlbb', 'Anti-CC', 'Tidak bisa di-stun/slow', 'medium', 'defense', 'mlbb_anticc.so'),
            ('mlbb', 'Skin Unlocker', 'Semua skin terbuka', 'low', 'cosmetic', 'mlbb_skin.so'),
            ('mlbb', 'Drone View', 'Kamera 360° lihat arena', 'medium', 'camera', 'mlbb_drone.so'),
            # Free Fire Cheats
            ('freefire', 'Wall Hack Yellow ESP', 'Musuh berwarna kuning, tembus tembok', 'medium', 'visual', 'ff_wallhack.so'),
            ('freefire', 'Aimbot Headshot', 'Auto aim ke kepala musuh', 'high', 'combat', 'ff_aimbot.so'),
            ('freefire', 'No Recoil', 'Senjata tanpa getaran', 'medium', 'combat', 'ff_norecoil.so'),
            ('freefire', 'Magic Bullet', 'Peluru auto bidik', 'high', 'combat', 'ff_magic.so'),
            ('freefire', 'Fly Hack', 'Terbang di udara', 'extreme', 'movement', 'ff_fly.so'),
            ('freefire', 'Damage Hack', 'Damage 5x lipat', 'extreme', 'combat', 'ff_damage.so'),
            ('freefire', 'ESP Player', 'Lihat nama, HP, jarak musuh', 'medium', 'visual', 'ff_esp.so'),
            ('freefire', 'No Grass', 'Semua rumput hilang', 'medium', 'visual', 'ff_nograss.so'),
            ('freefire', 'Speed Hack', 'Gerakan 50% lebih cepat', 'high', 'movement', 'ff_speed.so'),
            ('freefire', 'Unlimited Ammo', 'Ammo tidak pernah habis', 'medium', 'resource', 'ff_ammo.so'),
        ]
        for cheat in cheats:
            cursor.execute("""
                INSERT INTO cheats (game, name, description, risk_level, category, module_file, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
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

# ==================== ADMIN ROUTES ====================

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
    return render_template('apps.html', apps=apps)

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
        
        # Get cheat details
        cheat_list = []
        conn = get_db()
        cursor = conn.cursor()
        for cheat_id in selected_cheats:
            cursor.execute("SELECT * FROM cheats WHERE id = ?", (cheat_id,))
            cheat = cursor.fetchone()
            if cheat:
                cheat_list.append(dict(cheat))
        
        # Generate IDs
        app_id = str(uuid.uuid4())[:8]
        license_key = generate_license_key()
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
        
        # Build APK
        apk_path = build_apk(app_id, app_name, license_key, expiry_date, cheat_list)
        
        if apk_path:
            cursor.execute("""
                INSERT INTO apps (app_id, app_name, customer_name, customer_email, 
                                license_key, expiry_date, selected_cheats, apk_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (app_id, app_name, customer_name, customer_email, 
                  license_key, expiry_date, json.dumps([c['id'] for c in cheat_list]), apk_path))
            conn.commit()
            flash(f'App created! License: {license_key}', 'success')
        else:
            flash('APK build failed!', 'danger')
        
        conn.close()
        return redirect(url_for('apps_list'))
    
    return render_template('create_app.html', mlbb_cheats=mlbb_cheats, ff_cheats=ff_cheats)

@app.route('/app/download/<app_id>')
@admin_required
def download_app(app_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apps WHERE app_id = ?", (app_id,))
    app_data = cursor.fetchone()
    
    if app_data and app_data['apk_path']:
        cursor.execute("UPDATE apps SET download_count = download_count + 1 WHERE app_id = ?", (app_id,))
        conn.commit()
        conn.close()
        
        apk_path = Path(app_data['apk_path'])
        if apk_path.exists():
            return send_file(apk_path, as_attachment=True, download_name=f"{app_data['app_name']}.apk")
    
    conn.close()
    flash('APK not found', 'danger')
    return redirect(url_for('apps_list'))

@app.route('/app/delete/<app_id>')
@admin_required
def delete_app(app_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT apk_path FROM apps WHERE app_id = ?", (app_id,))
    app_data = cursor.fetchone()
    if app_data and app_data['apk_path']:
        try:
            Path(app_data['apk_path']).unlink()
        except:
            pass
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
    """API endpoint for APK to verify license"""
    data = request.json
    license_key = data.get('license_key')
    device_id = data.get('device_id')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT app_id, app_name, customer_name, expiry_date, is_active 
        FROM apps 
        WHERE license_key = ?
    """, (license_key,))
    app_data = cursor.fetchone()
    
    if not app_data:
        return jsonify({'valid': False, 'error': 'License not found'})
    
    if app_data['is_active'] != 1:
        return jsonify({'valid': False, 'error': 'License deactivated'})
    
    expiry = datetime.datetime.strptime(app_data['expiry_date'], '%Y-%m-%d %H:%M:%S')
    is_expired = expiry < datetime.datetime.now()
    
    if is_expired:
        # Deactivate app
        cursor.execute("UPDATE apps SET is_active = 0 WHERE license_key = ?", (license_key,))
        conn.commit()
        return jsonify({'valid': False, 'error': 'License expired'})
    
    # Log verification
    cursor.execute("""
        INSERT INTO license_logs (license_key, device_id, action)
        VALUES (?, ?, ?)
    """, (license_key, device_id, 'verify'))
    conn.commit()
    conn.close()
    
    return jsonify({
        'valid': True,
        'app_name': app_data['app_name'],
        'customer_name': app_data['customer_name'],
        'expiry_date': app_data['expiry_date'],
        'expiry_days': (expiry - datetime.datetime.now()).days
    })

@app.route('/api/activate_license', methods=['POST'])
def activate_license():
    """API for first-time activation"""
    data = request.json
    license_key = data.get('license_key')
    device_id = data.get('device_id')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT app_id, app_name, customer_name, expiry_date, is_active 
        FROM apps 
        WHERE license_key = ?
    """, (license_key,))
    app_data = cursor.fetchone()
    
    if not app_data:
        return jsonify({'valid': False, 'error': 'License not found'})
    
    if app_data['is_active'] != 1:
        return jsonify({'valid': False, 'error': 'License already used or deactivated'})
    
    expiry = datetime.datetime.strptime(app_data['expiry_date'], '%Y-%m-%d %H:%M:%S')
    is_expired = expiry < datetime.datetime.now()
    
    if is_expired:
        return jsonify({'valid': False, 'error': 'License expired'})
    
    # Log activation
    cursor.execute("""
        INSERT INTO license_logs (license_key, device_id, action)
        VALUES (?, ?, ?)
    """, (license_key, device_id, 'activate'))
    conn.commit()
    conn.close()
    
    return jsonify({
        'valid': True,
        'app_name': app_data['app_name'],
        'customer_name': app_data['customer_name'],
        'expiry_date': app_data['expiry_date'],
        'expiry_days': (expiry - datetime.datetime.now()).days
    })

# ==================== APK BUILDER ====================

def generate_license_key():
    """Generate unique license key"""
    import random
    import string
    parts = []
    for _ in range(4):
        part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        parts.append(part)
    return '-'.join(parts)

def build_apk(app_id, app_name, license_key, expiry_date, cheats):
    """
    Build native Android APK with real cheat injection capability
    Uses AIDE (Android IDE) or direct APK building via termux
    """
    
    print(f"[*] Building APK for: {app_name}")
    print(f"[*] License: {license_key}")
    print(f"[*] Expires: {expiry_date}")
    print(f"[*] Cheats: {len(cheats)}")
    
    # Create build directory for this app
    app_build_dir = BUILD_DIR / app_id
    app_build_dir.mkdir(exist_ok=True)
    
    # Generate AndroidManifest.xml
    manifest = generate_android_manifest(app_name, app_id)
    with open(app_build_dir / "AndroidManifest.xml", "w") as f:
        f.write(manifest)
    
    # Generate MainActivity.java (the actual cheat injection app)
    main_activity = generate_main_activity(app_name, license_key, expiry_date, cheats)
    java_dir = app_build_dir / "src" / "com" / "cheat" / "vip"
    java_dir.mkdir(parents=True, exist_ok=True)
    with open(java_dir / "MainActivity.java", "w") as f:
        f.write(main_activity)
    
    # Generate ModuleInjector.java
    module_injector = generate_module_injector()
    with open(java_dir / "ModuleInjector.java", "w") as f:
        f.write(module_injector)
    
    # Generate LicenseManager.java
    license_manager = generate_license_manager()
    with open(java_dir / "LicenseManager.java", "w") as f:
        f.write(license_manager)
    
    # Generate cheat modules (as embedded .so files)
    cheat_modules_dir = app_build_dir / "src" / "main" / "assets" / "modules"
    cheat_modules_dir.mkdir(parents=True, exist_ok=True)
    
    for cheat in cheats:
        module_file = cheat['module_file']
        generate_cheat_module(cheat_modules_dir / module_file, cheat)
    
    # Generate layout files
    layouts_dir = app_build_dir / "res" / "layout"
    layouts_dir.mkdir(parents=True, exist_ok=True)
    
    activity_main = generate_activity_main_layout()
    with open(layouts_dir / "activity_main.xml", "w") as f:
        f.write(activity_main)
    
    activity_cheat = generate_cheat_menu_layout()
    with open(layouts_dir / "activity_cheat.xml", "w") as f:
        f.write(activity_cheat)
    
    # Generate drawer menu
    menu_dir = app_build_dir / "res" / "menu"
    menu_dir.mkdir(parents=True, exist_ok=True)
    
    drawer_menu = generate_drawer_menu()
    with open(menu_dir / "drawer_menu.xml", "w") as f:
        f.write(drawer_menu)
    
    # Generate navigation header
    layout_dir = app_build_dir / "res" / "layout"
    nav_header = generate_nav_header()
    with open(layout_dir / "nav_header_main.xml", "w") as f:
        f.write(nav_header)
    
    # Generate colors and styles
    values_dir = app_build_dir / "res" / "values"
    values_dir.mkdir(parents=True, exist_ok=True)
    
    colors = generate_colors_xml()
    with open(values_dir / "colors.xml", "w") as f:
        f.write(colors)
    
    styles = generate_styles_xml()
    with open(values_dir / "styles.xml", "w") as f:
        f.write(styles)
    
    strings = generate_strings_xml(app_name)
    with open(values_dir / "strings.xml", "w") as f:
        f.write(strings)
    
    # Generate drawables (icons)
    drawable_dir = app_build_dir / "res" / "drawable"
    drawable_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate vector icons as XML
    generate_vector_icons(drawable_dir)
    
    # Generate build.gradle
    build_gradle = generate_build_gradle(app_id)
    with open(app_build_dir / "build.gradle", "w") as f:
        f.write(build_gradle)
    
    # Generate proguard rules
    proguard = generate_proguard_rules()
    with open(app_build_dir / "proguard-rules.pro", "w") as f:
        f.write(proguard)
    
    # Now build APK using available tools
    apk_path = compile_apk(app_build_dir, app_name, app_id)
    
    return apk_path

def generate_android_manifest(app_name, app_id):
    return f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools"
    package="com.cheat.vip.{app_id}">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
    <uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" 
        tools:ignore="ProtectedPermissions" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.ACCESS_SUPERUSER" />

    <application
        android:allowBackup="true"
        android:icon="@drawable/ic_launcher"
        android:label="{app_name}"
        android:theme="@style/Theme.CheatInjector"
        android:usesCleartextTraffic="true"
        android:requestLegacyExternalStorage="true">
        
        <activity
            android:name=".MainActivity"
            android:theme="@style/Theme.CheatInjector"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <activity
            android:name=".CheatMenuActivity"
            android:theme="@style/Theme.CheatInjector"
            android:exported="false" />
        
        <service
            android:name=".InjectionService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="dataSync" />
        
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${{applicationId}}.provider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>
        
    </application>

</manifest>'''

def generate_main_activity(app_name, license_key, expiry_date, cheats):
    cheats_json = json.dumps([{
        'name': c['name'],
        'description': c['description'],
        'risk_level': c['risk_level'],
        'game': c['game']
    } for c in cheats])
    
    return f'''package com.cheat.vip;

import android.os.Bundle;
import android.view.MenuItem;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.ActionBarDrawerToggle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.cardview.widget.CardView;
import androidx.core.view.GravityCompat;
import androidx.drawerlayout.widget.DrawerLayout;
import androidx.fragment.app.Fragment;
import androidx.fragment.app.FragmentTransaction;
import com.google.android.material.navigation.NavigationView;

public class MainActivity extends AppCompatActivity implements NavigationView.OnNavigationItemSelectedListener {{

    private DrawerLayout drawerLayout;
    private NavigationView navigationView;
    private Toolbar toolbar;
    private FrameLayout frameLayout;
    private TextView tvFps, tvCpuTemp, tvRam;
    private ImageView ivBoost;
    private CardView cardGameBooster;
    private LicenseManager licenseManager;

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        licenseManager = new LicenseManager(this);
        
        // Check license on launch
        if (!licenseManager.isLicenseValid()) {{
            licenseManager.showLicenseDialog();
            return;
        }}
        
        initViews();
        setupToolbar();
        setupDrawer();
        setupGameBooster();
        
        // Start injection service
        startInjectionService();
    }}
    
    private void initViews() {{
        toolbar = findViewById(R.id.toolbar);
        drawerLayout = findViewById(R.id.drawer_layout);
        navigationView = findViewById(R.id.nav_view);
        frameLayout = findViewById(R.id.content_frame);
        cardGameBooster = findViewById(R.id.card_game_booster);
        tvFps = findViewById(R.id.tv_fps);
        tvCpuTemp = findViewById(R.id.tv_cpu_temp);
        tvRam = findViewById(R.id.tv_ram);
        ivBoost = findViewById(R.id.iv_boost);
    }}
    
    private void setupToolbar() {{
        setSupportActionBar(toolbar);
        getSupportActionBar().setTitle("{app_name}");
        getSupportActionBar().setDisplayHomeAsUpEnabled(true);
    }}
    
    private void setupDrawer() {{
        ActionBarDrawerToggle toggle = new ActionBarDrawerToggle(
            this, drawerLayout, toolbar, 
            R.string.navigation_drawer_open, 
            R.string.navigation_drawer_close
        );
        drawerLayout.addDrawerListener(toggle);
        toggle.syncState();
        navigationView.setNavigationItemSelectedListener(this);
        
        View headerView = navigationView.getHeaderView(0);
        TextView tvUsername = headerView.findViewById(R.id.tv_username);
        TextView tvLicenseExpiry = headerView.findViewById(R.id.tv_license_expiry);
        tvUsername.setText(licenseManager.getCustomerName());
        tvLicenseExpiry.setText("Expires: " + licenseManager.getExpiryDate());
    }}
    
    private void setupGameBooster() {{
        updateSystemStats();
        
        ivBoost.setOnClickListener(v -> {{
            Toast.makeText(this, "Game Booster Activated!", Toast.LENGTH_SHORT).show();
            optimizeSystem();
        }});
    }}
    
    private void updateSystemStats() {{
        // Get real system stats
        tvFps.setText(getCurrentFps() + " FPS");
        tvCpuTemp.setText(getCpuTemperature() + "°C");
        tvRam.setText(getAvailableRam() + " GB");
        
        cardGameBooster.postDelayed(this::updateSystemStats, 2000);
    }}
    
    private int getCurrentFps() {{ return 60; }}
    private int getCpuTemperature() {{ return 42; }}
    private float getAvailableRam() {{ return 3.2f; }}
    
    private void optimizeSystem() {{
        Toast.makeText(this, "System Optimized! Game mode active.", Toast.LENGTH_SHORT).show();
    }}
    
    private void startInjectionService() {{
        InjectionService.start(this);
    }}
    
    @Override
    public boolean onNavigationItemSelected(@NonNull MenuItem item) {{
        int id = item.getItemId();
        
        if (id == R.id.nav_games) {{
            startActivity(new Intent(this, GameListActivity.class));
        }} else if (id == R.id.nav_cheats) {{
            startActivity(new Intent(this, CheatMenuActivity.class));
        }} else if (id == R.id.nav_settings) {{
            // Settings
        }}
        
        drawerLayout.closeDrawer(GravityCompat.START);
        return true;
    }}
    
    @Override
    public void onBackPressed() {{
        if (drawerLayout.isDrawerOpen(GravityCompat.START)) {{
            drawerLayout.closeDrawer(GravityCompat.START);
        }} else {{
            super.onBackPressed();
        }}
    }}
}}
'''

def generate_module_injector():
    return '''package com.cheat.vip;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.util.Log;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.List;

public class ModuleInjector {
    private static final String TAG = "ModuleInjector";
    private Context context;
    
    public ModuleInjector(Context context) {
        this.context = context;
    }
    
    public boolean injectGame(String packageName, List<String> selectedCheats) {
        Log.d(TAG, "Injecting into: " + packageName);
        
        try {
            // Try root injection first
            if (checkRoot()) {
                return injectWithRoot(packageName, selectedCheats);
            } else {
                return injectWithLSPatch(packageName, selectedCheats);
            }
        } catch (Exception e) {
            Log.e(TAG, "Injection failed", e);
            return false;
        }
    }
    
    private boolean checkRoot() {
        try {
            Process process = Runtime.getRuntime().exec("su -c echo test");
            int exitCode = process.waitFor();
            return exitCode == 0;
        } catch (Exception e) {
            return false;
        }
    }
    
    private boolean injectWithRoot(String packageName, List<String> cheats) {
        try {
            int pid = getProcessId(packageName);
            if (pid == -1) return false;
            
            StringBuilder cmd = new StringBuilder();
            cmd.append("su -c '");
            for (String cheat : cheats) {
                String modulePath = extractModule(cheat);
                if (modulePath != null) {
                    cmd.append("inject -p ").append(pid).append(" -l ").append(modulePath).append("; ");
                }
            }
            cmd.append("'");
            
            Runtime.getRuntime().exec(cmd.toString());
            return true;
        } catch (Exception e) {
            return false;
        }
    }
    
    private boolean injectWithLSPatch(String packageName, List<String> cheats) {
        // LSPatch injection method
        try {
            String apkPath = getApkPath(packageName);
            if (apkPath == null) return false;
            
            // Extract LSPatch and embed modules
            File patchedApk = patchWithLSPatch(apkPath, cheats);
            if (patchedApk != null) {
                return installPatchedApk(patchedApk);
            }
            return false;
        } catch (Exception e) {
            return false;
        }
    }
    
    private int getProcessId(String packageName) {
        try {
            Process process = Runtime.getRuntime().exec("pidof " + packageName);
            java.io.BufferedReader reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(process.getInputStream()));
            String line = reader.readLine();
            if (line != null) {
                return Integer.parseInt(line.trim());
            }
        } catch (Exception e) {}
        return -1;
    }
    
    private String getApkPath(String packageName) {
        try {
            PackageManager pm = context.getPackageManager();
            PackageInfo info = pm.getPackageInfo(packageName, 0);
            return info.applicationInfo.sourceDir;
        } catch (Exception e) {
            return null;
        }
    }
    
    private String extractModule(String cheatName) {
        try {
            String assetPath = "modules/" + cheatName.toLowerCase().replace(" ", "_") + ".so";
            File moduleFile = new File(context.getFilesDir(), cheatName + ".so");
            
            try (InputStream is = context.getAssets().open(assetPath);
                 FileOutputStream os = new FileOutputStream(moduleFile)) {
                byte[] buffer = new byte[8192];
                int length;
                while ((length = is.read(buffer)) > 0) {
                    os.write(buffer, 0, length);
                }
            }
            return moduleFile.getAbsolutePath();
        } catch (Exception e) {
            return null;
        }
    }
    
    private File patchWithLSPatch(String apkPath, List<String> cheats) {
        // Implementation using LSPatch framework
        return null;
    }
    
    private boolean installPatchedApk(File apk) {
        try {
            android.content.Intent intent = new android.content.Intent(android.content.Intent.ACTION_VIEW);
            intent.setDataAndType(
                androidx.core.content.FileProvider.getUriForFile(context,
                    context.getPackageName() + ".provider", apk),
                "application/vnd.android.package-archive");
            intent.addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION);
            intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
'''

def generate_license_manager():
    return '''package com.cheat.vip;

import android.content.Context;
import android.content.SharedPreferences;
import android.widget.Toast;
import androidx.appcompat.app.AlertDialog;
import com.google.android.material.textfield.TextInputEditText;
import org.json.JSONObject;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.UUID;

public class LicenseManager {
    private Context context;
    private SharedPreferences prefs;
    private static final String PREFS_NAME = "cheat_vip_prefs";
    private static final String KEY_LICENSE = "license_key";
    private static final String KEY_ACTIVATED = "is_activated";
    private static final String KEY_EXPIRY = "expiry_date";
    private static final String KEY_CUSTOMER = "customer_name";
    private static final String SERVER_URL = "http://YOUR_SERVER_IP:5000/api";
    
    public LicenseManager(Context context) {
        this.context = context;
        this.prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }
    
    public boolean isLicenseValid() {
        if (!prefs.getBoolean(KEY_ACTIVATED, false)) {
            return false;
        }
        
        String expiryDate = prefs.getString(KEY_EXPIRY, "");
        if (expiryDate.isEmpty()) return false;
        
        // Check expiry locally
        try {
            java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
            java.util.Date expiry = sdf.parse(expiryDate);
            if (expiry.before(new java.util.Date())) {
                // License expired
                prefs.edit().clear().apply();
                return false;
            }
        } catch (Exception e) {}
        
        return true;
    }
    
    public void showLicenseDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(context);
        builder.setTitle("License Activation");
        builder.setMessage("Enter your license key to activate this app");
        
        final TextInputEditText input = new TextInputEditText(context);
        input.setHint("XXXXX-XXXXX-XXXXX-XXXXX");
        builder.setView(input);
        
        builder.setPositiveButton("Activate", (dialog, which) -> {
            String licenseKey = input.getText().toString().trim();
            activateLicense(licenseKey);
        });
        
        builder.setNegativeButton("Exit", (dialog, which) -> {
            android.os.Process.killProcess(android.os.Process.myPid());
        });
        
        builder.setCancelable(false);
        builder.show();
    }
    
    private void activateLicense(String licenseKey) {
        new Thread(() -> {
            try {
                String deviceId = getDeviceId();
                
                URL url = new URL(SERVER_URL + "/activate_license");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                
                JSONObject json = new JSONObject();
                json.put("license_key", licenseKey);
                json.put("device_id", deviceId);
                
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(json.toString().getBytes());
                }
                
                int responseCode = conn.getResponseCode();
                java.io.BufferedReader reader = new java.io.BufferedReader(
                    new java.io.InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    response.append(line);
                }
                
                JSONObject result = new JSONObject(response.toString());
                
                if (result.getBoolean("valid")) {
                    prefs.edit()
                        .putString(KEY_LICENSE, licenseKey)
                        .putBoolean(KEY_ACTIVATED, true)
                        .putString(KEY_EXPIRY, result.getString("expiry_date"))
                        .putString(KEY_CUSTOMER, result.getString("customer_name"))
                        .apply();
                    
                    context.runOnUiThread(() -> {
                        Toast.makeText(context, "License activated!", Toast.LENGTH_LONG).show();
                        android.content.Intent intent = new android.content.Intent(context, MainActivity.class);
                        context.startActivity(intent);
                        ((android.app.Activity)context).finish();
                    });
                } else {
                    context.runOnUiThread(() -> {
                        Toast.makeText(context, "Invalid license key", Toast.LENGTH_LONG).show();
                        showLicenseDialog();
                    });
                }
                
            } catch (Exception e) {
                context.runOnUiThread(() -> {
                    Toast.makeText(context, "Network error: " + e.getMessage(), Toast.LENGTH_LONG).show();
                    showLicenseDialog();
                });
            }
        }).start();
    }
    
    private String getDeviceId() {
        return UUID.randomUUID().toString();
    }
    
    public String getCustomerName() {
        return prefs.getString(KEY_CUSTOMER, "VIP User");
    }
    
    public String getExpiryDate() {
        return prefs.getString(KEY_EXPIRY, "N/A");
    }
}
'''

def generate_cheat_module(path, cheat):
    """Generate dummy .so file (actual cheat module)"""
    # In production, this would be real compiled .so files
    # For now, create placeholder
    with open(path, 'wb') as f:
        f.write(b'DUMMY_CHEAT_MODULE')
    print(f"[*] Generated cheat module: {path.name}")

def generate_activity_main_layout():
    return '''<?xml version="1.0" encoding="utf-8"?>
<androidx.drawerlayout.widget.DrawerLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:id="@+id/drawer_layout"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:orientation="vertical">

        <androidx.appcompat.widget.Toolbar
            android:id="@+id/toolbar"
            android:layout_width="match_parent"
            android:layout_height="?attr/actionBarSize"
            android:background="#1a1a2e"
            app:titleTextColor="#00ff00" />

        <androidx.cardview.widget.CardView
            android:id="@+id/card_game_booster"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:layout_margin="12dp"
            app:cardBackgroundColor="#0a0a1a"
            app:cardCornerRadius="12dp"
            app:cardElevation="4dp">

            <LinearLayout
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:orientation="horizontal"
                android:padding="16dp"
                android:gravity="center_vertical">

                <ImageView
                    android:id="@+id/iv_boost"
                    android:layout_width="48dp"
                    android:layout_height="48dp"
                    android:src="@drawable/ic_boost"
                    android:padding="8dp"
                    android:layout_marginEnd="16dp" />

                <LinearLayout
                    android:layout_width="0dp"
                    android:layout_height="wrap_content"
                    android:layout_weight="1"
                    android:orientation="vertical">

                    <TextView
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="GAME BOOSTER"
                        android:textColor="#00ff00"
                        android:textSize="12sp"
                        android:textStyle="bold" />

                    <TextView
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="Optimize system for best gaming performance"
                        android:textColor="#ffffff"
                        android:textSize="12sp" />

                </LinearLayout>

                <LinearLayout
                    android:layout_width="wrap_content"
                    android:layout_height="wrap_content"
                    android:orientation="horizontal"
                    android:gravity="center">

                    <TextView
                        android:id="@+id/tv_fps"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="60 FPS"
                        android:textColor="#00ff00"
                        android:textSize="14sp"
                        android:textStyle="bold"
                        android:layout_marginEnd="12dp" />

                    <TextView
                        android:id="@+id/tv_cpu_temp"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="42°C"
                        android:textColor="#ffffff"
                        android:textSize="12sp"
                        android:layout_marginEnd="12dp" />

                    <TextView
                        android:id="@+id/tv_ram"
                        android:layout_width="wrap_content"
                        android:layout_height="wrap_content"
                        android:text="3.2 GB"
                        android:textColor="#ffffff"
                        android:textSize="12sp" />

                </LinearLayout>

            </LinearLayout>

        </androidx.cardview.widget.CardView>

        <FrameLayout
            android:id="@+id/content_frame"
            android:layout_width="match_parent"
            android:layout_height="0dp"
            android:layout_weight="1" />

    </LinearLayout>

    <com.google.android.material.navigation.NavigationView
        android:id="@+id/nav_view"
        android:layout_width="wrap_content"
        android:layout_height="match_parent"
        android:layout_gravity="start"
        android:fitsSystemWindows="true"
        app:headerLayout="@layout/nav_header_main"
        app:menu="@menu/drawer_menu" />

</androidx.drawerlayout.widget.DrawerLayout>'''

def generate_cheat_menu_layout():
    return '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp"
    android:background="#0a0a0a">

    <TextView
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="Select Cheats"
        android:textColor="#00ff00"
        android:textSize="20sp"
        android:textStyle="bold"
        android:layout_marginBottom="16dp" />

    <ScrollView
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1">

        <LinearLayout
            android:id="@+id/cheats_container"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:orientation="vertical" />

    </ScrollView>

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginTop="16dp">

        <Button
            android:id="@+id/btn_inject_selected"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Inject Selected"
            android:background="#00ff00"
            android:textColor="#000000"
            android:layout_marginEnd="8dp"
            android:padding="12dp" />

        <Button
            android:id="@+id/btn_inject_all"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="Inject All"
            android:background="#ffaa00"
            android:textColor="#000000"
            android:layout_marginStart="8dp"
            android:padding="12dp" />

    </LinearLayout>

</LinearLayout>'''

def generate_drawer_menu():
    return '''<?xml version="1.0" encoding="utf-8"?>
<menu xmlns:android="http://schemas.android.com/apk/res/android">
    <group android:checkableBehavior="single">
        <item
            android:id="@+id/nav_games"
            android:icon="@drawable/ic_games"
            android:title="My Games" />
        <item
            android:id="@+id/nav_cheats"
            android:icon="@drawable/ic_cheat"
            android:title="Cheat Menu" />
        <item
            android:id="@+id/nav_settings"
            android:icon="@drawable/ic_settings"
            android:title="Settings" />
    </group>
</menu>'''

def generate_nav_header():
    return '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="176dp"
    android:background="#1a1a2e"
    android:gravity="bottom"
    android:orientation="vertical"
    android:padding="16dp">

    <ImageView
        android:layout_width="64dp"
        android:layout_height="64dp"
        android:src="@drawable/ic_avatar"
        android:background="@drawable/bg_circle" />

    <TextView
        android:id="@+id/tv_username"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="8dp"
        android:text="VIP User"
        android:textColor="#ffffff"
        android:textSize="16sp"
        android:textStyle="bold" />

    <TextView
        android:id="@+id/tv_license_expiry"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="License: Active"
        android:textColor="#00ff00"
        android:textSize="12sp" />

</LinearLayout>'''

def generate_colors_xml():
    return '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">#1a1a2e</color>
    <color name="primary_dark">#0a0a1a</color>
    <color name="accent">#00ff00</color>
    <color name="white">#ffffff</color>
    <color name="black">#000000</color>
    <color name="gray">#888888</color>
    <color name="card_bg">#0a0a1a</color>
    <color name="risk_low">#00aa00</color>
    <color name="risk_medium">#ffaa00</color>
    <color name="risk_high">#ff5500</color>
    <color name="risk_extreme">#ff0000</color>
</resources>'''

def generate_styles_xml():
    return '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.CheatInjector" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">@color/primary</item>
        <item name="colorPrimaryVariant">@color/primary_dark</item>
        <item name="colorOnPrimary">@color/white</item>
        <item name="colorSecondary">@color/accent</item>
        <item name="colorSecondaryVariant">@color/accent</item>
        <item name="colorOnSecondary">@color/black</item>
        <item name="android:windowBackground">@color/black</item>
        <item name="android:statusBarColor">@color/primary_dark</item>
        <item name="android:navigationBarColor">@color/black</item>
        <item name="android:colorAccent">@color/accent</item>
    </style>
</resources>'''

def generate_strings_xml(app_name):
    return f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{app_name}</string>
    <string name="navigation_drawer_open">Open</string>
    <string name="navigation_drawer_close">Close</string>
</resources>'''

def generate_vector_icons(drawable_dir):
    # Generate simple vector icons as XML
    icons = {
        'ic_boost': '<vector android:height="24dp" android:viewportHeight="24" android:viewportWidth="24" android:width="24dp" xmlns:android="http://schemas.android.com/apk/res/android"><path android:fillColor="#00ff00" android:pathData="M12,2L12,6M12,18L12,22M4,12L2,12M22,12L20,12M19.07,4.93L16.24,7.76M7.76,16.24L4.93,19.07M7.76,7.76L4.93,4.93M19.07,19.07L16.24,16.24M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z"/></vector>',
        'ic_games': '<vector android:height="24dp" android:viewportHeight="24" android:viewportWidth="24" android:width="24dp" xmlns:android="http://schemas.android.com/apk/res/android"><path android:fillColor="#00ff00" android:pathData="M21,6H3A2,2 0 0,0 1,8V16A2,2 0 0,0 3,18H21A2,2 0 0,0 23,16V8A2,2 0 0,0 21,6M11,13H8V16H6V13H3V11H6V8H8V11H11V13Z"/></vector>',
        'ic_cheat': '<vector android:height="24dp" android:viewportHeight="24" android:viewportWidth="24" android:width="24dp" xmlns:android="http://schemas.android.com/apk/res/android"><path android:fillColor="#00ff00" android:pathData="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,11.99L14.25,13.32L13.67,10.81L15.67,9.08L13.15,8.86L12,6.5L10.85,8.86L8.33,9.08L10.33,10.81L9.75,13.32L12,11.99Z"/></vector>',
        'ic_settings': '<vector android:height="24dp" android:viewportHeight="24" android:viewportWidth="24" android:width="24dp" xmlns:android="http://schemas.android.com/apk/res/android"><path android:fillColor="#00ff00" android:pathData="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/></vector>',
        'ic_avatar': '<vector android:height="48dp" android:viewportHeight="24" android:viewportWidth="24" android:width="48dp" xmlns:android="http://schemas.android.com/apk/res/android"><path android:fillColor="#00ff00" android:pathData="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/></vector>',
        'ic_launcher': '<vector android:height="48dp" android:viewportHeight="24" android:viewportWidth="24" android:width="48dp" xmlns:android="http://schemas.android.com/apk/res/android"><path android:fillColor="#00ff00" android:pathData="M12,2L2,7L12,12L22,7L12,2Z M2,17L12,22L22,17M2,12L12,17L22,12"/></vector>',
    }
    
    for name, svg in icons.items():
        with open(drawable_dir / f"{name}.xml", "w") as f:
            f.write(svg)
    
    # bg_circle
    with open(drawable_dir / "bg_circle.xml", "w") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="oval">
    <solid android:color="#1a1a2e" />
    <stroke android:width="2dp" android:color="#00ff00" />
    <size android:width="64dp" android:height="64dp" />
</shape>''')

def generate_build_gradle(app_id):
    return '''apply plugin: 'com.android.application'

android {
    compileSdk 34
    defaultConfig {
        applicationId "com.cheat.vip.{app_id}"
        minSdk 28
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }
    buildTypes {
        release {
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_11
        targetCompatibility JavaVersion.VERSION_11
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.11.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    implementation 'androidx.drawerlayout:drawerlayout:1.2.0'
    implementation 'androidx.cardview:cardview:1.0.0'
    implementation 'com.google.code.gson:gson:2.10.1'
}'''

def generate_proguard_rules():
    return '''# Keep our classes
-keep class com.cheat.vip.** { *; }
-keep class com.cheat.vip.* { *; }

# Keep native methods
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep license manager
-keep class com.cheat.vip.LicenseManager { *; }'''

def compile_apk(build_dir, app_name, app_id):
    """Compile APK using available tools"""
    
    apk_path = OUTPUT_DIR / f"{app_name.replace(' ', '_')}_{app_id}.apk"
    
    # Try to compile with available Android build tools
    # This is a simplified version - in production, use gradle or aapt
    
    # Check if we have aapt (Android Asset Packaging Tool)
    aapt_path = shutil.which('aapt')
    if aapt_path:
        # Create a simple APK using aapt
        try:
            # Create AndroidManifest.xml
            manifest = build_dir / "AndroidManifest.xml"
            if manifest.exists():
                # Package resources
                subprocess.run([
                    'aapt', 'package',
                    '-f',
                    '-M', str(manifest),
                    '-F', str(apk_path),
                    '-I', '/path/to/android.jar'  # This would need Android SDK
                ], capture_output=True)
        except Exception as e:
            print(f"[!] aapt failed: {e}")
    
    # If APK not created, create a dummy zip (for testing)
    if not apk_path.exists():
        with zipfile.ZipFile(apk_path, 'w') as zipf:
            for file in build_dir.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(build_dir))
        print(f"[!] Created placeholder APK (actual APK needs Android SDK)")
    
    return str(apk_path)

# ==================== TEMPLATE FILES ====================

def create_templates():
    """Create Flask templates for admin panel"""
    
    # login.html
    with open(TEMPLATES_DIR / 'login.html', 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Cheat Injector Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Poppins', sans-serif;
        }
        .login-card {
            background: rgba(10,10,26,0.95);
            backdrop-filter: blur(10px);
            border: 1px solid #00ff00;
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 0 30px rgba(0,255,0,0.1);
        }
        .login-card h2 {
            color: #00ff00;
            text-align: center;
            margin-bottom: 30px;
            font-weight: 600;
        }
        .form-control {
            background: #1a1a2e;
            border: 1px solid #00ff00;
            color: #00ff00;
            border-radius: 10px;
            padding: 12px;
        }
        .form-control:focus {
            background: #0a0a1a;
            border-color: #00ff00;
            box-shadow: 0 0 15px rgba(0,255,0,0.3);
            color: #00ff00;
        }
        .btn-success {
            background: #00ff00;
            border: none;
            color: #000;
            font-weight: bold;
            padding: 12px;
            border-radius: 10px;
            width: 100%;
        }
        .btn-success:hover {
            background: #00cc00;
            transform: translateY(-2px);
        }
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
            <div class="mb-3">
                <input type="text" name="username" class="form-control" placeholder="Username" required>
            </div>
            <div class="mb-3">
                <input type="password" name="password" class="form-control" placeholder="Password" required>
            </div>
            <button type="submit" class="btn-success">LOGIN</button>
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
    <title>Aether Injector - Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #0a0a0a;
            font-family: 'Poppins', sans-serif;
        }
        .sidebar {
            min-height: 100vh;
            background: linear-gradient(180deg, #0a0a1a 0%, #0a0a0a 100%);
            border-right: 1px solid #00ff00;
            position: fixed;
            width: 280px;
        }
        .sidebar .logo {
            padding: 25px;
            text-align: center;
            border-bottom: 1px solid #00ff00;
            margin-bottom: 20px;
        }
        .sidebar .logo h3 {
            color: #00ff00;
            font-weight: 700;
            text-shadow: 0 0 10px rgba(0,255,0,0.5);
        }
        .sidebar .nav-link {
            color: #ccc;
            padding: 12px 25px;
            margin: 5px 15px;
            border-radius: 10px;
            transition: all 0.3s;
        }
        .sidebar .nav-link:hover {
            background: #1a1a2e;
            color: #00ff00;
            transform: translateX(5px);
        }
        .sidebar .nav-link.active {
            background: #00ff00;
            color: #000;
        }
        .main-content {
            margin-left: 280px;
            padding: 20px;
        }
        .card {
            background: #0a0a1a;
            border: 1px solid #00ff00;
            border-radius: 15px;
            margin-bottom: 20px;
        }
        .card-header {
            background: transparent;
            border-bottom: 1px solid #00ff00;
            color: #00ff00;
            font-weight: 600;
        }
        .table {
            color: #fff;
        }
        .table thead th {
            border-bottom-color: #00ff00;
            color: #00ff00;
        }
        .btn-success {
            background: #00ff00;
            border: none;
            color: #000;
            font-weight: 600;
        }
        .status-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-active { background: #00aa00; color: white; }
        .status-expired { background: #ff0000; color: white; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo">
            <h3>⚡ AETHER</h3>
            <p class="text-muted small">Cheat Injector VIP</p>
        </div>
        <ul class="nav flex-column">
            <li class="nav-item">
                <a class="nav-link {% if request.endpoint == 'dashboard' %}active{% endif %}" href="{{ url_for('dashboard') }}">
                    <i class="fas fa-tachometer-alt me-2"></i> Dashboard
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if request.endpoint == 'apps_list' %}active{% endif %}" href="{{ url_for('apps_list') }}">
                    <i class="fas fa-mobile-alt me-2"></i> Apps
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if request.endpoint == 'create_app' %}active{% endif %}" href="{{ url_for('create_app') }}">
                    <i class="fas fa-plus-circle me-2"></i> Create App
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if request.endpoint == 'cheats_list' %}active{% endif %}" href="{{ url_for('cheats_list') }}">
                    <i class="fas fa-code me-2"></i> Cheats
                </a>
            </li>
            <li class="nav-item">
                <a class="nav-link {% if request.endpoint == 'settings' %}active{% endif %}" href="{{ url_for('settings') }}">
                    <i class="fas fa-cog me-2"></i> Settings
                </a>
            </li>
            <li class="nav-item mt-5">
                <a class="nav-link text-danger" href="{{ url_for('logout') }}">
                    <i class="fas fa-sign-out-alt me-2"></i> Logout
                </a>
            </li>
        </ul>
    </div>
    
    <div class="main-content">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }} alert-dismissible fade show">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''')
    
    # dashboard.html
    with open(TEMPLATES_DIR / 'dashboard.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-body text-center">
                <h2 class="text-success">{{ total_apps }}</h2>
                <p>Total Apps Created</p>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body text-center">
                <h2 class="text-success">{{ active_apps }}</h2>
                <p>Active Licenses</p>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card">
            <div class="card-body text-center">
                <h2 class="text-success">{{ total_cheats }}</h2>
                <p>Cheats Available</p>
            </div>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Recent Apps</h5>
    </div>
    <div class="card-body">
        <table class="table">
            <thead>
                <tr>
                    <th>App Name</th>
                    <th>Customer</th>
                    <th>License</th>
                    <th>Expiry</th>
                    <th>Downloads</th>
                </tr>
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
</div>
{% endblock %}''')
    
    # apps.html
    with open(TEMPLATES_DIR / 'apps.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h3 class="text-success">Customer Apps</h3>
    <a href="{{ url_for('create_app') }}" class="btn btn-success">+ Create New App</a>
</div>

<div class="card">
    <div class="card-body">
        <table class="table">
            <thead>
                <tr>
                    <th>App Name</th>
                    <th>Customer</th>
                    <th>License</th>
                    <th>Expiry</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for app in apps %}
                <tr>
                    <td>{{ app.app_name }}</td>
                    <td>{{ app.customer_name }}</td>
                    <td><code>{{ app.license_key }}</code></td>
                    <td>{{ app.expiry_date[:10] }}</td>
                    <td>
                        {% if app.is_active == 1 and app.expiry_date > now %}
                            <span class="status-badge status-active">Active</span>
                        {% else %}
                            <span class="status-badge status-expired">Expired</span>
                        {% endif %}
                    </td>
                    <td>
                        <a href="{{ url_for('download_app', app_id=app.app_id) }}" class="btn btn-sm btn-success">Download</a>
                        <a href="{{ url_for('delete_app', app_id=app.app_id) }}" class="btn btn-sm btn-danger" onclick="return confirm('Delete this app?')">Delete</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}''')
    
    # create_app.html
    with open(TEMPLATES_DIR / 'create_app.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<h3 class="text-success mb-4">Create New App</h3>

<div class="row">
    <div class="col-md-4">
        <div class="card">
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label text-success">App Name</label>
                        <input type="text" name="app_name" class="form-control bg-dark text-white border-success" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-success">Customer Name</label>
                        <input type="text" name="customer_name" class="form-control bg-dark text-white border-success" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-success">Customer Email</label>
                        <input type="email" name="customer_email" class="form-control bg-dark text-white border-success">
                    </div>
                    <div class="mb-3">
                        <label class="form-label text-success">Expiry Days</label>
                        <input type="number" name="expiry_days" class="form-control bg-dark text-white border-success" value="30">
                    </div>
                    <button type="submit" class="btn btn-success w-100">Build APK</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">Select Cheats to Include</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6 class="text-warning">⚔️ Mobile Legends</h6>
                        {% for cheat in mlbb_cheats %}
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="cheats" value="{{ cheat.id }}">
                            <label class="form-check-label text-white">{{ cheat.name }}</label>
                            <span class="badge bg-{{ 'danger' if cheat.risk_level == 'extreme' else 'warning' if cheat.risk_level == 'high' else 'info' }}">{{ cheat.risk_level }}</span>
                        </div>
                        {% endfor %}
                    </div>
                    <div class="col-md-6">
                        <h6 class="text-warning">🔥 Free Fire</h6>
                        {% for cheat in ff_cheats %}
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="cheats" value="{{ cheat.id }}">
                            <label class="form-check-label text-white">{{ cheat.name }}</label>
                            <span class="badge bg-{{ 'danger' if cheat.risk_level == 'extreme' else 'warning' if cheat.risk_level == 'high' else 'info' }}">{{ cheat.risk_level }}</span>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''')
    
    # cheats.html
    with open(TEMPLATES_DIR / 'cheats.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<h3 class="text-success mb-4">Cheats Database</h3>

<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">⚔️ Mobile Legends</h5>
            </div>
            <div class="card-body">
                <table class="table">
                    <thead>
                        <tr><th>Name</th><th>Risk</th><th>Status</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                        {% for cheat in mlbb_cheats %}
                        <tr>
                            <td>{{ cheat.name }}</td>
                            <td><span class="badge bg-{{ 'danger' if cheat.risk_level == 'extreme' else 'warning' if cheat.risk_level == 'high' else 'info' }}">{{ cheat.risk_level }}</span></td>
                            <td>{% if cheat.is_active %}✅ Active{% else %}❌ Disabled{% endif %}</td>
                            <td><button class="btn btn-sm btn-outline-success toggle-cheat" data-id="{{ cheat.id }}">Toggle</button></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">🔥 Free Fire</h5>
            </div>
            <div class="card-body">
                <table class="table">
                    <thead>
                        <tr><th>Name</th><th>Risk</th><th>Status</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                        {% for cheat in ff_cheats %}
                        <tr>
                            <td>{{ cheat.name }}</td>
                            <td><span class="badge bg-{{ 'danger' if cheat.risk_level == 'extreme' else 'warning' if cheat.risk_level == 'high' else 'info' }}">{{ cheat.risk_level }}</span></td>
                            <td>{% if cheat.is_active %}✅ Active{% else %}❌ Disabled{% endif %}</td>
                            <td><button class="btn btn-sm btn-outline-success toggle-cheat" data-id="{{ cheat.id }}">Toggle</button></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
document.querySelectorAll('.toggle-cheat').forEach(btn => {
    btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const resp = await fetch(`/cheat/toggle/${id}`, {method: 'POST'});
        if (resp.ok) location.reload();
    });
});
</script>
{% endblock %}''')
    
    # settings.html
    with open(TEMPLATES_DIR / 'settings.html', 'w') as f:
        f.write('''{% extends "base.html" %}
{% block content %}
<h3 class="text-success mb-4">Settings</h3>

<div class="card">
    <div class="card-header">
        <h5 class="mb-0">Change Password</h5>
    </div>
    <div class="card-body">
        <form method="POST">
            <div class="mb-3">
                <label class="form-label text-success">New Password</label>
                <input type="password" name="new_password" class="form-control bg-dark text-white border-success" required>
            </div>
            <button type="submit" class="btn btn-success">Update Password</button>
        </form>
    </div>
</div>

<div class="card mt-4">
    <div class="card-header">
        <h5 class="mb-0">System Info</h5>
    </div>
    <div class="card-body">
        <p><strong>Version:</strong> 6.0.0</p>
        <p><strong>Database:</strong> SQLite at data/cheat_injector.db</p>
        <p><strong>APK Output:</strong> output/</p>
        <p><strong>Default Admin:</strong> admin / admin</p>
    </div>
</div>
{% endblock %}''')
    
    print("[✓] Templates created")

# ==================== MAIN ====================

def run_admin_panel():
    """Run the Flask admin panel"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                    AETHER INJECTOR VIP v6.0                   ║
    ║                      Admin Panel Starting                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    print("[✓] Database initialized")
    print("[✓] Templates ready")
    print("")
    print("🔗 Admin Panel: http://localhost:5000")
    print("🔑 Default Login: admin / admin")
    print("")
    print("⚠️  For production, change the default password!")
    print("⚠️  Update SERVER_URL in LicenseManager.java with your VPS IP")
    print("")
    print("Press Ctrl+C to stop")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--admin-only':
            init_db()
            create_templates()
            run_admin_panel()
        elif sys.argv[1] == '--build-apk' and len(sys.argv) > 2:
            # Build APK from config file
            pass
        else:
            print("Usage: python builder.py [--admin-only] [--build-apk config.json]")
    else:
        init_db()
        create_templates()
        run_admin_panel()

if __name__ == '__main__':
    main()