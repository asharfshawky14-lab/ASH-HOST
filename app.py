import os
import secrets
from datetime import timezone
import psycopg
from psycopg.rows import dict_row
from flask import Flask, request, jsonify, render_template_string, redirect, session, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE-URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

LOGIN = r"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>دخول ASH-HOST</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(ellipse at top,#241541,#090a12 60%);color:#f5f5ff;font-family:system-ui,Arial}.box{width:min(92vw,420px);background:#121421;border:1px solid #34304f;border-radius:20px;padding:26px}.logo{width:48px;height:48px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(135deg,#8b5cf6,#22d3ee);color:#080914;font-size:23px;font-weight:900}.box h1{font-size:22px;margin:15px 0 5px}.muted{color:#9296b2;font-size:13px;line-height:1.8}.field{width:100%;margin:17px 0 12px;padding:13px;border-radius:10px;background:#090a12;border:1px solid #34364d;color:white}.btn{width:100%;border:0;border-radius:10px;padding:12px;background:linear-gradient(100deg,#8b5cf6,#6d5dfc);color:white;font-weight:800}.err{color:#fecdd3;background:#351923;padding:10px;border-radius:8px;margin:10px 0;font-size:13px}</style><form class="box" method="post"><div class="logo">A</div><h1>تسجيل الدخول</h1><div class="muted">ASH-HOST · لوحة إدارة البوتات الخاصة</div>{% if error %}<div class="err">{{error}}</div>{% endif %}<label>كلمة مرور لوحة التحكم</label><input class="field" name="password" type="password" autocomplete="current-password" required autofocus><button class="btn">دخول آمن</button><p class="muted">أضف متغير البيئة ADMIN_PASSWORD في Hostless قبل الاستخدام.</p></form></html>"""

