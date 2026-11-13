"""Simple, transparent video link landing page."""
from flask import Flask, render_template

app = Flask(__name__)

@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'none'; style-src 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response

@app.get('/')
def home():
    return render_template('index.html')

@app.get('/health')
def health():
    return {'status': 'ok'}
