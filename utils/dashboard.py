from flask import Flask, render_template, jsonify, request, session, redirect
import logging
import datetime
import os

# Dashboard HTML: templates/index.html faylida joylashgan.
# Flask avtomatik ravishda templates/ papkasidan qidiradi.

# Loyiha ildiz papkasi (utils/ ning yuqorisidagi papka)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEMPLATE_DIR = os.path.join(_BASE_DIR, 'templates')

def create_app(bot_state: dict, config: dict, lock):
    _STATIC_DIR = os.path.join(_BASE_DIR, 'static')
    app = Flask(__name__, template_folder=_TEMPLATE_DIR, static_folder=_STATIC_DIR)
    app.secret_key = "gemini_terminal_ultra_v27"
    pwd = config.get('web', {}).get('password', 'gemini2024')

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            if request.form.get('password') == pwd:
                session['logged'] = True
                return redirect('/')
        return '<html><body style="background:#060912;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh"><form method="POST"><h2 style="color:#00f5ff;margin-bottom:16px">⚡ GEMINI LOGIN</h2><input type="password" name="password" placeholder="Parol" style="padding:12px;border-radius:8px;border:1px solid #333;background:#0b0e1a;color:#fff;display:block;margin-bottom:12px;width:220px"><button type="submit" style="width:100%;padding:12px;background:linear-gradient(135deg,#9e00ff,#00f5ff);border:none;border-radius:8px;color:#fff;font-weight:800;cursor:pointer">KIRISH</button></form></body></html>'

    @app.route('/')
    def index():
        if not session.get('logged'): return redirect('/login')
        return render_template('index.html')


    @app.route('/api/symbols_data')
    def sd():
        if not session.get('logged'): return jsonify({'err':'unauth'})

        # PythonAnywhere jonli sinxronizatsiyasi (Fayldan o'qish)
        import os, json
        try:
            if os.path.exists('data/bot_state.json'):
                with open('data/bot_state.json', 'r') as f:
                    bot_state.update(json.load(f))
        except: pass

        symbols_list = bot_state.get('symbols', {})
        terminal = bot_state.get('terminal', {})
        signals = bot_state.get('signals_log', [])
        last_ai = bot_state.get('last_ai_report', '')
        
        syms_ui = {}
        for s, d in symbols_list.items():
            price = d.get('price')
            price_str = f"{price:.5g}" if price is not None else "0.000"
            syms_ui[s] = {'price': price_str, 'change': d.get('change', 0)}
        
        return jsonify({
            'symbols': syms_ui, 
            'terminal': terminal, 
            'signals': signals,
            'last_ai_report': last_ai
        })

    @app.route('/api/request_ai', methods=['POST'])
    def rai():
        if not session.get('logged'): return jsonify({'err':'unauth'})
        data = request.json
        with lock:
            bot_state['ai_requests'].append({'type': data.get('type', 'technical'), 'symbol': data.get('symbol', 'XAU/USD')})
        return jsonify({'ok':True})

    @app.route('/api/panic', methods=['POST'])
    def panic():
        if not session.get('logged'): return jsonify({'err':'unauth'})
        with lock: bot_state['panic_request'] = True
        return jsonify({'ok':True})

    @app.route('/webhook', methods=['POST'])
    def webhook():
        """TradingView yoki tashqi manbadan (Pine Script) kelgan signalni qabul qilish"""
        data = request.json
        if not data:
            return jsonify({"error": "No JSON payload"}), 400
        
        # Webhook navbatiga yozib qo'yamiz (bot.py o'qib, AI ga beradi)
        import json, os
        queue_file = 'data/webhook_queue.json'
        try:
            queue = []
            if os.path.exists(queue_file):
                with open(queue_file, 'r') as f:
                    queue = json.load(f)
            
            queue.append(data)
            
            # Atomic yo'sinda yozish
            with open(queue_file + '.tmp', 'w') as f:
                json.dump(queue, f)
            os.replace(queue_file + '.tmp', queue_file)
            
            return jsonify({"status": "queued", "message": "Signal qabul qilindi va navbatga qo'shildi."}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app
