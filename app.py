
import os
import io
import time
import json
import uuid
import hmac
import secrets
import logging
from datetime import datetime
from functools import wraps

import psycopg
from psycopg.rows import dict_row
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    render_template_string,
    send_file,
    abort,
)

# ==========================================
# ASH-HOST | إعدادات التطبيق
# ==========================================

APP_NAME = "ASH-HOST"
APP_VERSION = "1.0.0"

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SESSION_SECRET")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 3600 * 12

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("DATABASE-URL", "")
).strip()

WORKER_URL = os.environ.get("WORKER_URL", "").strip().rstrip("/")
WORKER_SECRET = os.environ.get("WORKER_SECRET", "").strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("ash-host")


# ==========================================
# التحقق من الإعدادات
# ==========================================

def configuration_status():
    return {
        "admin_password": bool(ADMIN_PASSWORD),
        "session_secret": bool(app.config["SECRET_KEY"]),
        "database_url": bool(DATABASE_URL),
        "worker_url": bool(WORKER_URL),
        "worker_secret": bool(WORKER_SECRET),
    }


# ==========================================
# الاتصال بقاعدة PostgreSQL
# ==========================================

def get_db():
    if not DATABASE_URL:
        raise RuntimeError(
            "متغير DATABASE_URL غير مضبوط في إعدادات الاستضافة."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


# ==========================================
# إنشاء جداول لوحة التحكم
# ==========================================

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ash_host_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content BYTEA NOT NULL,
                    size_bytes BIGINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ash_host_events (
                    id BIGSERIAL PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()


# ==========================================
# تسجيل أحداث النظام
# ==========================================

def log_event(event_type, message):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ash_host_events
                        (event_type, message)
                    VALUES (%s, %s)
                    """,
                    (str(event_type)[:50], str(message)[:2000]),
                )
            conn.commit()

    except Exception:
        logger.exception("تعذر تسجيل حدث في قاعدة البيانات")


# ==========================================
# أدوات مساعدة
# ==========================================

def get_setting_status():
    settings = configuration_status()

    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "database_configured": settings["database_url"],
        "worker_configured": (
            settings["worker_url"]
            and settings["worker_secret"]
        ),
        "admin_configured": settings["admin_password"],
        "session_configured": settings["session_secret"],
    }


def admin_required(view_function):
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped


@app.errorhandler(413)
def file_too_large(error):
    return "حجم الملف أكبر من الحد المسموح (10 MB).", 413


@app.errorhandler(404)
def page_not_found(error):
    return "الصفحة المطلوبة غير موجودة.", 404


@app.errorhandler(500)
def internal_error(error):
    logger.exception("حدث خطأ داخلي في التطبيق")
    return "حدث خطأ داخلي. راجع سجلات الاستضافة.", 500


# ==========================================
# فحص صحة التطبيق
# ==========================================

@app.route("/health")
def health():
    database_ok = False

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        database_ok = True

    except Exception:
        logger.exception("فشل فحص قاعدة البيانات")

    status_code = 200 if database_ok else 503

    return jsonify({
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "ok" if database_ok else "degraded",
        "database": "connected" if database_ok else "disconnected",
        "worker_configured": bool(WORKER_URL and WORKER_SECRET),
    }), status_code




# لا تشغّل خادم التطوير مباشرة عند الاستيراد بواسطة Gunicorn.
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )

# ==========================================
# ASH-HOST | تسجيل الدخول والخروج
# ==========================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تسجيل الدخول | ASH-HOST</title>
<style>
*{box-sizing:border-box}
body{
    margin:0;min-height:100vh;display:flex;
    align-items:center;justify-content:center;
    padding:20px;background:#0b0b12;color:#f4f4ff;
    font-family:Arial,sans-serif
}
.card{
    width:100%;max-width:410px;padding:30px;
    border:1px solid #343052;border-radius:22px;
    background:#161526;box-shadow:0 20px 70px #0008
}
.logo{text-align:center;font-size:32px;font-weight:bold;color:#a99aff}
.subtitle{text-align:center;color:#aaa8c6;margin:12px 0 28px;line-height:1.8}
label{display:block;margin-bottom:9px}
input{
    width:100%;padding:15px;border-radius:12px;
    border:1px solid #393650;outline:none;
    background:#10101b;color:white;font-size:16px
}
input:focus{border-color:#a99aff}
button{
    width:100%;margin-top:18px;padding:15px;border:0;
    border-radius:12px;
    background:linear-gradient(100deg,#7664f5,#27c8db);
    color:#090914;font-size:16px;font-weight:bold;cursor:pointer
}
.message{margin-bottom:16px;padding:12px;border-radius:10px;background:#48212b;color:#ffc8d2}
.footer{text-align:center;margin-top:24px;font-size:12px;color:#85829f}
</style>
</head>
<body>
<main class="card">
<div class="logo">ASH-HOST</div>
<div class="subtitle">لوحة إدارة واستضافة بوتات تيليجرام</div>

{% if error %}
<div class="message">{{ error }}</div>
{% endif %}

<form method="POST" action="{{ url_for('login') }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label for="password">كلمة مرور الإدارة</label>
<input id="password" name="password" type="password"
placeholder="أدخل كلمة المرور"
autocomplete="current-password" required autofocus>
<button type="submit">دخول إلى لوحة التحكم</button>
</form>

<div class="footer">ASH-HOST · لوحة إدارة خاصة</div>
</main>
</body>
</html>
"""


# ==========================================
# حماية CSRF للنماذج
# ==========================================

def generate_csrf_token():
    token = session.get("_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token

    return token


def validate_csrf_token():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("_csrf_token", "")

    if (
        not submitted
        or not expected
        or not hmac.compare_digest(submitted, expected)
    ):
        abort(400, description="رمز حماية الطلب غير صحيح.")


@app.context_processor
def inject_template_security():
    return {"csrf_token": generate_csrf_token}


# ==========================================
# تسجيل الدخول
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("index"))

    if not ADMIN_PASSWORD:
        return (
            "خطأ إعداد: متغير ADMIN_PASSWORD غير مضبوط في الاستضافة.",
            503,
        )

    error = None

    if request.method == "POST":
        validate_csrf_token()
        submitted_password = request.form.get("password", "")

        if hmac.compare_digest(submitted_password, ADMIN_PASSWORD):
            session.clear()
            session["admin_logged_in"] = True
            session["login_time"] = int(time.time())
            session["_csrf_token"] = secrets.token_urlsafe(32)
            session.permanent = True

            logger.info("تم تسجيل دخول المسؤول")
            log_event("login", "تم تسجيل دخول المسؤول")

            return redirect(url_for("index"))

        error = "كلمة المرور غير صحيحة."
        logger.warning("محاولة دخول غير ناجحة")

    return render_template_string(
        LOGIN_PAGE,
        error=error,
        csrf_token=generate_csrf_token(),
    )


# ==========================================
# تسجيل الخروج
# ==========================================

@app.route("/logout", methods=["POST"])
@admin_required
def logout():
    validate_csrf_token()
    session.clear()

    logger.info("تم تسجيل خروج المسؤول")
    log_event("logout", "تم تسجيل خروج المسؤول")

    return redirect(url_for("login"))


# ==========================================
# صفحة رفض الوصول
# ==========================================

@app.errorhandler(403)
def forbidden_page(error):
    return "ليس لديك إذن للوصول إلى هذه الصفحة.", 403

# ==========================================
# ASH-HOST | إحصائيات لوحة التحكم
# ==========================================

def get_dashboard_stats():
    stats = {
        "files_count": 0,
        "files_size": 0,
        "events_count": 0,
        "database_status": "غير متصل",
    }

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total,
                           COALESCE(SUM(size_bytes), 0) AS total_size
                    FROM ash_host_files
                """)
                row = cur.fetchone()
                stats["files_count"] = row["total"]
                stats["files_size"] = row["total_size"]

                cur.execute("""
                    SELECT COUNT(*) AS total
                    FROM ash_host_events
                """)
                stats["events_count"] = cur.fetchone()["total"]
                stats["database_status"] = "متصل"

    except Exception:
        logger.exception("تعذر تحميل إحصائيات لوحة التحكم")

    return stats


def get_recent_events(limit=10):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, event_type, message, created_at
                    FROM ash_host_events
                    ORDER BY id DESC
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()

    except Exception:
        logger.exception("تعذر تحميل سجل الأحداث")
        return []


# ==========================================
# تصميم الصفحة الرئيسية
# ==========================================

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ASH-HOST | الرئيسية</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b12;color:#f4f4ff;font-family:Arial,sans-serif}
header{padding:20px;background:#151426;border-bottom:1px solid #302b4b}
header h1{margin:0;color:#a99aff}
nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
nav a{color:#dcd8ff;text-decoration:none;padding:10px 12px;border-radius:10px;background:#24213a}
nav a:hover{background:#39305f}
main{max-width:1100px;margin:auto;padding:20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.card{background:#171626;border:1px solid #302b49;border-radius:16px;padding:20px}
.card small{color:#aaa5c7}
.number{font-size:27px;font-weight:bold;margin-top:12px;color:#75e3ee}
h2{font-size:20px;margin-top:28px}
table{width:100%;border-collapse:collapse;background:#171626}
th,td{text-align:right;padding:12px;border-bottom:1px solid #302b49;overflow-wrap:anywhere}
th{color:#aaa5c7}
.muted{color:#aaa5c7}
button{background:#7161e8;color:white;border:0;padding:10px 14px;border-radius:9px;cursor:pointer}
@media(max-width:520px){
    main{padding:12px}
    header{padding:16px}
    th,td{padding:8px;font-size:13px}
}
</style>
</head>
<body>
<header>
<h1>ASH-HOST</h1>
<p class="muted">لوحة إدارة بوتات تيليجرام</p>
<nav>
<a href="/">الرئيسية</a>
<a href="/files">مدير الملفات</a>
<a href="/bots">إدارة البوتات</a>
<a href="/logs">السجلات</a>
<form action="/logout" method="POST" style="margin:0">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button type="submit">تسجيل الخروج</button>
</form>
</nav>
</header>

<main>
<h2>نظرة عامة</h2>
<div class="cards">
<div class="card">
<small>الملفات المحفوظة</small>
<div class="number">{{ stats.files_count }}</div>
</div>
<div class="card">
<small>حجم الملفات</small>
<div class="number">{{ "%.2f"|format(stats.files_size / 1048576) }} MB</div>
</div>
<div class="card">
<small>حالة قاعدة البيانات</small>
<div class="number" style="font-size:20px">{{ stats.database_status }}</div>
</div>
<div class="card">
<small>الأحداث المسجلة</small>
<div class="number">{{ stats.events_count }}</div>
</div>
</div>

<h2>آخر الأحداث</h2>
<table>
<thead>
<tr><th>النوع</th><th>التفاصيل</th><th>الوقت</th></tr>
</thead>
<tbody>
{% for event in events %}
<tr>
<td>{{ event.event_type }}</td>
<td>{{ event.message }}</td>
<td>{{ event.created_at }}</td>
</tr>
{% else %}
<tr><td colspan="3">لا توجد أحداث مسجلة حتى الآن.</td></tr>
{% endfor %}
</tbody>
</table>

<p class="muted">الإحصائيات مبنية على البيانات المحفوظة.</p>
</main>
</body>
</html>
"""


# ==========================================
# مسار الصفحة الرئيسية
# يستبدل دالة index المؤقتة من الجزء الأول
# ==========================================

@app.route("/")
@admin_required
def index():
    return render_template_string(
        DASHBOARD_PAGE,
        stats=get_dashboard_stats(),
        events=get_recent_events(),
        csrf_token=generate_csrf_token(),
    )

# ==========================================
# ASH-HOST | إدارة البوتات والتواصل مع Worker
# ==========================================

import requests


def worker_request(method, endpoint, payload=None, timeout=15):
    if not WORKER_URL or not WORKER_SECRET:
        return {
            "ok": False,
            "error": "إعدادات Worker غير مكتملة.",
        }, 503

    endpoint = "/" + endpoint.lstrip("/")

    try:
        response = requests.request(
            method=method,
            url=WORKER_URL + endpoint,
            json=payload,
            headers={
                "X-Worker-Secret": WORKER_SECRET,
                "Accept": "application/json",
            },
            timeout=timeout,
        )

        try:
            data = response.json()
        except ValueError:
            data = {
                "ok": False,
                "error": "استجابة Worker غير صالحة.",
            }

        return data, response.status_code

    except requests.RequestException:
        logger.exception("تعذر الاتصال بخدمة Worker")

        return {
            "ok": False,
            "error": "تعذر الاتصال بخدمة تشغيل البوتات.",
        }, 502


# ==========================================
# صفحة إدارة البوتات
# ==========================================

BOTS_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>إدارة البوتات | ASH-HOST</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b12;color:#f4f4ff;font-family:Arial,sans-serif}
header{padding:20px;background:#151426;border-bottom:1px solid #302b4b}
h1{color:#a99aff;margin:0}
nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
nav a{color:#dcd8ff;text-decoration:none;padding:10px 12px;border-radius:10px;background:#24213a}
main{max-width:1000px;margin:auto;padding:20px}
.card{background:#171626;border:1px solid #302b49;border-radius:16px;padding:18px;margin:14px 0}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
select,input{padding:12px;border-radius:9px;border:1px solid #393650;background:#10101b;color:white;max-width:100%}
button{padding:11px 14px;border:0;border-radius:9px;color:white;cursor:pointer;background:#7161e8}
button.danger{background:#b83d5a}
button.success{background:#178b76}
.message{padding:12px;border-radius:10px;background:#24213a;margin:14px 0;overflow-wrap:anywhere}
.muted{color:#aaa5c7}
</style>
</head>
<body>
<header>
<h1>ASH-HOST</h1>
<p class="muted">إدارة وتشغيل البوتات</p>
<nav>
<a href="/">الرئيسية</a>
<a href="/files">مدير الملفات</a>
<a href="/bots">إدارة البوتات</a>
<a href="/logs">السجلات</a>
</nav>
</header>
<main>
<h2>التحكم في البوتات</h2>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<div class="card">
<h3>تشغيل بوت محفوظ</h3>
<form method="POST" action="/bots/start">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label for="file_id">ملف البوت:</label>
<select id="file_id" name="file_id" required>
<option value="">اختر ملفًا</option>
{% for file in files %}
<option value="{{ file.id }}">{{ file.filename }}</option>
{% endfor %}
</select>
<button class="success" type="submit">تشغيل</button>
</form>
<p class="muted">يجب إعداد Worker وتشغيله أولًا.</p>
</div>

<div class="card">
<h3>البوتات على Worker</h3>
<form method="GET" action="/bots">
<button type="submit">تحديث القائمة</button>
</form>
{% if worker_error %}
<p>{{ worker_error }}</p>
{% elif bots %}
{% for bot in bots %}
<div class="card">
<strong>{{ bot.get('filename', bot.get('file_id', 'بوت')) }}</strong>
<p>الحالة: {{ bot.get('status', 'غير معروفة') }}</p>
<div class="row">
<form method="POST" action="/bots/restart">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="file_id" value="{{ bot.get('file_id', '') }}">
<button type="submit">إعادة التشغيل</button>
</form>
<form method="POST" action="/bots/stop">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<input type="hidden" name="file_id" value="{{ bot.get('file_id', '') }}">
<button class="danger" type="submit">إيقاف</button>
</form>
<a href="/bots/logs/{{ bot.get('file_id', '') }}">عرض السجلات</a>
</div>
</div>
{% endfor %}
{% else %}
<p class="muted">لا توجد بوتات ظاهرة حاليًا أو أن Worker لم يرجع قائمة.</p>
{% endif %}
</div>
</main>
</body>
</html>
"""


def get_saved_files():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, filename, size_bytes
                    FROM ash_host_files
                    ORDER BY updated_at DESC
                """)
                return cur.fetchall()
    except Exception:
        logger.exception("تعذر جلب الملفات المحفوظة")
        return []


@app.route("/bots")
@admin_required
def bots_page():
    data, status = worker_request("GET", "/api/bots")

    bots = []
    worker_error = None

    if status == 200 and data.get("ok", True):
        bots = data.get("bots", [])
    else:
        worker_error = data.get(
            "error",
            "Worker غير متصل أو لم يرجع بيانات صحيحة.",
        )

    return render_template_string(
        BOTS_PAGE,
        files=get_saved_files(),
        bots=bots,
        worker_error=worker_error,
        message=request.args.get("message", ""),
        csrf_token=generate_csrf_token(),
    )


# ==========================================
# تشغيل بوت
# ==========================================

@app.route("/bots/start", methods=["POST"])
@admin_required
def start_bot():
    validate_csrf_token()

    file_id = request.form.get("file_id", "").strip()

    if not file_id:
        flash("اختار ملف البوت أولًا.")
        return redirect(url_for("bots_page"))

    data, status = worker_request(
        "POST",
        "/api/bots/start",
        {"file_id": file_id},
    )

    message = data.get("message") or data.get("error", "انتهى الطلب.")
    log_event("bot_start", f"{file_id}: {message}")

    return redirect(
        url_for("bots_page", message=message)
    )


# ==========================================
# إيقاف بوت
# ==========================================

@app.route("/bots/stop", methods=["POST"])
@admin_required
def stop_bot():
    validate_csrf_token()

    file_id = request.form.get("file_id", "").strip()

    data, status = worker_request(
        "POST",
        "/api/bots/stop",
        {"file_id": file_id},
    )

    message = data.get("message") or data.get("error", "انتهى الطلب.")
    log_event("bot_stop", f"{file_id}: {message}")

    return redirect(url_for("bots_page", message=message))


# ==========================================
# إعادة تشغيل بوت
# ==========================================

@app.route("/bots/restart", methods=["POST"])
@admin_required
def restart_bot():
    validate_csrf_token()

    file_id = request.form.get("file_id", "").strip()

    data, status = worker_request(
        "POST",
        "/api/bots/restart",
        {"file_id": file_id},
    )

    message = data.get("message") or data.get("error", "انتهى الطلب.")
    log_event("bot_restart", f"{file_id}: {message}")

    return redirect(url_for("bots_page", message=message))


# ==========================================
# عرض سجلات بوت محدد
# ==========================================

@app.route("/bots/logs/<file_id>")
@admin_required
def bot_logs(file_id):
    data, status = worker_request(
        "GET",
        "/api/bots/" + file_id + "/logs",
    )

    if status != 200:
        return (
            data.get("error", "تعذر جلب سجلات البوت."),
            status,
        )

    return (
        "<html lang='ar' dir='rtl'><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<body style='background:#0b0b12;color:#eee;font-family:monospace;padding:18px'>"
        "<h2>سجلات البوت</h2><pre style='white-space:pre-wrap;overflow-wrap:anywhere'>"
        + str(data.get("logs", ""))[:50000]
        + "</pre><a style='color:#9af' href='/bots'>رجوع</a></body></html>"
    )

# ==========================================
# ASH-HOST | مدير الملفات
# رفع وتنزيل وحذف ملفات البوتات
# ==========================================

from werkzeug.utils import secure_filename


FILES_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>مدير الملفات | ASH-HOST</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b12;color:#f4f4ff;font-family:Arial,sans-serif}
header{padding:20px;background:#151426;border-bottom:1px solid #302b4b}
h1{margin:0;color:#a99aff}
nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
nav a{color:#dcd8ff;text-decoration:none;padding:10px 12px;border-radius:10px;background:#24213a}
main{max-width:1000px;margin:auto;padding:20px}
.card{background:#171626;border:1px solid #302b49;border-radius:16px;padding:18px;margin-bottom:16px}
input[type=file]{display:block;width:100%;margin:14px 0;color:#ddd}
button,.btn{display:inline-block;padding:11px 14px;border:0;border-radius:9px;color:white;background:#7161e8;text-decoration:none;cursor:pointer;font-size:14px}
.danger{background:#b83d5a}
.success{background:#178b76}
.message{padding:12px;border-radius:10px;background:#24213a;margin:14px 0;overflow-wrap:anywhere}
.muted{color:#aaa5c7}
.file{border-bottom:1px solid #302b49;padding:16px 0}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.actions form{margin:0}
.filename{overflow-wrap:anywhere;font-weight:bold}
@media(max-width:520px){main{padding:12px}header{padding:16px}}
</style>
</head>
<body>
<header>
<h1>ASH-HOST</h1>
<p class="muted">مدير ملفات البوتات</p>
<nav>
<a href="/">الرئيسية</a>
<a href="/files">مدير الملفات</a>
<a href="/bots">إدارة البوتات</a>
<a href="/logs">السجلات</a>
</nav>
</header>

<main>
<h2>رفع ملف بوت جديد</h2>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<div class="card">
<form method="POST" action="/files/upload" enctype="multipart/form-data">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label for="botfile">اختار ملف Python بامتداد .py</label>
<input id="botfile" type="file" name="botfile" accept=".py" required>
<button class="success" type="submit">رفع وحفظ الملف</button>
</form>
<p class="muted">الحد الأقصى للملف 10 ميجابايت. الملفات تحفظ في قاعدة البيانات.</p>
</div>

<h2>الملفات المحفوظة ({{ files|length }})</h2>

<div class="card">
{% for file in files %}
<div class="file">
<div class="filename">{{ file.filename }}</div>
<p class="muted">
الحجم: {{ "%.2f"|format(file.size_bytes / 1048576) }} MB
<br>
آخر تعديل: {{ file.updated_at }}
</p>

<div class="actions">
<a class="btn" href="/files/download/{{ file.id }}">تنزيل</a>
<a class="btn" href="/editor/{{ file.id }}">فتح المحرر</a>

<form method="POST" action="/files/delete/{{ file.id }}"
onsubmit="return confirm('متأكد إنك عايز تحذف الملف؟');">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button class="danger" type="submit">حذف</button>
</form>
</div>
</div>
{% else %}
<p class="muted">مفيش ملفات محفوظة لحد دلوقتي.</p>
{% endfor %}
</div>
</main>
</body>
</html>
"""


# ==========================================
# عرض مدير الملفات
# ==========================================

@app.route("/files")
@admin_required
def files_page():
    message = request.args.get("message", "")

    return render_template_string(
        FILES_PAGE,
        files=get_saved_files(),
        message=message,
        csrf_token=generate_csrf_token(),
    )


# ==========================================
# رفع ملف Python وحفظه في PostgreSQL
# ==========================================

@app.route("/files/upload", methods=["POST"])
@admin_required
def upload_file():
    validate_csrf_token()

    uploaded = request.files.get("botfile")

    if not uploaded or not uploaded.filename:
        return redirect(
            url_for("files_page", message="اختار ملفًا أولًا.")
        )

    original_name = uploaded.filename
    filename = secure_filename(original_name)

    if not filename:
        return redirect(
            url_for("files_page", message="اسم الملف غير صالح.")
        )

    if not filename.lower().endswith(".py"):
        return redirect(
            url_for("files_page", message="مسموح برفع ملفات .py فقط.")
        )

    content = uploaded.read(10 * 1024 * 1024 + 1)

    if not content:
        return redirect(
            url_for("files_page", message="الملف فارغ.")
        )

    if len(content) > 10 * 1024 * 1024:
        return redirect(
            url_for("files_page", message="حجم الملف أكبر من 10 MB.")
        )

    file_id = str(uuid.uuid4())

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ash_host_files
                        (id, filename, content, size_bytes)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        file_id,
                        filename,
                        psycopg.Binary(content),
                        len(content),
                    ),
                )

            conn.commit()

        log_event(
            "file_upload",
            f"تم رفع الملف {filename} ({len(content)} bytes)",
        )

        logger.info("تم حفظ ملف جديد: %s", filename)

        return redirect(
            url_for("files_page", message="تم رفع الملف وحفظه بنجاح.")
        )

    except Exception:
        logger.exception("فشل رفع الملف إلى قاعدة البيانات")

        return redirect(
            url_for("files_page", message="فشل حفظ الملف. راجع سجلات الاستضافة.")
        )


# ==========================================
# تنزيل ملف محفوظ
# ==========================================

@app.route("/files/download/<file_id>")
@admin_required
def download_file(file_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT filename, content
                    FROM ash_host_files
                    WHERE id = %s
                    """,
                    (file_id,),
                )
                file_record = cur.fetchone()

        if not file_record:
            abort(404)

        content = file_record["content"]

        return send_file(
            io.BytesIO(bytes(content)),
            mimetype="text/x-python",
            as_attachment=True,
            download_name=file_record["filename"],
        )

    except Exception as exc:
        if getattr(exc, "code", None) == 404:
            raise

        logger.exception("فشل تنزيل الملف")
        return "تعذر تنزيل الملف.", 500


# ==========================================
# حذف ملف محفوظ
# ==========================================

@app.route("/files/delete/<file_id>", methods=["POST"])
@admin_required
def delete_file(file_id):
    validate_csrf_token()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT filename
                    FROM ash_host_files
                    WHERE id = %s
                    """,
                    (file_id,),
                )
                record = cur.fetchone()

                if not record:
                    return redirect(
                        url_for(
                            "files_page",
                            message="الملف المطلوب غير موجود.",
                        )
                    )

                cur.execute(
                    """
                    DELETE FROM ash_host_files
                    WHERE id = %s
                    """,
                    (file_id,),
                )

            conn.commit()

        log_event(
            "file_delete",
            f"تم حذف الملف {record['filename']}",
        )

        return redirect(
            url_for("files_page", message="تم حذف الملف.")
        )

    except Exception:
        logger.exception("فشل حذف الملف")

        return redirect(
            url_for("files_page", message="تعذر حذف الملف.")
        )

# ==========================================
# ASH-HOST | محرر الأكواد
# ==========================================

EDITOR_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>محرر الأكواد | ASH-HOST</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b12;color:#f4f4ff;font-family:Arial,sans-serif}
header{padding:18px;background:#151426;border-bottom:1px solid #302b4b}
h1{margin:0;color:#a99aff;font-size:25px}
nav{display:flex;gap:9px;flex-wrap:wrap;margin-top:15px}
nav a{color:#dcd8ff;text-decoration:none;padding:10px 12px;border-radius:9px;background:#24213a}
main{max-width:1200px;margin:auto;padding:18px}
.card{background:#171626;border:1px solid #302b49;border-radius:15px;padding:16px}
input,textarea{width:100%;padding:12px;border-radius:9px;border:1px solid #393650;background:#10101b;color:#eee;font-family:monospace}
input{margin:8px 0 14px}
textarea{min-height:55vh;resize:vertical;direction:ltr;text-align:left;white-space:pre;tab-size:4;font-size:14px;line-height:1.6}
button,.btn{display:inline-block;padding:11px 15px;border:0;border-radius:9px;color:white;background:#7161e8;text-decoration:none;cursor:pointer;font-size:14px}
.save{background:#178b76}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.muted{color:#aaa5c7;line-height:1.7}
.message{padding:12px;background:#24213a;border-radius:9px;margin-bottom:14px;overflow-wrap:anywhere}
@media(max-width:600px){main{padding:10px}header{padding:14px}textarea{min-height:50vh;font-size:13px}}
</style>
</head>
<body>
<header>
<h1>ASH-HOST</h1>
<p class="muted">محرر أكواد Python</p>
<nav>
<a href="/">الرئيسية</a>
<a href="/files">مدير الملفات</a>
<a href="/bots">إدارة البوتات</a>
<a href="/logs">السجلات</a>
</nav>
</header>

<main>
<div class="card">
<h2>تعديل الملف</h2>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<p class="muted">
اسم الملف: {{ filename }}<br>
التعديلات تُحفظ في قاعدة البيانات، ولا تُرفع تلقائيًا إلى GitHub.
</p>

<form method="POST" action="/editor/{{ file_id }}">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">

<label for="filename">اسم الملف</label>
<input id="filename" name="filename" value="{{ filename }}"
maxlength="120" required pattern="[A-Za-z0-9_.-]+">

<label for="content">محتوى الكود</label>
<textarea id="content" name="content" spellcheck="false"
autocapitalize="off" autocomplete="off" required>{{ content }}</textarea>

<div class="row">
<button class="save" type="submit" name="action" value="save">
حفظ التعديلات
</button>
<button type="submit" name="action" value="download">
تنزيل نسخة
</button>
<a class="btn" href="/files">رجوع للملفات</a>
</div>
</form>

<p class="muted">
راجع الكود قبل تشغيله. المحرر لا يشغّل البوت بمجرد الحفظ.
</p>
</div>
</main>
</body>
</html>
"""


# ==========================================
# فتح ملف داخل المحرر
# ==========================================

@app.route("/editor/<file_id>", methods=["GET", "POST"])
@admin_required
def editor_page(file_id):
    message = ""

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, content
                    FROM ash_host_files
                    WHERE id = %s
                    """,
                    (file_id,),
                )
                record = cur.fetchone()

        if not record:
            abort(404)

        filename = record["filename"]
        content_bytes = bytes(record["content"])
        content = content_bytes.decode("utf-8", errors="replace")

        if request.method == "POST":
            validate_csrf_token()

            action = request.form.get("action", "save")
            new_filename = secure_filename(
                request.form.get("filename", "").strip()
            )
            new_content = request.form.get("content", "")

            if not new_filename or not new_filename.lower().endswith(".py"):
                message = "اسم الملف لازم يكون صالحًا وينتهي بـ .py"

            elif len(new_content.encode("utf-8")) > 10 * 1024 * 1024:
                message = "حجم الكود أكبر من الحد المسموح (10 MB)."

            elif action == "download":
                return send_file(
                    io.BytesIO(new_content.encode("utf-8")),
                    mimetype="text/x-python",
                    as_attachment=True,
                    download_name=new_filename,
                )

            else:
                try:
                    with get_db() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE ash_host_files
                                SET filename = %s,
                                    content = %s,
                                    size_bytes = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                                """,
                                (
                                    new_filename,
                                    psycopg.Binary(
                                        new_content.encode("utf-8")
                                    ),
                                    len(new_content.encode("utf-8")),
                                    file_id,
                                ),
                            )

                            if cur.rowcount == 0:
                                abort(404)

                        conn.commit()

                    filename = new_filename
                    content = new_content
                    message = "تم حفظ التعديلات بنجاح."

                    log_event(
                        "file_edit",
                        f"تم تعديل الملف {filename}",
                    )

                except Exception:
                    logger.exception("فشل حفظ تعديلات الملف")
                    message = "تعذر حفظ التعديلات. راجع سجلات الاستضافة."

        return render_template_string(
            EDITOR_PAGE,
            file_id=file_id,
            filename=filename,
            content=content,
            message=message,
            csrf_token=generate_csrf_token(),
        )

    except Exception as exc:
        if getattr(exc, "code", None) == 404:
            raise

        logger.exception("تعذر فتح محرر الأكواد")
        return "تعذر فتح الملف. راجع سجلات الاستضافة.", 500

# ==========================================
# ASH-HOST | السجلات ومراقبة النظام
# ==========================================

import platform
import shutil
import psutil


LOGS_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>السجلات والموارد | ASH-HOST</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b12;color:#f4f4ff;font-family:Arial,sans-serif}
header{padding:18px;background:#151426;border-bottom:1px solid #302b4b}
h1{margin:0;color:#a99aff}
nav{display:flex;gap:9px;flex-wrap:wrap;margin-top:15px}
nav a{color:#dcd8ff;text-decoration:none;padding:10px 12px;border-radius:9px;background:#24213a}
main{max-width:1100px;margin:auto;padding:18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.card{background:#171626;border:1px solid #302b49;border-radius:15px;padding:17px;margin-bottom:14px}
.number{font-size:25px;color:#75e3ee;margin-top:10px}
.muted{color:#aaa5c7;line-height:1.7}
pre{background:#0a0a11;border:1px solid #302b49;border-radius:10px;padding:14px;white-space:pre-wrap;overflow-wrap:anywhere;direction:ltr;text-align:left;max-height:450px;overflow:auto}
input{width:100%;padding:12px;border-radius:9px;border:1px solid #393650;background:#10101b;color:white}
button{padding:11px 14px;border:0;border-radius:9px;color:white;background:#7161e8;cursor:pointer}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.message{padding:12px;background:#24213a;border-radius:9px;margin:12px 0}
</style>
</head>
<body>
<header>
<h1>ASH-HOST</h1>
<p class="muted">سجلات النظام ومراقبة الموارد</p>
<nav>
<a href="/">الرئيسية</a>
<a href="/files">مدير الملفات</a>
<a href="/bots">إدارة البوتات</a>
<a href="/logs">السجلات</a>
</nav>
</header>

<main>
<h2>موارد خادم لوحة التحكم</h2>
<p class="muted">
الأرقام التالية تخص خادم الويب نفسه، وليست بالضرورة موارد Worker.
</p>

<div class="cards">
<div class="card">
<div>استخدام المعالج</div>
<div class="number">{{ resources.cpu }}%</div>
</div>
<div class="card">
<div>استخدام الذاكرة</div>
<div class="number">{{ resources.ram }}%</div>
<p class="muted">{{ resources.ram_used }} / {{ resources.ram_total }} MB</p>
</div>
<div class="card">
<div>مساحة القرص المتاحة</div>
<div class="number">{{ resources.disk_free }} MB</div>
</div>
<div class="card">
<div>عدد العمليات الظاهرة</div>
<div class="number">{{ resources.processes }}</div>
</div>
</div>

<div class="card">
<h2>أحداث النظام</h2>
<form method="GET" action="/logs">
<button type="submit">تحديث السجلات</button>
</form>
<pre>{% for event in events %}[{{ event.created_at }}] [{{ event.event_type }}] {{ event.message }}
{% else %}لا توجد أحداث مسجلة.
{% endfor %}</pre>
</div>

<div class="card">
<h2>وحدة الأوامر المحدودة</h2>
<p class="muted">
الوحدة دي بتنفذ أوامر إدارية محددة فقط، ولا تتيح تنفيذ أوامر نظام التشغيل.
</p>
<form method="POST" action="/console">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<label for="command">الأمر</label>
<input id="command" name="command" placeholder="help" maxlength="30" required>
<div class="row"><button type="submit">تنفيذ</button></div>
</form>

{% if console_result is not none %}
<pre>{{ console_result }}</pre>
{% endif %}
</div>
</main>
</body>
</html>
"""


# ==========================================
# قراءة موارد خادم الويب
# ==========================================

def get_system_resources():
    try:
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")

        return {
            "cpu": round(psutil.cpu_percent(interval=0.1), 1),
            "ram": round(memory.percent, 1),
            "ram_used": round(memory.used / 1048576),
            "ram_total": round(memory.total / 1048576),
            "disk_free": round(disk.free / 1048576),
            "processes": len(psutil.pids()),
        }

    except Exception:
        logger.exception("تعذر قراءة موارد النظام")

        return {
            "cpu": 0,
            "ram": 0,
            "ram_used": 0,
            "ram_total": 0,
            "disk_free": 0,
            "processes": 0,
        }


# ==========================================
# صفحة السجلات والموارد
# ==========================================

@app.route("/logs")
@admin_required
def logs_page():
    return render_template_string(
        LOGS_PAGE,
        resources=get_system_resources(),
        events=get_recent_events(100),
        console_result=None,
        csrf_token=generate_csrf_token(),
    )


# ==========================================
# وحدة أوامر إدارية محدودة
# ==========================================

@app.route("/console", methods=["POST"])
@admin_required
def console_command():
    validate_csrf_token()

    command = request.form.get("command", "").strip().lower()

    allowed_commands = {
        "help": (
            "الأوامر المتاحة:\n"
            "help - عرض المساعدة\n"
            "status - حالة لوحة التحكم\n"
            "files - عدد الملفات المحفوظة\n"
            "bots - طلب قائمة البوتات من Worker\n"
            "clear - مسح شاشة النتائج فقط"
        ),
        "status": json.dumps(
            get_setting_status(),
            ensure_ascii=False,
            indent=2,
        ),
        "files": (
            "عدد الملفات المحفوظة: "
            + str(get_dashboard_stats()["files_count"])
        ),
    }

    if command == "bots":
        data, status = worker_request("GET", "/api/bots")

        if status == 200:
            result = json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
        else:
            result = data.get(
                "error",
                "تعذر الحصول على حالة البوتات.",
            )

    elif command == "clear":
        result = "تم مسح نتيجة الأمر. لم يتم حذف أي سجلات."

    elif command in allowed_commands:
        result = allowed_commands[command]

    else:
        result = (
            "الأمر غير مسموح.\n"
            "اكتب help لعرض قائمة الأوامر المتاحة."
        )

    log_event("console", f"تم تنفيذ الأمر الإداري: {command}")

    return render_template_string(
        LOGS_PAGE,
        resources=get_system_resources(),
        events=get_recent_events(100),
        console_result=result,
        csrf_token=generate_csrf_token(),
    )

# ==========================================
# ASH-HOST | الإعدادات وفحص الاتصال
# ==========================================

SETTINGS_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>الإعدادات | ASH-HOST</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0b12;color:#f4f4ff;font-family:Arial,sans-serif}
header{padding:18px;background:#151426;border-bottom:1px solid #302b4b}
h1{margin:0;color:#a99aff}
nav{display:flex;gap:9px;flex-wrap:wrap;margin-top:15px}
nav a{color:#dcd8ff;text-decoration:none;padding:10px 12px;border-radius:9px;background:#24213a}
main{max-width:1000px;margin:auto;padding:18px}
.card{background:#171626;border:1px solid #302b49;border-radius:15px;padding:18px;margin-bottom:14px}
.item{padding:13px 0;border-bottom:1px solid #302b49;overflow-wrap:anywhere}
.status{color:#75e3ee;font-weight:bold}
.muted{color:#aaa5c7;line-height:1.8}
button{padding:11px 14px;border:0;border-radius:9px;color:white;background:#7161e8;cursor:pointer}
.message{padding:12px;background:#24213a;border-radius:9px;margin:12px 0;overflow-wrap:anywhere}
</style>
</head>
<body>
<header>
<h1>ASH-HOST</h1>
<p class="muted">الإعدادات وحالة الخدمات</p>
<nav>
<a href="/">الرئيسية</a>
<a href="/files">مدير الملفات</a>
<a href="/bots">إدارة البوتات</a>
<a href="/logs">السجلات</a>
<a href="/settings">الإعدادات</a>
</nav>
</header>

<main>
<h2>إعدادات النظام</h2>

{% if message %}
<div class="message">{{ message }}</div>
{% endif %}

<div class="card">
<h3>حالة الإعدادات</h3>

{% for name, enabled in settings.items() %}
<div class="item">
<strong>{{ name }}</strong>:
<span class="status">{{ "مضبوط" if enabled else "غير مضبوط" }}</span>
</div>
{% endfor %}

<p class="muted">
القيم السرية لا يتم عرضها في هذه الصفحة.
غيّر كلمات المرور والأسرار من إعدادات متغيرات البيئة في الاستضافة.
</p>
</div>

<div class="card">
<h3>فحص الاتصال</h3>
<p class="muted">
يمكنك اختبار اتصال قاعدة البيانات وخدمة Worker دون كشف أسرار الاتصال.
</p>

<form method="POST" action="/settings/check">
<input type="hidden" name="csrf_token" value="{{ csrf_token }}">
<button type="submit">فحص الخدمات الآن</button>
</form>

{% if checks %}
{% for name, result in checks.items() %}
<div class="item">
<strong>{{ name }}</strong>:
<span class="status">{{ result }}</span>
</div>
{% endfor %}
{% endif %}
</div>

<div class="card">
<h3>معلومات التطبيق</h3>
<div class="item">اسم التطبيق: ASH-HOST</div>
<div class="item">الإصدار: 1.0.0</div>
<div class="item">قاعدة البيانات: PostgreSQL</div>
<div class="item">الحد الأقصى لرفع الملف: 10 MB</div>
</div>
</main>
</body>
</html>
"""


# ==========================================
# صفحة الإعدادات
# ==========================================

@app.route("/settings")
@admin_required
def settings_page():
    return render_template_string(
        SETTINGS_PAGE,
        settings=configuration_status(),
        checks=None,
        message=request.args.get("message", ""),
        csrf_token=generate_csrf_token(),
    )


# ==========================================
# فحص قاعدة البيانات وWorker
# ==========================================

@app.route("/settings/check", methods=["POST"])
@admin_required
def settings_check():
    validate_csrf_token()

    checks = {}

    # فحص قاعدة البيانات
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        checks["قاعدة البيانات"] = "متصلة"

    except Exception:
        logger.exception("فشل فحص قاعدة البيانات")
        checks["قاعدة البيانات"] = "فشل الاتصال"

    # فحص Worker إذا كانت إعداداته موجودة
    if WORKER_URL and WORKER_SECRET:
        data, status = worker_request(
            "GET",
            "/health",
            timeout=8,
        )

        if status == 200:
            checks["خدمة Worker"] = "متصلة"
        else:
            checks["خدمة Worker"] = data.get(
                "error",
                "غير متصلة أو أعادت خطأ",
            )
    else:
        checks["خدمة Worker"] = "الإعدادات غير مكتملة"

    log_event(
        "health_check",
        "تم تنفيذ فحص اتصال الخدمات.",
    )

    return render_template_string(
        SETTINGS_PAGE,
        settings=configuration_status(),
        checks=checks,
        message="انتهى فحص الاتصال.",
        csrf_token=generate_csrf_token(),
    )
