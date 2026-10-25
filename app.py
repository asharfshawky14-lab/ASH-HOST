
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ASH-HOST</title>
        <style>
            body {
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                background: #0b0b16;
                color: #fff;
                font-family: Arial, sans-serif;
                text-align: center;
            }
            .card {
                width: 85%;
                max-width: 420px;
                padding: 28px 18px;
                border: 1px solid #713cff;
                border-radius: 18px;
                background: #151326;
                box-sizing: border-box;
                box-shadow: 0 0 25px #713cff30;
            }
            h1 { color: #a78bfa; }
            .status { color: #4ade80; }
            p { color: #cbd5e1; line-height: 1.8; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 ASH-HOST</h1>
            <p class="status">● التطبيق يعمل</p>
            <p>منصة إدارة البوتات الخاصة بك</p>
            <p>دي صفحة الاختبار الأولى، ولسه هنضيف لوحة التحكم.</p>
        </div>
    </body>
    </html>
    """

@app.route("/health")
def health():
    return jsonify(status="ok", service="ASH-HOST")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
  
