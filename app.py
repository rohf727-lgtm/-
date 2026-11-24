from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
import re
import string
import threading
import time
from flask import Flask, Response, jsonify, render_template_string, request
import requests
from requests.adapters import HTTPAdapter

app = Flask(__name__)

MAX_USERNAMES = 50000
MAX_UI_ITEMS = 1000
MAX_WORKERS = 25

lock = threading.Lock()
state = {
    "running": False,
    "stop": False,
    "platform": "tiktok",
    "done": 0,
    "total": 0,
    "elapsed": 0.0,
    "rate": 0.0,
    "eta": 0.0,
    "available": 0,
    "taken": 0,
    "blocked": 0,
    "retries_used": 0,
    "last_error": "",
    "available_list": [],
    "blocked_list": [],
    "items": [],
}

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>صائد يوزرات — النسخة المتكاملة</title>
<style>
*{box-sizing:border-box}
body{background:#000;color:#f3f4f6;font-family:Tahoma,sans-serif;margin:0;padding:12px}
.gate{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;padding:14px;z-index:99}
.gate.hide{display:none}
.gbox{width:100%;max-width:360px;background:#070709;border:1px solid #3d0d13;border-radius:16px;padding:20px;text-align:center;box-shadow:0 0 40px rgba(220,38,38,.28)}
.gbox h3{margin:0 0 8px;color:#ef4444;font-size:19px}
.gbox p{margin:0 0 12px;color:#9ca3af;font-size:12px}
.gbox input{text-align:center;letter-spacing:4px;font-weight:bold}
.gbox button{width:100%;margin-top:10px;padding:10px;border-radius:9px;border:none;background:#dc2626;color:#fff;font-weight:bold;cursor:pointer}
.gerr{color:#f87171;font-size:12px;min-height:16px;margin-top:8px}
.wrap{max-width:820px;margin:8px auto;background:#070709;border:1px solid #3d0d13;border-radius:16px;padding:16px;box-shadow:0 0 40px rgba(220,38,38,.2)}
h2{margin:0 0 12px;text-align:center;color:#ef4444;font-size:21px}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.tab{padding:9px;border-radius:10px;border:1px solid #26262b;background:#0e0e12;color:#d1d5db;font-weight:bold;cursor:pointer}
.tab.active{background:#dc2626;border-color:#ef4444;color:#fff}
.pbox{display:none;background:#0c0c10;border:1px solid #1f1f26;border-radius:10px;padding:10px;margin-bottom:10px;font-size:12px;color:#9ca3af;line-height:1.6}
.pbox.active{display:block}
.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.row3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
label{display:block;margin-top:8px;font-size:12px;color:#e5e7eb}
input,select,textarea{width:100%;margin-top:4px;padding:8px 10px;border-radius:8px;border:1px solid #26262b;background:#050507;color:#fff;font-size:13px;font-family:Tahoma,sans-serif}
textarea{min-height:74px;resize:vertical}
.checks{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.chk{display:flex;align-items:center;gap:6px;margin-top:4px;font-size:12px;color:#d1d5db}
.chk input{width:auto;margin:0}
.btns{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:8px;margin-top:12px}
button{padding:9px 12px;border-radius:9px;border:none;font-weight:bold;cursor:pointer}
.main{background:#dc2626;color:#fff}
.sec{background:#18181b;color:#f3f4f6}
.ftab{padding:5px 9px;font-size:11px;border-radius:7px;background:#141418;color:#9ca3af;border:1px solid #23232a}
.ftab.active{background:#dc2626;color:#fff;border-color:#ef4444}
.link-btn{display:inline-block;margin-top:8px;padding:6px 10px;border-radius:8px;background:#18181b;color:#f87171;text-decoration:none;font-size:12px;border:1px solid #331317}
button:disabled{opacity:.45;cursor:not-allowed}
.bar-bg{margin-top:10px;height:10px;background:#141418;border-radius:999px;overflow:hidden}
.bar{height:100%;width:0%;background:linear-gradient(90deg,#7f1d1d,#dc2626,#ef4444);transition:width .18s}
.stats{margin-top:8px;font-size:12px;color:#d1d5db;line-height:1.7}
.err{margin-top:6px;font-size:12px;color:#f87171;min-height:16px}
.sec-box{margin-top:12px;background:#0c0c10;border:1px solid #1f1f26;border-radius:10px;padding:10px}
.grid{display:flex;flex-wrap:wrap;gap:6px;max-height:180px;overflow-y:auto;margin-top:8px}
.chip{background:rgba(34,197,94,.14);border:1px solid rgba(74,222,128,.4);color:#4ade80;padding:4px 8px;border-radius:7px;font-size:12px;cursor:pointer}
.logs{max-height:250px;overflow-y:auto;font-size:12px;margin-top:8px;line-height:1.6}
.ok{color:#4ade80}
.taken{color:#f87171}
.warn{color:#facc15}
.msg{color:#4ade80;font-size:12px;min-height:16px;margin-top:6px}
.hidden{display:none}
@media(max-width:600px){.row,.row3,.btns,.checks{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="gate" id="gate">
  <form class="gbox" id="gform">
    <h3>رمز الدخول</h3>
    <p>أدخل الرقم السري للدخول إلى الموقع</p>
    <input type="password" inputmode="numeric" id="pin" maxlength="12" placeholder="****" required>
    <button type="submit">دخول</button>
    <div class="gerr" id="gerr"></div>
  </form>
</div>

<div class="wrap">
  <h2>صائد يوزرات تيك • يوتيوب • ديسكورد</h2>
  <div class="tabs">
    <button type="button" class="tab active" data-p="tiktok">تيك توك</button>
    <button type="button" class="tab" data-p="youtube">يوتيوب</button>
    <button type="button" class="tab" data-p="discord">ديسكورد</button>
  </div>

  <div class="pbox active" id="p-tiktok">محرك فحص متقدم لـ TikTok مع تدوير ترويسات وتحقق مزدوج وتصفية صفحات الحجب والقيود. راجع اليوزر داخل التطبيق قبل اعتماده.</div>
  <div class="pbox" id="p-youtube">محرك فحص متقدم لمعرفات YouTube (@Handle) مع قراءة مؤشرات القناة وتأكيد النتائج بدقة عالية.</div>
  <div class="pbox" id="p-discord">
    محرك فحص متقدم لأسماء Discord عبر فحصين متتابعين بدون تغيير تلقائي للحساب. اضغط على اليوزر المتاح لنسخه وتغييره يدوياً.
    <div class="row">
      <div><label>يوزر حسابك (اختياري للتذكير)</label><input type="text" id="dc_user" placeholder="مثال: my_user"></div>
      <div><label>طريقة التغيير</label><input type="text" value="نسخ وتغيير يدوي آمن" readonly></div>
    </div>
    <a class="link-btn" href="https://discord.com/channels/@me" target="_blank" rel="noopener noreferrer">فتح ديسكورد لتغيير اليوزر يدوياً</a>
  </div>

  <form id="f">
    <div class="row3">
      <div><label>الطول (2 - 16)</label><input type="number" id="length" min="2" max="16" value="4" required></div>
      <div><label>العدد (1 - 50000)</label><input type="number" id="count" min="1" max="50000" value="500" required></div>
      <div><label>السرعة / العمال (1 - 25)</label><input type="number" id="workers" min="1" max="25" value="12" required></div>
    </div>
    <div class="row">
      <div><label>بداية اليوزر</label><input type="text" id="prefix" maxlength="8" placeholder="اختياري مثل: x_ أو ntr"></div>
      <div><label>نهاية اليوزر</label><input type="text" id="suffix" maxlength="8" placeholder="اختياري مثل: _x أو 99"></div>
    </div>
    <div class="row">
      <div>
        <label>النوع</label>
        <select id="mode">
          <option value="alnum">حروف وأرقام</option>
          <option value="alpha">حروف فقط</option>
          <option value="underscore">حروف وأرقام و _</option>
          <option value="dots">حروف وأرقام و .</option>
          <option value="syllable">مقاطع نطقية + أرقام</option>
          <option value="short_sharp">مقاطع قصيرة حادة</option>
          <option value="stylish_tags">تنسيقات وتكرارات مميزة</option>
          <option value="digits">أرقام فقط</option>
          <option value="custom_list">قائمة يوزرات جاهزة يدوياً</option>
        </select>
      </div>
      <div>
        <label>تأخير خفيف إضافي (مللي ثانية)</label>
        <input type="number" id="jitter_ms" min="0" max="500" value="25">
      </div>
    </div>

    <div id="customListBox" class="hidden">
      <label>أدخل قائمة اليوزرات (كل يوزر في سطر أو مفصول بفاصلة/مسافة)</label>
      <textarea id="custom_list" placeholder="example_1&#10;test.user&#10;short_tag"></textarea>
    </div>

    <div class="checks">
      <label class="chk"><input type="checkbox" id="sound" checked> تنبيه صوتي عند صيد يوزر متاح</label>
      <label class="chk"><input type="checkbox" id="auto_retry" checked> إعادة فحص المقيد تلقائياً مرة واحدة</label>
    </div>

    <div class="btns">
      <button type="submit" class="main" id="startBtn">بدء الفحص</button>
      <button type="button" class="sec" id="stopBtn" disabled>إيقاف</button>
      <button type="button" class="sec" id="retryBtn" disabled>إعادة المقيد</button>
      <button type="button" class="sec" id="clearBtn">مسح</button>
    </div>
  </form>

  <div class="bar-bg"><div class="bar" id="bar"></div></div>
  <div class="stats" id="info">جاهز.</div>
  <div class="err" id="errBox"></div>

  <div class="sec-box">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap">
      <span style="color:#f87171;font-size:13px;font-weight:bold">اليوزرات المتاحة المؤكدة (اضغط للنسخ)</span>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <button type="button" class="sec" id="copyAll">نسخ الكل (@)</button>
        <button type="button" class="sec" id="copyRaw">نسخ بدون @</button>
        <a id="exp" href="/export?platform=tiktok"><button type="button" class="sec">تصدير TXT</button></a>
      </div>
    </div>
    <div class="msg" id="msg"></div>
    <div class="grid" id="grid"></div>
  </div>

  <div class="sec-box">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap">
      <span style="color:#f87171;font-size:13px;font-weight:bold">سجل الفحص المباشر</span>
      <div style="display:flex;gap:5px">
        <button type="button" class="ftab active" data-flt="all">الكل</button>
        <button type="button" class="ftab" data-flt="available">المتاح</button>
        <button type="button" class="ftab" data-flt="taken">المأخوذ</button>
        <button type="button" class="ftab" data-flt="blocked">المقيد</button>
      </div>
    </div>
    <div class="logs" id="logs"></div>
  </div>
</div>

<script>
const gate=document.getElementById('gate'),gform=document.getElementById('gform'),pin=document.getElementById('pin'),gerr=document.getElementById('gerr');
if(sessionStorage.getItem('auth2007')==='1'){gate.classList.add('hide');}
gform.onsubmit=e=>{e.preventDefault();if(pin.value.trim()==='2007'){sessionStorage.setItem('auth2007','1');gate.classList.add('hide');gerr.textContent='';}else{gerr.textContent='الرمز غير صحيح';pin.value='';pin.focus();}};

let plat='tiktok',flt='all',avail=[],lastItems=[],lastAvailCount=0,timer=null;
const startBtn=document.getElementById('startBtn'),stopBtn=document.getElementById('stopBtn'),retryBtn=document.getElementById('retryBtn'),clearBtn=document.getElementById('clearBtn'),f=document.getElementById('f'),bar=document.getElementById('bar'),info=document.getElementById('info'),errBox=document.getElementById('errBox'),grid=document.getElementById('grid'),logs=document.getElementById('logs'),msg=document.getElementById('msg'),sound=document.getElementById('sound'),autoRetry=document.getElementById('auto_retry'),modeSel=document.getElementById('mode'),customListBox=document.getElementById('customListBox');

modeSel.onchange=()=>{
  customListBox.classList.toggle('hidden', modeSel.value !== 'custom_list');
};

function beep(){
  if(!sound.checked)return;
  try{
    const ctx=new(window.AudioContext||window.webkitAudioContext)(),o=ctx.createOscillator(),g=ctx.createGain();
    o.type='triangle';o.frequency.value=1040;g.gain.value=0.1;o.connect(g);g.connect(ctx.destination);o.start();
    setTimeout(()=>{o.stop();ctx.close();},140);
  }catch{}
}

document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{
  plat=b.dataset.p;
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x===b));
  document.querySelectorAll('.pbox').forEach(x=>x.classList.remove('active'));
  document.getElementById('p-'+plat).classList.add('active');
  document.getElementById('exp').href='/export?platform='+encodeURIComponent(plat);
});

function renderLogs(){
  const filtered=flt==='all'?lastItems:lastItems.filter(x=>x.status===flt);
  logs.innerHTML=filtered.slice().reverse().map(x=>`<div class="${x.status==='available'?'ok':(x.status==='taken'?'taken':'warn')}">@${x.u} -> ${x.txt}</div>`).join('');
}

document.querySelectorAll('.ftab').forEach(b=>b.onclick=()=>{
  flt=b.dataset.flt;
  document.querySelectorAll('.ftab').forEach(x=>x.classList.toggle('active',x===b));
  renderLogs();
});

async function cp(t,m){
  try{await navigator.clipboard.writeText(t);msg.textContent=m;}
  catch{msg.textContent='استخدم التصدير للنسخ.';}
}

function renderAvail(){
  grid.innerHTML=avail.map(u=>`<span class="chip" data-u="@${u}">@${u}</span>`).join('');
  grid.querySelectorAll('.chip').forEach(c=>c.onclick=()=>cp(c.dataset.u,'تم نسخ '+c.dataset.u));
}

copyAll.onclick=()=>avail.length?cp(avail.map(u=>'@'+u).join('\n'),`تم نسخ ${avail.length} يوزر.`):msg.textContent='لا توجد يوزرات متاحة.';
copyRaw.onclick=()=>avail.length?cp(avail.join('\n'),`تم نسخ ${avail.length} يوزر بدون @.`):msg.textContent='لا توجد يوزرات متاحة.';
clearBtn.onclick=()=>{lastItems=[];logs.innerHTML='';grid.innerHTML='';msg.textContent='';errBox.textContent='';bar.style.width='0%';info.textContent='جاهز.';lastAvailCount=0;};

async function poll(){
  try{
    const d=await(await fetch('/status')).json();
    avail=d.available_list||[];
    lastItems=d.items||[];
    if(avail.length>lastAvailCount){lastAvailCount=avail.length;beep();}
    renderAvail();
    renderLogs();
    const pct=d.total?Math.min(100,Math.round((d.done/d.total)*100)):0;
    bar.style.width=pct+'%';
    info.textContent=`${d.platform} | ${d.done}/${d.total} (${pct}%) | ${d.elapsed}ث (${d.rate}/ث) | متبقي ~${d.eta}ث | متاح مؤكد: ${d.available} | مأخوذ: ${d.taken} | مقيد: ${d.blocked} | محاولات: ${d.retries_used||0}`;
    errBox.textContent=d.last_error||'';
    if(!d.running){
      startBtn.disabled=false;stopBtn.disabled=true;retryBtn.disabled=(d.blocked<=0);
      if(timer){clearInterval(timer);timer=null;}
    }else{
      retryBtn.disabled=true;
    }
  }catch(e){
    errBox.textContent='خطأ في قراءة الحالة: '+e.message;
  }
}

stopBtn.onclick=async()=>{stopBtn.disabled=true;await fetch('/stop',{method:'POST'});poll();};

retryBtn.onclick=async()=>{
  startBtn.disabled=true;stopBtn.disabled=false;retryBtn.disabled=true;msg.textContent='';errBox.textContent='';
  try{
    const wrkV=document.getElementById('workers').value||'12';
    const jitV=document.getElementById('jitter_ms').value||'25';
    const body=new URLSearchParams({platform:plat,workers:wrkV,jitter_ms:jitV});
    const data=await(await fetch('/retry-blocked',{method:'POST',body})).json();
    if(!data.ok){errBox.textContent=data.error||'لا توجد يوزرات مقيدة لإعادتها.';startBtn.disabled=false;stopBtn.disabled=true;return;}
    if(timer)clearInterval(timer);
    timer=setInterval(poll,200);poll();
  }catch(err){
    errBox.textContent='فشل إعادة الفحص: '+err.message;startBtn.disabled=false;stopBtn.disabled=true;
  }
};

f.onsubmit=async e=>{
  e.preventDefault();
  startBtn.disabled=true;stopBtn.disabled=false;retryBtn.disabled=true;msg.textContent='';errBox.textContent='';grid.innerHTML='';logs.innerHTML='';lastItems=[];lastAvailCount=0;info.textContent='جاري البدء...';
  try{
    const lenV=document.getElementById('length').value||'4',
          cntV=document.getElementById('count').value||'500',
          wrkV=document.getElementById('workers').value||'12',
          jitV=document.getElementById('jitter_ms').value||'25',
          preV=document.getElementById('prefix').value||'',
          sufV=document.getElementById('suffix').value||'',
          modV=document.getElementById('mode').value||'alnum',
          lstV=document.getElementById('custom_list').value||'';
    const body=new URLSearchParams({
      platform:plat,length:lenV,count:cntV,prefix:preV,suffix:sufV,
      mode:modV,workers:wrkV,jitter_ms:jitV,custom_list:lstV,
      auto_retry:autoRetry.checked?'1':'0'
    });
    const data=await(await fetch('/start',{method:'POST',body})).json();
    if(!data.ok){errBox.textContent=data.error||'تعذر بدء الفحص.';startBtn.disabled=false;stopBtn.disabled=true;return;}
    if(timer)clearInterval(timer);
    timer=setInterval(poll,200);poll();
  }catch(err){
    errBox.textContent='فشل إرسال طلب البدء: '+err.message;startBtn.disabled=false;stopBtn.disabled=true;
  }
};
</script>
</body>
</html>"""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

ALLOWED = set(string.ascii_lowercase + string.digits + "_.")
CONS, VOWS = "bcdfghjklmnprstvwyz", "aeiou"
SHARP_STARTS = ["k", "r", "v", "z", "x", "q", "n", "m", "d", "t", "s", "l"]
_tls = threading.local()


def get_session(workers: int) -> requests.Session:
    s = getattr(_tls, "session", None)
    if s is None:
        s = requests.Session()
        pool = max(12, min(40, workers * 2))
        adapter = HTTPAdapter(pool_connections=pool, pool_maxsize=pool, max_retries=0)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Connection": "keep-alive",
        })
        _tls.session = s
    elif random.random() < 0.08:
        s.headers["User-Agent"] = random.choice(USER_AGENTS)
    return s


def clean_affix(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c in ALLOWED).strip(".")


def parse_custom_list(raw: str, prefix: str, suffix: str, limit: int) -> list[str]:
    tokens = re.split(r"[\s,;]+", (raw or "").strip().lower())
    seen, out = set(), []
    for tok in tokens:
        if len(out) >= limit:
            break
        cleaned = clean_affix(tok.lstrip("@"))
        if not cleaned:
            continue
        candidate = clean_affix(f"{prefix}{cleaned}{suffix}").replace("..", ".")
        if len(candidate) >= 2 and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    return out


def make_syllable_core(core_len: int) -> str:
    parts = []
    while len("".join(parts)) < core_len:
        parts.append(random.choice(CONS) + random.choice(VOWS))
    raw = "".join(parts)[:core_len]
    if core_len >= 2 and random.random() < 0.35:
        raw = raw[:-1] + random.choice(string.digits)
    return raw


def make_sharp_core(core_len: int) -> str:
    base = random.choice(SHARP_STARTS) + random.choice(VOWS) + random.choice(CONS)
    while len(base) < core_len:
        base += random.choice(string.ascii_lowercase + string.digits)
    return base[:core_len]


def make_stylish_core(core_len: int) -> str:
    if core_len == 1:
        return random.choice(string.ascii_lowercase + string.digits)
    ch = random.choice(string.ascii_lowercase)
    if core_len == 2:
        return ch + random.choice([ch, random.choice(string.digits), "x", "z"])
    mid = "".join(random.choices(string.ascii_lowercase + string.digits, k=max(1, core_len - 2)))
    tail = random.choice([ch, random.choice(string.digits), "x"])
    return (ch + mid + tail)[:core_len]


def gen_users(count: int, length: int, mode: str, prefix: str, suffix: str, custom_raw: str = "") -> list[str]:
    if mode == "custom_list":
        return parse_custom_list(custom_raw, prefix, suffix, count)

    pool = (
        string.ascii_lowercase
        if mode == "alpha"
            else (
            string.digits
            if mode == "digits"
            else (
                string.ascii_lowercase + string.digits + "_"
                if mode == "underscore"
                else (
                    string.ascii_lowercase + string.digits + "."
                    if mode == "dots"
                    else string.ascii_lowercase + string.digits
                )
            )
        )
    )
    fb = string.digits if mode == "digits" else (string.ascii_lowercase + string.digits)
    core_len = max(1, length - len(prefix) - len(suffix))
    seen, out = set(), []
    for _ in range(min(count * 8 + 500, 450000)):
        if len(out) >= count:
            break
        if mode == "syllable":
            core = make_syllable_core(core_len)
        elif mode == "short_sharp":
            core = make_sharp_core(core_len)
        elif mode == "stylish_tags":
            core = make_stylish_core(core_len)
        else:
            core = "".join(random.choices(pool, k=core_len)).strip("_.") or "".join(random.choices(fb, k=core_len))
        u = clean_affix(f"{prefix}{core}{suffix}").replace("..", ".")
        if len(u) >= 2 and u not in seen:
            seen.add(u)
            out.append(u)
    while len(out) < count:
        u = clean_affix(f"{prefix}{''.join(random.choices(fb, k=max(2, core_len)))}{suffix}")
        if u not in seen:
            seen.add(u)
            out.append(u)
        else:
            out.append(f"{u[:12]}{random.randint(10, 9999)}")
    return out[:count]


def _probe_once(s: requests.Session, platform: str, u: str) -> tuple[str, str]:
    if platform == "youtube":
        r = s.get(f"https://www.youtube.com/@{u}", timeout=7, allow_redirects=True)
        if r.status_code == 404:
            return "available", "غير موجود (404)"
        if r.status_code == 429:
            return "blocked", "تقييد مؤقت (429)"
        if r.status_code >= 500 or r.status_code == 403:
            return "blocked", f"حجب/خطأ ({r.status_code})"
        html = r.text
        not_found_markers = [
            "This page isn't available",
            "404 Not Found",
            "HTTP ERROR 404",
            'itemSectionRenderer":{"contents":[{"messageRenderer"',
        ]
        channel_markers = [
            '"channelId":"',
            '"externalId":"',
            f'/@{u.lower()}"',
        ]
        if any(m in html for m in not_found_markers) and not any(m in html for m in channel_markers):
            return "available", "غير موجود في يوتيوب"
        if any(m in html for m in channel_markers):
            return "taken", "قناة موجودة"
        return "blocked", "تعذر جزم حالة القناة"

    if platform == "discord":
        r = s.post(
            "https://discord.com/api/v9/unique-username/username-attempt-unauthenticated",
            json={"username": u},
            headers={"Content-Type": "application/json", "User-Agent": random.choice(USER_AGENTS)},
            timeout=7,
        )
        if r.status_code == 429:
            return "blocked", "تقييد مؤقت (429)"
        if r.status_code == 200:
            try:
                d = r.json()
            except ValueError:
                return "blocked", "رد غير صالح من ديسكورد"
            if d.get("taken") is False:
                return "available", "غير مستخدم في API"
            if d.get("taken") is True:
                return "taken", "مستخدم مسبقاً"
        return "blocked", f"حالة غير مؤكدة ({r.status_code})"

    # tiktok
    r = s.get(f"https://www.tiktok.com/@{u}", timeout=7, allow_redirects=True)
    if r.status_code == 404:
        return "available", "غير موجود (404)"
    if r.status_code == 429:
        return "blocked", "تقييد مؤقت (429)"
    if r.status_code in (403, 405, 503) or r.status_code >= 500:
        return "blocked", f"حجب/خطأ ({r.status_code})"

    html = r.text
    challenge_markers = [
        "captcha",
        "verify center",
        "sec_user_id",
        "Please wait...",
        "Access Denied",
    ]
    user_markers = [
        '"webapp.user-detail"',
        '"secUid":"',
    ]

    if re.search(r'"uniqueId"\s*:\s*"' + re.escape(u) + r'"', html, flags=re.IGNORECASE) or any(
        m in html for m in user_markers
    ):
        return "taken", "حساب نشط/موجود"

    if r.status_code == 200 and not any(m in html for m in challenge_markers):
        if "Couldn't find this account" in html or "Page not found" in html or len(html) < 4000:
            return "available", "غير موجود في تيك توك"
        return "blocked", "استجابة غير حاسمة"

    return "blocked", "تحقق أمني أو حجب"


def check_platform(platform: str, u: str, workers: int) -> tuple[str, str, int]:
    s = get_session(workers)
    retries = 0
    for attempt in range(2):
        try:
            st1, reason1 = _probe_once(s, platform, u)
            if st1 == "blocked":
                if attempt == 0:
                    retries += 1
                    time.sleep(random.uniform(0.35, 0.75))
                    continue
                return "blocked", reason1, retries

            time.sleep(random.uniform(0.05, 0.14))
            st2, reason2 = _probe_once(s, platform, u)

            if st1 == "available" and st2 == "available":
                return "available", f"مؤكد متاح ({reason2})", retries
            if st1 == "taken" and st2 == "taken":
                return "taken", f"مؤكد مأخوذ ({reason2})", retries
            if st1 != st2:
                return "blocked", f"تعارض الفحصين ({st1}/{st2})", retries
            return "blocked", reason2, retries
        except Exception as e:
            if attempt == 0:
                retries += 1
                time.sleep(0.2)
                continue
            return "blocked", e.__class__.__name__, retries
    return "blocked", "تعذر التحقق", retries


def update_metrics(t0: float) -> None:
    elapsed = max(0.1, time.perf_counter() - t0)
    rate = state["done"] / elapsed
    rem = max(0, state["total"] - state["done"])
    state["elapsed"] = round(elapsed, 1)
    state["rate"] = round(rate, 1)
    state["eta"] = round(rem / rate, 1) if rate > 0 else 0.0


def check_u(platform: str, u: str, t0: float, workers: int, jitter_sec: float) -> None:
    with lock:
        if state["stop"]:
            return
    if jitter_sec > 0:
        time.sleep(random.uniform(jitter_sec * 0.5, jitter_sec * 1.4))
    with lock:
        if state["stop"]:
            return
    st, txt, retries = check_platform(platform, u, workers)
    with lock:
        if state["stop"]:
            return
        state["done"] += 1
        state["retries_used"] += retries
        if st == "available":
            state["available"] += 1
            if len(state["available_list"]) < MAX_USERNAMES:
                state["available_list"].append(u)
        elif st == "taken":
            state["taken"] += 1
        else:
            state["blocked"] += 1
            if len(state["blocked_list"]) < MAX_USERNAMES:
                state["blocked_list"].append(u)
        update_metrics(t0)
        state["items"].append({"u": u, "status": st, "txt": txt})
        if len(state["items"]) > MAX_UI_ITEMS:
            state["items"] = state["items"][-MAX_UI_ITEMS:]


def run_pool(platform: str, users: list[str], workers: int, reset: bool, jitter_sec: float = 0.025) -> list[str]:
    t0 = time.perf_counter()
    try:
        with lock:
            base = {
                "running": True,
                "stop": False,
                "platform": platform,
                "done": 0,
                "total": len(users),
                "elapsed": 0.0,
                "rate": 0.0,
                "eta": 0.0,
                "blocked": 0,
                "blocked_list": [],
                "last_error": "",
            }
            if reset:
                base.update({"available": 0, "taken": 0, "retries_used": 0, "available_list": [], "items": []})
            state.update(base)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(check_u, platform, u, t0, workers, jitter_sec) for u in users]
            for fut in as_completed(futs):
                with lock:
                    if state["stop"]:
                        ex.shutdown(wait=False, cancel_futures=True)
                        break
                try:
                    fut.result()
                except Exception as exc:
                    with lock:
                        state["last_error"] = f"خطأ أثناء الفحص: {exc}"
    except Exception as e:
        with lock:
            state["last_error"] = f"خطأ في المهمة: {e}"
    finally:
        with lock:
            remaining_blocked = list(state["blocked_list"])
            state["running"] = False
            state["stop"] = False
            state["eta"] = 0.0
            update_metrics(t0)
    return remaining_blocked


def worker_job(
    platform: str,
    length: int,
    count: int,
    mode: str,
    prefix: str,
    suffix: str,
    workers: int,
    jitter_sec: float,
    auto_retry: bool,
    custom_raw: str,
) -> None:
    users = gen_users(count, length, mode, prefix, suffix, custom_raw=custom_raw)
    if not users:
        with lock:
            state["last_error"] = "لم يتم العثور على يوزرات صالحة للفحص."
        return
    blocked_after = run_pool(platform, users, workers, reset=True, jitter_sec=jitter_sec)
    with lock:
        stopped = state["stop"]
    if auto_retry and not stopped and blocked_after:
        run_pool(platform, blocked_after, max(1, min(workers, 10)), reset=False, jitter_sec=max(jitter_sec, 0.06))


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/start", methods=["POST"])
def start_scan():
    with lock:
        if state["running"]:
            return jsonify({"ok": False, "error": "يوجد فحص قيد التشغيل حالياً."})

    platform = (request.form.get("platform") or "tiktok").strip().lower()
    if platform not in {"tiktok", "youtube", "discord"}:
        platform = "tiktok"

    try:
        length = max(2, min(16, int(request.form.get("length", 4))))
        count = max(1, min(MAX_USERNAMES, int(request.form.get("count", 500))))
        workers = max(1, min(MAX_WORKERS, int(request.form.get("workers", 12))))
        jitter_ms = max(0, min(500, int(request.form.get("jitter_ms", 25))))
    except ValueError:
        return jsonify({"ok": False, "error": "قيم غير صالحة."})

    mode = (request.form.get("mode") or "alnum").strip()
    if mode not in {"alnum", "alpha", "underscore", "dots", "syllable", "short_sharp", "stylish_tags", "digits", "custom_list"}:
        mode = "alnum"

    prefix = clean_affix(request.form.get("prefix") or "")[:8]
    suffix = clean_affix(request.form.get("suffix") or "")[:8]
    custom_raw = request.form.get("custom_list") or ""
    auto_retry = (request.form.get("auto_retry") or "0") == "1"

    threading.Thread(
        target=worker_job,
        args=(platform, length, count, mode, prefix, suffix, workers, jitter_ms / 1000.0, auto_retry, custom_raw),
        daemon=True,
    ).start()
    return jsonify({"ok": True})


@app.route("/retry-blocked", methods=["POST"])
def retry_blocked():
    with lock:
        if state["running"]:
            return jsonify({"ok": False, "error": "يوجد فحص قيد التشغيل حالياً."})
        blocked_users = list(state["blocked_list"])
        platform = (request.form.get("platform") or state["platform"] or "tiktok").strip().lower()

    if not blocked_users:
        return jsonify({"ok": False, "error": "لا توجد يوزرات مقيدة لإعادتها."})

    try:
        workers = max(1, min(MAX_WORKERS, int(request.form.get("workers", 12))))
        jitter_ms = max(0, min(500, int(request.form.get("jitter_ms", 40))))
    except ValueError:
        workers, jitter_ms = 12, 40

    threading.Thread(
        target=run_pool,
        args=(platform, blocked_users, max(1, min(workers, 12)), False, jitter_ms / 1000.0),
        daemon=True,
    ).start()
    return jsonify({"ok": True})


@app.route("/stop", methods=["POST"])
def stop_scan():
    with lock:
        state["stop"] = True
    return jsonify({"ok": True})


@app.route("/status")
def get_status():
    with lock:
        return jsonify({
            "running": state["running"],
            "platform": state["platform"],
            "done": state["done"],
            "total": state["total"],
            "elapsed": state["elapsed"],
            "rate": state["rate"],
            "eta": state["eta"],
            "available": state["available"],
            "taken": state["taken"],
            "blocked": state["blocked"],
            "retries_used": state["retries_used"],
            "last_error": state["last_error"],
            "available_list": state["available_list"][-300:],
            "items": state["items"][-120:],
        })


@app.route("/export")
def export_txt():
    platform = (request.args.get("platform") or "all").strip().lower()
    with lock:
        lines = [f"@{u}" for u in state["available_list"]]
    body = "\n".join(lines) + ("\n" if lines else "")
    return Response(
        body,
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=available_{platform}.txt"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
    