PAGE = r"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090a12"><title>ASH-HOST</title><style>
:root{--bg:#090a12;--panel:#121421;--line:#282b40;--purple:#8b5cf6;--cyan:#22d3ee;--text:#f5f5ff;--muted:#9296b2;--green:#4ade80}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 80% 0%,#17112c 0,transparent 38%),var(--bg);color:var(--text);font-family:system-ui,Arial}.layout{min-height:100vh}.side{position:fixed;right:0;top:0;bottom:0;width:230px;background:#0d0e18;border-left:1px solid var(--line);padding:20px 13px;display:flex;flex-direction:column}.brand{display:flex;gap:11px;align-items:center;padding:7px 8px 25px}.logo{width:42px;height:42px;border-radius:13px;background:linear-gradient(135deg,var(--purple),var(--cyan));display:grid;place-items:center;color:#090a12;font-weight:900;font-size:22px}.brand h2{margin:0;font-size:17px}.muted{color:var(--muted);font-size:12px}.nav{display:block;width:100%;padding:12px;margin:3px 0;text-align:right;border:1px solid transparent;border-radius:10px;background:none;color:#b8bbd2}.nav.active,.nav:hover{background:#201b36;border-color:#392b60;color:white}.main{margin-right:230px;padding:24px;max-width:1450px}.top{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:22px}.top h1{font-size:23px;margin:0}.status{color:var(--green);background:#10291f;border:1px solid #24553b;padding:8px 11px;border-radius:30px;font-size:12px}.hero{padding:23px;border:1px solid #38305d;border-radius:18px;background:radial-gradient(ellipse at 0% 0%,#34215a 0,transparent 55%),#141323;margin-bottom:17px}.hero h2{margin:0 0 9px}.hero p{font-size:13px;line-height:1.9;color:#c1bfd8;margin:0}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;min-width:0}.num{font-size:26px;font-weight:800;margin:10px 0}.section{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:23px 0 12px}.section h2{font-size:17px;margin:0}.btn,.secondary,.danger{border:0;border-radius:9px;padding:10px 13px;font-weight:700}.btn{background:linear-gradient(100deg,#8b5cf6,#6d5dfc);color:white}.secondary{background:#202235;border:1px solid #353850;color:white}.danger{background:#3a1724;border:1px solid #6b263b;color:#fecdd3}.toolbar{display:flex;gap:9px;flex-wrap:wrap;margin:12px 0}.field{background:#0d0f19;color:white;border:1px solid #34364d;border-radius:9px;padding:11px;min-width:0}.toolbar .field{flex:1}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:470px}td,th{text-align:right;padding:12px 8px;border-bottom:1px solid var(--line);font-size:12px}th{color:var(--muted)}.empty{text-align:center;padding:25px;color:var(--muted)}.notice{margin-top:13px;background:#201a32;border:1px solid #3d2b5c;padding:12px;border-radius:10px;color:#d8c7ff;font-size:12px;line-height:1.9}.page{display:none}.page.active{display:block}.flash{display:none;padding:10px;border-radius:9px;margin-bottom:12px;font-size:13px}.flash.show{display:block}.ok{background:#10291f;color:#86efac}.err{background:#351923;color:#fecdd3}@media(max-width:760px){.side{position:static;width:auto;height:auto;display:block;border-left:0;border-bottom:1px solid var(--line)}.side .nav{display:inline-block;width:auto}.main{margin:0;padding:15px 12px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.top h1{font-size:19px}}@media(max-width:430px){.grid{gap:8px}.card{padding:12px}.status{font-size:10px}}</style></head><body><div class="layout"><aside class="side"><div class="brand"><div class="logo">A</div><div><h2>ASH-HOST</h2><small class="muted">BOT HOSTING PANEL</small></div></div><button class="nav active" data-page="home">⌂　الرئيسية</button><button class="nav" data-page="bots">🤖　إدارة البوتات</button><button class="nav" data-page="files">📁　مدير الملفات</button><button class="nav" data-page="logs">▤　سجلات النظام</button><button class="nav" data-page="settings">⚙　الإعدادات</button><p class="muted">ASH-HOST v0.2</p></aside><main class="main"><header class="top"><div><h1 id="title">لوحة التحكم</h1><p class="muted">إدارة الاستضافة من مكان واحد</p></div><div><span class="status">● متصل</span> <button class="secondary" onclick="logout()">خروج</button></div></header><div id="flash" class="flash"></div>
<section class="page active" id="page-home"><div class="hero"><h2>أهلاً بيك في ASH-HOST 🚀</h2><p>لوحة خاصة لإدارة ملفات البوتات. حفظ الملفات في PostgreSQL وتسجيل الدخول أصبحا مفعّلين.</p></div><div class="grid"><div class="card"><div class="muted">ملفات البوتات</div><div class="num" id="count">—</div><div class="muted">محفوظة في قاعدة البيانات</div></div><div class="card"><div class="muted">حجم الملفات</div><div class="num" id="total">—</div><div class="muted">إجمالي الملفات المرفوعة</div></div><div class="card"><div class="muted">قاعدة البيانات</div><div class="num" id="dbstate" style="font-size:19px">جارٍ الفحص</div><div class="muted">اتصال فعلي من التطبيق</div></div></div><div class="section"><h2>ابدأ من هنا</h2><button class="btn" onclick="showPage('files')">رفع ملف +</button></div><div class="card"><div class="notice">النسخة دي تحفظ ملفات Python وتعرضها وتحذفها. تشغيل الكود المرفوع مش مفعّل لسه؛ هنضيفه من خلال Worker منفصل وآمن بدل تشغيل ملفات عشوائية داخل لوحة التحكم.</div></div></section>
<section class="page" id="page-bots"><div class="section"><h2>ملفات البوتات</h2><button class="btn" onclick="showPage('files')">إضافة ملف</button></div><div class="card"><div class="tablewrap"><table><thead><tr><th>الاسم</th><th>الحجم</th><th>تاريخ الرفع</th><th>الحالة</th></tr></thead><tbody id="botrows"></tbody></table></div></div><div class="notice">تشغيل وإيقاف البوتات هيتضاف بعد إعداد Worker مخصص.</div></section>
<section class="page" id="page-files"><div class="section"><h2>مدير الملفات</h2></div><div class="card"><form id="upload"><div class="toolbar"><input class="field" type="file" id="file" accept=".py" required><button class="btn">رفع وحفظ</button></div></form><p class="muted">ملفات .py فقط، بحد أقصى 10 ميجابايت للملف.</p><div class="tablewrap"><table><thead><tr><th>الاسم</th><th>الحجم</th><th>تاريخ الرفع</th><th>إجراء</th></tr></thead><tbody id="filerows"></tbody></table></div></div></section>
<section class="page" id="page-logs"><div class="section"><h2>سجلات النظام</h2><button class="secondary" onclick="refresh()">تحديث</button></div><div class="card" id="logs">جارٍ الفحص…</div></section>
<section class="page" id="page-settings"><div class="section"><h2>الإعدادات</h2></div><div class="card"><p>كلمة مرور اللوحة محفوظة في متغير البيئة <code>ADMIN_PASSWORD</code>.</p><p>اتصال PostgreSQL يقرأ <code>DATABASE_URL</code>.</p><button class="secondary" onclick="health()">فحص الاتصال</button><div class="notice" id="healthresult">اضغط فحص الاتصال.</div></div></section><p class="muted" style="text-align:center;padding:24px">ASH-HOST © 2026</p></main></div>
<script>
const titles={home:"لوحة التحكم",bots:"إدارة البوتات",files:"مدير الملفات",logs:"سجلات النظام",settings:"الإعدادات"};document.querySelectorAll(".nav").forEach(b=>b.onclick=()=>showPage(b.dataset.page));function showPage(n){document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));document.querySelectorAll(".nav").forEach(b=>b.classList.toggle("active",b.dataset.page===n));document.getElementById("page-"+n).classList.add("active");document.getElementById("title").textContent=titles[n];if(n==="files"||n==="bots")refresh()}
function flash(t,ok){let e=document.getElementById("flash");e.textContent=t;e.className="flash show "+(ok?"ok":"err");setTimeout(()=>e.classList.remove("show"),4500)}function fmt(n){return n<1024?n+" B":n<1048576?(n/1024).toFixed(1)+" KB":(n/1048576).toFixed(2)+" MB"}
async function req(url,opt={}){let r=await fetch(url,opt);if(r.status===401){location.href="/login";throw Error("سجّل الدخول من جديد")}let d=await r.json().catch(()=>({error:"استجابة غير مفهومة"}));if(!r.ok)throw Error(d.error||"حصل خطأ");return d}
function rows(items,id,del){let el=document.getElementById(id);el.innerHTML="";if(!items.length){el.innerHTML='<tr><td colspan="4" class="empty">لا توجد ملفات حتى الآن</td></tr>';return}items.forEach(x=>{let tr=document.createElement("tr");[x.filename,fmt(x.size),x.created_at].forEach(v=>{let td=document.createElement("td");td.textContent=v;tr.appendChild(td)});let td=document.createElement("td");if(del){let b=document.createElement("button");b.className="danger";b.textContent="حذف";b.onclick=async()=>{if(!confirm("حذف الملف "+x.filename+"؟"))return;try{await req("/api/files/"+x.id,{method:"DELETE"});flash("تم حذف الملف",true);refresh()}catch(e){flash(e.message,false)}};td.appendChild(b)}else td.textContent="محفوظ";tr.appendChild(td);el.appendChild(tr)})}
async function refresh(){try{let d=await req("/api/files");document.getElementById("count").textContent=d.files.length;document.getElementById("total").textContent=fmt(d.total_size);document.getElementById("dbstate").textContent="متصلة";rows(d.files,"filerows",true);rows(d.files,"botrows",false);document.getElementById("logs").textContent="الاتصال بقاعدة البيانات ناجح. عدد الملفات: "+d.files.length}catch(e){document.getElementById("dbstate").textContent="غير متاحة";document.getElementById("logs").textContent=e.message}}
document.getElementById("upload").onsubmit=async e=>{e.preventDefault();let f=document.getElementById("file").files[0];if(!f)return;let fd=new FormData();fd.append("file",f);try{let r=await fetch("/api/files",{method:"POST",body:fd});let d=await r.json();if(!r.ok)throw Error(d.error||"فشل الرفع");flash("تم حفظ "+d.filename,true);e.target.reset();refresh()}catch(x){flash(x.message,false)}};
async function health(){let el=document.getElementById("healthresult");try{let d=await req("/api/health");el.textContent=d.message}catch(e){el.textContent=e.message}}async function logout(){await fetch("/logout",{method:"POST"});location.href="/login"}refresh();
</script></body></html>"""

def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=8)

def schema():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS ash_host_files (
        id BIGSERIAL PRIMARY KEY, filename TEXT NOT NULL UNIQUE,
        size_bytes BIGINT NOT NULL, content BYTEA NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")

def logged_in():
    return session.get("logged_in") is True

@app.get("/health")
def health_route():
    try:
        with db() as conn: conn.execute("SELECT 1")
        return jsonify(status="ok", service="ASH-HOST", database="connected")
    except Exception:
        return jsonify(status="degraded", service="ASH-HOST", database="unavailable"), 503

@app.route("/login", methods=["GET","POST"])
def login():
    if not ADMIN_PASSWORD:
        return "Set ADMIN_PASSWORD in Hostless Environment Variables first.", 503
    error=None
    if request.method=="POST":
        if secrets.compare_digest(request.form.get("password",""), ADMIN_PASSWORD):
            session.clear(); session["logged_in"]=True
            return redirect(url_for("home"))
        error="كلمة المرور غير صحيحة."
    return render_template_string(LOGIN, error=error)

@app.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get("/")
def home():
    if not logged_in(): return redirect(url_for("login"))
    try: schema()
    except Exception: return "تعذر الاتصال بقاعدة البيانات. راجع DATABASE_URL في Hostless.",503
    return render_template_string(PAGE)

@app.get("/api/health")
def api_health():
    if not logged_in(): return jsonify(error="تسجيل الدخول مطلوب"),401
    try:
        with db() as conn: conn.execute("SELECT 1")
        return jsonify(database="متصلة",message="تم الاتصال بقاعدة البيانات بنجاح.")
    except Exception: return jsonify(error="تعذر الاتصال بقاعدة البيانات."),503

@app.get("/api/files")
def list_files():
    if not logged_in(): return jsonify(error="تسجيل الدخول مطلوب"),401
    try:
        schema()
        with db() as conn:
            records=conn.execute("SELECT id,filename,size_bytes,created_at FROM ash_host_files ORDER BY created_at DESC").fetchall()
        files=[{"id":r["id"],"filename":r["filename"],"size":r["size_bytes"],"created_at":r["created_at"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} for r in records]
        return jsonify(files=files,total_size=sum(f["size"] for f in files))
    except Exception: return jsonify(error="فشل قراءة الملفات من قاعدة البيانات."),503

@app.post("/api/files")
def upload_file():
    if not logged_in(): return jsonify(error="تسجيل الدخول مطلوب"),401
    f=request.files.get("file")
    if not f or not f.filename: return jsonify(error="اختار ملف الأول."),400
    name=secure_filename(f.filename)
    if not name.lower().endswith(".py"): return jsonify(error="المسموح ملفات .py فقط."),400
    content=f.read(10*1024*1024+1)
    if not content: return jsonify(error="الملف فارغ."),400
    if len(content)>10*1024*1024: return jsonify(error="حجم الملف أكبر من 10 ميجابايت."),413
    try:
        schema()
        with db() as conn:
            if conn.execute("SELECT id FROM ash_host_files WHERE filename=%s",(name,)).fetchone():
                return jsonify(error="يوجد ملف بنفس الاسم. احذف القديم أولًا أو غيّر الاسم."),409
            conn.execute("INSERT INTO ash_host_files(filename,size_bytes,content) VALUES(%s,%s,%s)",(name,len(content),psycopg.Binary(content)))
        return jsonify(ok=True,filename=name,size=len(content)),201
    except Exception: return jsonify(error="فشل حفظ الملف في قاعدة البيانات."),503

@app.delete("/api/files/<int:file_id>")
def delete_file(file_id):
    if not logged_in(): return jsonify(error="تسجيل الدخول مطلوب"),401
    try:
        with db() as conn: row=conn.execute("DELETE FROM ash_host_files WHERE id=%s RETURNING id",(file_id,)).fetchone()
        if not row: return jsonify(error="الملف غير موجود."),404
        return jsonify(ok=True)
    except Exception: return jsonify(error="فشل حذف الملف."),503

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","8000")))
