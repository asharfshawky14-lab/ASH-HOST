
import os
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

PAGE = r"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b0b12">
<title>ASH-HOST | لوحة الاستضافة</title>
<style>
:root {
  --bg:#090a12; --panel:#121421; --panel2:#191b2c;
  --border:#282b40; --purple:#8b5cf6; --cyan:#22d3ee;
  --text:#f5f5ff; --muted:#9296b2; --green:#4ade80;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
font-family:system-ui,-apple-system,Arial,sans-serif}
button,input{font:inherit}
button{cursor:pointer}
.layout{display:flex;min-height:100vh}
.sidebar{width:245px;background:#0d0e18;border-left:1px solid var(--border);
padding:22px 14px;position:fixed;right:0;top:0;bottom:0;z-index:10;
display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:12px;padding:8px 10px 25px}
.logo{width:43px;height:43px;border-radius:14px;
background:linear-gradient(135deg,var(--purple),var(--cyan));
display:grid;place-items:center;font-size:21px;font-weight:900;color:#080914}
.brand h2{font-size:17px;margin:0;letter-spacing:1px}
.brand small{color:var(--muted);font-size:11px}
.section-label{font-size:11px;color:var(--muted);padding:12px 12px 8px}
.nav{display:flex;align-items:center;gap:12px;width:100%;padding:12px;
border:1px solid transparent;border-radius:11px;background:transparent;
color:#b8bbd2;text-align:right;margin:3px 0;font-size:13px}
.nav:hover,.nav.active{background:#201b36;border-color:#392b60;color:#fff}
.nav.active{box-shadow:inset -3px 0 var(--purple)}
.nav-icon{width:23px;text-align:center;font-size:17px}
.sidebar-bottom{margin-top:auto;border-top:1px solid var(--border);
padding:15px 10px 0;color:var(--muted);font-size:11px;line-height:1.8}
.main{margin-right:245px;min-width:0;flex:1;padding:26px}
.topbar{display:flex;align-items:center;justify-content:space-between;
gap:14px;margin-bottom:28px}
.top-title{display:flex;align-items:center;gap:12px}
.top-title h1{font-size:23px;margin:0}
.top-title p{font-size:12px;color:var(--muted);margin:6px 0 0}
.icon-btn{display:none;background:var(--panel);border:1px solid var(--border);
color:white;border-radius:10px;padding:9px 12px}
.status{font-size:12px;background:#10291f;color:var(--green);
border:1px solid #24553b;padding:8px 12px;border-radius:30px;white-space:nowrap}
.welcome{padding:25px;border:1px solid #38305d;border-radius:19px;
background:radial-gradient(ellipse at 0% 0%,#34215a 0,transparent 55%),#141323;
margin-bottom:23px;position:relative;overflow:hidden}
.welcome h2{font-size:23px;margin:0 0 10px}
.welcome p{font-size:13px;color:#c1bfd8;line-height:1.9;margin:0 0 18px}
.primary{background:linear-gradient(100deg,#8b5cf6,#6d5dfc);
color:white;border:0;border-radius:10px;padding:11px 16px;font-weight:700}
.secondary{background:#202235;color:#e9e8ff;border:1px solid #353850;
border-radius:10px;padding:10px 14px}
.primary:hover,.secondary:hover{filter:brightness(1.13)}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--border);
border-radius:15px;padding:18px;min-width:0}
.stat-head{display:flex;align-items:center;justify-content:space-between;
color:var(--muted);font-size:12px;gap:8px}
.stat-icon{width:35px;height:35px;border-radius:11px;
display:grid;place-items:center;background:#24203a;color:#c4b5fd;font-size:18px}
.stat-number{font-size:27px;font-weight:800;margin:18px 0 7px}
.stat-note{font-size:11px;color:var(--muted)}
.green{color:var(--green)}
.section-head{display:flex;align-items:center;justify-content:space-between;
gap:12px;margin:27px 0 14px}
.section-head h2{font-size:17px;margin:0}
.section-head p{font-size:12px;color:var(--muted);margin:6px 0 0}
.content-grid{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:15px}
.empty{text-align:center;padding:28px 12px}
.empty .big{font-size:34px;margin-bottom:10px}
.empty h3{font-size:15px;margin:0 0 8px}
.empty p{font-size:12px;color:var(--muted);line-height:1.8;margin:0 auto 17px;max-width:300px}
.feature-list{display:grid;gap:13px}
.feature{display:flex;gap:12px;align-items:center}
.feature-icon{width:39px;height:39px;flex-shrink:0;border-radius:11px;
background:#202038;display:grid;place-items:center;font-size:18px}
.feature strong{font-size:13px;display:block;margin-bottom:5px}
.feature span{font-size:11px;color:var(--muted);line-height:1.6}
.notice{font-size:12px;color:#d8c7ff;line-height:1.9;
background:#201a32;border:1px solid #3d2b5c;padding:13px;border-radius:12px;margin-top:15px}
.page{display:none}.page.active{display:block}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;margin:15px 0}
.search{flex:1;min-width:180px;background:var(--panel);border:1px solid var(--border);
border-radius:10px;padding:11px;color:white}
.placeholder{border:1px dashed #383b54;border-radius:14px;padding:28px 15px;
text-align:center;color:var(--muted);line-height:1.9;font-size:13px}
.terminal{background:#07090e;border:1px solid #303148;border-radius:14px;
padding:17px;direction:ltr;text-align:left;color:#8ff5b1;font:13px monospace;
min-height:170px;line-height:1.9;overflow-wrap:anywhere}
.terminal-input{display:flex;gap:8px;margin-top:12px}
.terminal-input input{min-width:0;flex:1;background:#10121c;border:1px solid var(--border);
border-radius:9px;padding:11px;color:white;direction:ltr}
.footer{font-size:11px;color:var(--muted);text-align:center;padding:28px 0 10px}
.overlay{display:none}
@media(max-width:1000px){
 .grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .content-grid{grid-template-columns:1fr}
}
@media(max-width:700px){
 .sidebar{transform:translateX(100%);transition:transform .22s ease;width:260px}
 .sidebar.open{transform:translateX(0)}
 .overlay.show{display:block;position:fixed;inset:0;background:#0009;z-index:9}
 .main{margin-right:0;padding:17px 13px}
 .icon-btn{display:inline-block}
 .top-title h1{font-size:19px}
 .topbar{margin-bottom:19px}
 .welcome{padding:21px 17px}
 .welcome h2{font-size:20px}
 .grid{gap:9px}
 .card{padding:13px}
 .stat-number{font-size:23px}
 .stat-head{font-size:11px}
 .status{font-size:10px;padding:7px 9px}
}
</style>
</head>
<body>
<div class="overlay" id="overlay" onclick="toggleMenu()"></div>
<div class="layout">
<aside class="sidebar" id="sidebar">
  <div class="brand">
    <div class="logo">A</div>
    <div><h2>ASH-HOST</h2><small>BOT HOSTING PANEL</small></div>
  </div>
  <div class="section-label">القائمة الرئيسية</div>
  <button class="nav active" data-page="home"><span class="nav-icon">⌂</span>الرئيسية</button>
  <button class="nav" data-page="bots"><span class="nav-icon">🤖</span>إدارة البوتات</button>
  <button class="nav" data-page="files"><span class="nav-icon">📁</span>مدير الملفات</button>
  <button class="nav" data-page="terminal"><span class="nav-icon">⌘</span>Terminal</button>
  <div class="section-label">الأدوات والإعدادات</div>
  <button class="nav" data-page="logs"><span class="nav-icon">▤</span>سجلات التشغيل</button>
  <button class="nav" data-page="resources"><span class="nav-icon">◫</span>الموارد</button>
  <button class="nav" data-page="settings"><span class="nav-icon">⚙</span>الإعدادات</button>
  <div class="sidebar-bottom">ASH-HOST v0.1<br>واجهة لوحة التحكم الأولية</div>
</aside>

<main class="main">
<header class="topbar">
  <div class="top-title">
    <button class="icon-btn" onclick="toggleMenu()">☰</button>
    <div><h1 id="pageTitle">لوحة التحكم</h1><p>إدارة الاستضافة من مكان واحد</p></div>
  </div>
  <div class="status">● التطبيق متصل</div>
</header>

<section class="page active" id="page-home">
  <div class="welcome">
    <h2>أهلاً بيك في ASH-HOST 🚀</h2>
    <p>لوحتك الخاصة لإدارة البوتات والملفات وبيئة التشغيل.<br>
    هنضيف الوظائف الفعلية تدريجياً ونختبر كل جزء قبل الاعتماد عليه.</p>
    <button class="primary" onclick="showPage('bots')">ابدأ إدارة البوتات ←</button>
  </div>
  <div class="grid">
    <div class="card"><div class="stat-head"><span>إجمالي البوتات</span><span class="stat-icon">🤖</span></div><div class="stat-number">0</div><div class="stat-note">لم تتم إضافة بوتات بعد</div></div>
    <div class="card"><div class="stat-head"><span>البوتات العاملة</span><span class="stat-icon">▶</span></div><div class="stat-number green">0</div><div class="stat-note">ستظهر الحالة بعد الربط</div></div>
    <div class="card"><div class="stat-head"><span>الملفات</span><span class="stat-icon">📁</span></div><div class="stat-number">0</div><div class="stat-note">لم تتم إضافة ملفات</div></div>
    <div class="card"><div class="stat-head"><span>حالة اللوحة</span><span class="stat-icon">✦</span></div><div class="stat-number" style="font-size:20px">Online</div><div class="stat-note">واجهة الويب تعمل</div></div>
  </div>
  <div class="section-head"><div><h2>الوصول السريع</h2><p>انتقل إلى الوظيفة المطلوبة</p></div></div>
  <div class="content-grid">
    <div class="card">
      <div class="feature-list">
        <div class="feature"><div class="feature-icon">⬆</div><div><strong>رفع ملفات البوتات</strong><span>تجهيز مساحة مخصصة لملفات Python.</span></div></div>
        <div class="feature"><div class="feature-icon">⌘</div><div><strong>شاشة الأوامر</strong><span>واجهة Terminal بانتظار ربطها بخلفية آمنة.</span></div></div>
        <div class="feature"><div class="feature-icon">▤</div><div><strong>سجلات التشغيل</strong><span>مكان لمتابعة رسائل التشغيل والأخطاء.</span></div></div>
      </div>
    </div>
    <div class="card">
      <h3 style="font-size:14px;margin-top:0">حالة المشروع</h3>
      <div class="feature"><div class="feature-icon">✓</div><div><strong class="green">واجهة الويب جاهزة للاختبار</strong><span>تم نشر التطبيق الأساسي على Hostless.</span></div></div>
      <div class="notice">تنبيه: ظهور الواجهة لا يعني أن تشغيل البوتات أو الأوامر أصبح مفعّلاً. سنربط كل وظيفة بالخلفية ونختبرها قبل استخدامها.</div>
    </div>
  </div>
</section>

<section class="page" id="page-bots">
  <div class="section-head"><div><h2>إدارة البوتات</h2><p>رفع ملفات البوتات وإدارة تشغيلها</p></div></div>
  <div class="card">
    <div class="empty"><div class="big">🤖</div><h3>لسه مفيش بوتات</h3><p>هنضيف رفع ملفات Python والتشغيل والإيقاف ومتابعة الحالة بعد إعداد خدمة التشغيل الخلفية.</p><button class="primary" onclick="showPage('files')">الانتقال لمدير الملفات</button></div>
  </div>
  <div class="notice">الأزرار الفعلية للتشغيل ستُفعّل بعد إنشاء خدمة آمنة لعزل عمليات كل بوت.</div>
</section>

<section class="page" id="page-files">
  <div class="section-head"><div><h2>مدير الملفات</h2><p>مساحة ملفات البوتات</p></div></div>
  <div class="card">
    <div class="placeholder">📂<br><strong style="color:white">مساحة الملفات غير مفعّلة بعد</strong><br>هنضيف الرفع والحفظ والتعديل والحذف بعد إعداد التخزين الخلفي والصلاحيات.</div>
  </div>
</section>

<section class="page" id="page-terminal">
  <div class="section-head"><div><h2>Terminal</h2><p>واجهة الأوامر — وضع المعاينة</p></div></div>
  <div class="card">
    <div class="terminal">ASH-HOST Console v0.1<br>Web interface loaded successfully.<br>Backend command execution is not configured.<br><span style="color:#b6a4ff">Safe preview mode.</span></div>
    <div class="terminal-input"><input disabled placeholder="الأوامر غير مفعّلة حتى إعداد الخلفية الآمنة"><button class="secondary" disabled>تنفيذ</button></div>
    <div class="notice">لن نشغّل أوامر النظام مباشرة من المتصفح. سنربط Terminal بخدمة خلفية محدودة الصلاحيات لحماية ملفاتك وأسرار البوتات.</div>
  </div>
</section>

<section class="page" id="page-logs">
  <div class="section-head"><div><h2>سجلات التشغيل</h2><p>الأحداث والأخطاء</p></div></div>
  <div class="card"><div class="placeholder">▤<br><strong style="color:white">لا توجد سجلات بعد</strong><br>ستظهر هنا سجلات التشغيل بعد ربط خدمة البوتات.</div></div>
</section>

<section class="page" id="page-resources">
  <div class="section-head"><div><h2>الموارد</h2><p>مراقبة استهلاك بيئة الاستضافة</p></div></div>
  <div class="grid">
    <div class="card"><div class="stat-head">المعالج CPU</div><div class="stat-number">—</div><div class="stat-note">بانتظار مصدر قياس فعلي</div></div>
    <div class="card"><div class="stat-head">الذاكرة RAM</div><div class="stat-number">—</div><div class="stat-note">بانتظار مصدر قياس فعلي</div></div>
    <div class="card"><div class="stat-head">التخزين</div><div class="stat-number">—</div><div class="stat-note">بانتظار مصدر قياس فعلي</div></div>
    <div class="card"><div class="stat-head">عدد العمليات</div><div class="stat-number">—</div><div class="stat-note">بانتظار خدمة التشغيل</div></div>
  </div>
  <div class="notice">لن نعرض أرقام موارد وهمية. القياسات ستُربط بمصدر حقيقي عندما تتيحه بيئة التشغيل.</div>
</section>

<section class="page" id="page-settings">
  <div class="section-head"><div><h2>الإعدادات</h2><p>إعدادات لوحة ASH-HOST</p></div></div>
  <div class="card">
    <div class="feature-list">
      <div class="feature"><div class="feature-icon">🔐</div><div><strong>الحماية وتسجيل الدخول</strong><span>يجب إضافة مصادقة قبل السماح بإدارة الملفات أو تشغيل الأوامر.</span></div></div>
      <div class="feature"><div class="feature-icon">🔑</div><div><strong>متغيرات البيئة والأسرار</strong><span>ستُخزّن في الخلفية، ولن تظهر قيمها الحساسة في الواجهة.</span></div></div>
      <div class="feature"><div class="feature-icon">💾</div><div><strong>النسخ الاحتياطي</strong><span>سيُضاف بعد تحديد مكان التخزين الدائم المتاح.</span></div></div>
    </div>
  </div>
</section>

<div class="footer">ASH-HOST © 2026 · لوحة إدارة الاستضافة</div>
</main>
</div>
<script>
const titles = {
  home:"لوحة التحكم", bots:"إدارة البوتات", files:"مدير الملفات",
  terminal:"Terminal", logs:"سجلات التشغيل", resources:"الموارد",
  settings:"الإعدادات"
};
function showPage(name){
  document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
  document.querySelectorAll(".nav").forEach(b=>b.classList.toggle("active",b.dataset.page===name));
  const page=document.getElementById("page-"+name);
  if(page) page.classList.add("active");
  document.getElementById("pageTitle").textContent=titles[name]||"ASH-HOST";
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("overlay").classList.remove("show");
  window.scrollTo({top:0,behavior:"smooth"});
}
function toggleMenu(){
  document.getElementById("sidebar").classList.toggle("open");
  document.getElementById("overlay").classList.toggle("show");
}
document.querySelectorAll(".nav").forEach(button=>{
  button.addEventListener("click",()=>showPage(button.dataset.page));
});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(PAGE)

@app.route("/health")
def health():
    return jsonify(status="ok", service="ASH-HOST", mode="dashboard-preview")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
