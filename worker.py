
import os
import sys
import time
import threading
import subprocess
import hmac
from collections import deque

import psycopg
import psutil
from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

WORKER_SECRET = os.environ.get("WORKER_SECRET", "")
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("DATABASE-URL", "")
)

BOT_DIRECTORY = os.environ.get(
    "BOT_DIRECTORY",
    "/tmp/ash-host-bots",
)

MAX_LOG_LINES = 500
MAX_BOT_PROCESSES = 10

os.makedirs(BOT_DIRECTORY, exist_ok=True)

processes = {}
process_logs = {}
process_lock = threading.RLock()


def authorized():
    supplied = request.headers.get("X-Worker-Secret", "")
    return bool(
        WORKER_SECRET
        and supplied
        and hmac.compare_digest(
            supplied,
            WORKER_SECRET,
        )
    )


@app.before_request
def check_authentication():
    if request.path == "/health":
        return None

    if not authorized():
        return jsonify({"error": "Unauthorized"}), 401

    return None


@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, HTTPException):
        return error

    app.logger.exception("Worker request failed")
    return jsonify({"error": "Internal worker error"}), 500


def database_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(
        DATABASE_URL,
        connect_timeout=10,
    )


def read_bot_file(file_id):
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename, content
                FROM ash_host_files
                WHERE id = %s
                """,
                (file_id,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "content": bytes(row[2]),
    }


def append_log(file_id, message):
    with process_lock:
        if file_id not in process_logs:
            process_logs[file_id] = deque(
                maxlen=MAX_LOG_LINES
            )

        process_logs[file_id].append(
            str(message).rstrip()
        )


def read_process_output(file_id, process):
    try:
        if process.stdout is None:
            return

        for line in iter(process.stdout.readline, ""):
            append_log(file_id, line)

    except Exception as exc:
        append_log(
            file_id,
            "Log reader error: " + str(exc),
        )


def process_status(file_id):
    process = processes.get(file_id)

    if process is None:
        return "stopped"

    if process.poll() is None:
        return "running"

    return "stopped"


def list_bots():
    with database_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filename
                FROM ash_host_files
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()

    result = []

    with process_lock:
        for file_id, filename in rows:
            result.append({
                "file_id": file_id,
                "filename": filename,
                "status": process_status(file_id),
            })

    return result


def start_bot(file_id):
    with process_lock:
        if process_status(file_id) == "running":
            return False, "البوت يعمل بالفعل"

        active = sum(
            1 for p in processes.values()
            if p.poll() is None
        )

        if active >= MAX_BOT_PROCESSES:
            return False, "تم الوصول للحد الأقصى للعمليات"

        bot = read_bot_file(file_id)

        if not bot:
            return False, "الملف غير موجود"

        filename = os.path.basename(bot["filename"])

        if not filename.endswith(".py"):
            return False, "يُسمح بملفات Python فقط"

        path = os.path.join(
            BOT_DIRECTORY,
            str(file_id) + "_" + filename,
        )

        with open(path, "wb") as f:
            f.write(bot["content"])

        append_log(file_id, "Starting " + filename)

        try:
            process = subprocess.Popen(
                [sys.executable, "-u", path],
                cwd=BOT_DIRECTORY,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                close_fds=True,
            )

            
            
            processes[file_id] = process

            thread = threading.Thread(
                target=read_process_output,
                args=(file_id, process),
                daemon=True,
            )
            thread.start()

            time.sleep(0.5)

            if process.poll() is not None:
                append_log(
                    file_id,
                    "Bot exited immediately after startup",
                )
                return False, (
                    "البوت توقف مباشرة بعد التشغيل. "
                    "راجع السجلات لمعرفة الخطأ."
                )

            return True, "بدأت عملية تشغيل البوت"

        except Exception:
            app.logger.exception("Failed to start bot")
            append_log(file_id, "Failed to start bot")
            return False, "فشل تشغيل البوت"


def stop_bot(file_id):
    with process_lock:
        process = processes.get(file_id)

        if process is None or process.poll() is not None:
            return False, "البوت متوقف بالفعل"

        try:
            process.terminate()

            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

            append_log(file_id, "Bot stopped")
            return True, "تم إيقاف البوت"

        except Exception:
            app.logger.exception("Failed to stop bot")
            return False, "فشل إيقاف البوت"


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "ASH-HOST Worker",
    })


@app.get("/api/bots")
def api_bots():
    try:
        return jsonify({"bots": list_bots()})
    except Exception:
        app.logger.exception("Could not list bots")
        return jsonify({
            "error": "تعذر جلب قائمة البوتات"
        }), 500


@app.post("/api/bots/start")
def api_start_bot():
    data = request.get_json(silent=True) or {}
    file_id = str(data.get("file_id", "")).strip()

    if not file_id:
        return jsonify({"error": "file_id مطلوب"}), 400

    ok, message = start_bot(file_id)

    return jsonify({
        "success": ok,
        "message": message,
    }), (200 if ok else 400)


@app.post("/api/bots/stop")
def api_stop_bot():
    data = request.get_json(silent=True) or {}
    file_id = str(data.get("file_id", "")).strip()

    if not file_id:
        return jsonify({"error": "file_id مطلوب"}), 400

    ok, message = stop_bot(file_id)

    return jsonify({
        "success": ok,
        "message": message,
    }), (200 if ok else 400)


@app.post("/api/bots/restart")
def api_restart_bot():
    data = request.get_json(silent=True) or {}
    file_id = str(data.get("file_id", "")).strip()

    if not file_id:
        return jsonify({"error": "file_id مطلوب"}), 400

    
    stopped, stop_message = stop_bot(file_id)

    if not stopped and process_status(file_id) == "running":
        return jsonify({
            "success": False,
            "message": "تعذر إيقاف البوت لإعادة تشغيله: " + stop_message,
        }), 400

    time.sleep(1)

    ok, message = start_bot(file_id)


    return jsonify({
        "success": ok,
        "message": message,
    }), (200 if ok else 400)


@app.get("/api/bots/<file_id>/logs")
def api_bot_logs(file_id):
    with process_lock:
        lines = list(process_logs.get(file_id, []))
        status = process_status(file_id)

    return jsonify({
        "file_id": file_id,
        "status": status,
        "logs": "\n".join(lines),
    })


@app.get("/api/resources")
def api_resources():
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        with process_lock:
            running = sum(
                1 for p in processes.values()
                if p.poll() is None
            )

        return jsonify({
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "running_bots": running,
        })

    except Exception:
        app.logger.exception("Resource check failed")
        return jsonify({
            "error": "تعذر قراءة موارد النظام"
        }), 500


if __name__ == "__main__":
    if not WORKER_SECRET:
        raise RuntimeError(
            "Set WORKER_SECRET in the environment"
        )

    if not DATABASE_URL:
        raise RuntimeError(
            "Set DATABASE_URL in the environment"
        )

    port = int(os.environ.get("PORT", "8001"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
