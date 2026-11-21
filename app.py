from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
import string
import threading
import time
from flask import Flask, Response, jsonify, render_template_string, request
import requests

app = Flask(__name__)
MAX_USERNAMES = 5000
MAX_UI_ITEMS = 400

lock = threading.Lock()
state = {
    "running": False,
    "stop": False,
    "platform": "tiktok",
    "done": 0,
    "total": 0,
    "elapsed": 0.0,
    "available": 0,
    "taken": 0,
    "blocked": 0,
    "available_list": [],
    "items": [],
}

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>صائد يوزرات</title>
<style>
*{box-sizing:border-box}
body{background:#000;color:#f3f4f6;font-family:Tahoma,sans-serif;margin:0;padding:12px}
.wrap{max-width:620px;margin:8px auto;background:#070709;border:1px solid #2a0a0e;border-radius:14px;padding:16px}
h2{margin:0 0 12px;text-align:center;color:#ef4444;font-size:19px}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.tab{padding:9px;border-radius:9px;border:1px solid #26262b;background:#0e0e12;color:#d1d5db;font-weight:bold;cursor:pointer}
.tab.active{background:#dc2626;border-color:#ef4444;color:#fff}
.pbox{display:none;background:#0c0c10;border:1px solid #1f1f26;border-radius:10px;padding:10px;margin-bottom:10px;font-size:12px;color:#9ca3af}
.pbox.active{display:block}
.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
label{display:block;margin-top:8px;font-size:12px;color:#e5e7eb}
input,select{width:100%;margin-top:4px;padding:8px 10px;border-radius:8px;border:1px solid #26262b;background:#050507;color:#fff;font-size:13px}
.btns{display:grid;grid-template-columns:2fr 1fr;gap:8px;margin-top:12px}
button{padding:9px 12px;border-radius:9px;border:none;font-weight:bold;cursor:pointer}
.main{background:#dc2626;color:#fff}
.sec{background:#18181b;color:#f3f4f6}
button:disabled{opacity:.45}
.bar-bg{margin-top:10px;height:8px;background:#141418;border-radius:999px;overflow:hidden}
.bar{height:100%;width:0%;background:#ef4444}
.stats{margin-top:8px;font-size:12px;color:#d1d5db}
.sec-box{margin-top:12px;background:#0c0c10;border:1px solid #1f1f26;border-radius:10px;padding:10px}
.grid{display:flex;flex-wrap:wrap;gap:6px;max-height:140px;overflow-y:auto;margin-top:8px}
.chip{background:rgba(34,197,94,.14);border:1px solid rgba(74,222,128,.4);color:#4ade80;padding:4px 8px;border-radius:7px;font-size:12px;cursor:pointer}
.logs{max-height:200px;overflow-y:auto;font-size:12px;margin-top:6px}
.ok{color:#4ade80}.taken{color:#f87171}.warn{color:#facc15}
.msg{color:#4ade80;font-size:12px;min-height:16px;margin-top:6px}
@media(max-width:500px){.row{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <h2>صائد يوزرات تيك • يوتيوب • ديسكورد</h2>
  <div class="tabs">
    <button type="button" class="tab active" data-p="tiktok">تيك توك</button>
    <button type="button" class="tab" data-p="youtube">يوتيوب</button>
    <button type="button" class="tab" data-p="discord">ديسكورد</button>
  </div>
  <div class="pbox active" id="p-tiktok">فحص يوزرات تيك توك فقط. تأكد من اليوزر داخل التطبيق قبل اعتماده.</div>
  <div class="pbox" id="p-youtube">فحص معرفات يوتيوب (@Handle) فقط بنفس الإعدادات.</div>
  <div class="pbox" id="p-discord">
    فحص توفر أسماء ديسكورد فقط دون تغيير تلقائي للحساب. اضغط على اليوزر المتاح لنسخه وتغييره يدوياً.
    <div class="row">
      <div><label>يوزر حسابك (اختياري)</label><input type="text" id="dc_user" placeholder="مثال: my_user"></div>
      <div><label>ملاحظة</label><input type="text" value="نسخ وتغيير يدوي في ديسكورد" readonly></div>
    </div>
  </div>
  <form id="f">
    <div class="row">
      <div><label>الطول (2 - 16)</label><input type="number" id="length" min="2" max="16" value="5" required></div>
      <div><label>العدد (1 - 5000)</label><input type="number" id="count" min="1" max="5000" value="500" required></div>
    </div>
    <div class="row">
      <div><label>بداية اليوزر</label><input type="text" id="prefix" maxlength="8" placeholder="اختياري"></div>
      <div><label>نهاية اليوزر</label><input type="text" id="suffix" maxlength="8" placeholder="اختياري"></div>
    </div>
    <div class="row">
      <div>
        <label>النوع</label>
        <select id="mode">
          <option value="alnum">حروف وأرقام</option>
          <option value="alpha">حروف فقط</option>
          <option value="underscore">حروف وأرقام و _</option>
        </select>
      </div>
      <div><label>السرعة / العمال (1 - 20)</label><input type="number" id="workers" min="1" max="20" value="8" required></div>
    </div>
    <div class="btns">
      <button type="submit" class="main" id="startBtn">بدء الفحص</button>
      <button type="button" class="sec" id="stopBtn" disabled>إيقاف</button>
    </div>
  </form>
  <div class="bar-bg"><div class="bar" id="bar"></div></div>
  <div class="stats" id="info">جاهز.</div>
  <div class="sec-box">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap">
      <span style="color:#f87171;font-size:13px;font-weight:bold">اليوزرات المتاحة (اضغط للنسخ)</span>
      <div>
        <button type="button" class="sec" id="copyAll">نسخ الكل</button>
        <a id="exp" href="/export?platform=tiktok"><button type="button" class="sec">تصدير</button></a>
      </div>
    </div>
    <div class="msg" id="msg"></div>
    <div class="grid" id="grid"></div>
  </div>
  <div class="sec-box">
    <div style="color:#f87171;font-size:13px;font-weight:bold">سجل الفحص</div>
    <div class="logs" id="logs"></div>
  </div>
</div>
<script>
let plat="tiktok",avail=[],timer=null;
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{
  plat=b.dataset.p;
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===b));
  document.querySelectorAll(".pbox").forEach(x=>x.classList.remove("active"));
  document.getElementById("p-"+plat).classList.add("active");
  document.getElementById("exp").href="/export?platform="+encodeURIComponent(plat);
});
async function cp(t,m){try{await navigator.clipboard.writeText(t);msg.textContent=m;}catch{msg.textContent="استخدم التصدير للنسخ.";}}
function renderAvail(){
  grid.innerHTML=avail.map(u=>`<span class="chip" data-u="@${u}">@${u}</span>`).join("");
  grid.querySelectorAll(".chip").forEach(c=>c.onclick=()=>cp(c.dataset.u,"تم نسخ "+c.dataset.u));
}
copyAll.onclick=()=>avail.length?cp(avail.map(u=>"@"+u).join("\\n"),`تم نسخ ${avail.length} يوزر.`):msg.textContent="لا توجد يوزرات متاحة.";
async function poll(){
  const d=await(await fetch("/status")).json();
  avail=d.available_list||[];renderAvail();
  const pct=d.total?Math.round((d.done/d.total)*100):0;
  bar.style.width=pct+"%";
  info.textContent=`${d.platform} | ${d.done}/${d.total} (${pct}%) | ${d.elapsed}ث | متاح: ${d.available} | مأخوذ: ${d.taken} | مقيد: ${d.blocked}`;
  logs.innerHTML=(d.items||[]).map(x=>`<div class="${x.status==="available"?"ok":(x.status==="taken"?"taken":"warn")}">@${x.u} -> ${x.txt}</div>`).join("");
  if(!d.running){startBtn.disabled=false;stopBtn.disabled=true;if(timer){clearInterval(timer);timer=null;}}
}
stopBtn.onclick=async()=>{stopBtn.disabled=true;await fetch("/stop",{method:"POST"});poll();};
f.onsubmit=async e=>{
  e.preventDefault();startBtn.disabled=true;stopBtn.disabled=false;msg.textContent="";grid.innerHTML="";logs.innerHTML="";
  const body=new URLSearchParams({platform:plat,length:length.value,count:count.value,prefix:prefix.value,suffix:suffix.value,mode:mode.value,workers:workers.value});
  await fetch("/start",{method:"POST",body});
  if(timer)clearInterval(timer);timer=setInterval(poll,350);poll();
};
</script>
</body>
</html>"""

HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"}
ALLOWED = set(string.ascii_lowercase + string.digits + "_.")

def clean_affix(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c in ALLOWED).strip(".")

def gen_users(count: int, length: int, mode: str, prefix: str, suffix: str) -> list[str]:
    pool = string.ascii_lowercase if mode == "alpha" else (string.ascii_lowercase + string.digits + "_" if mode == "underscore" else string.ascii_lowercase + string.digits)
    fb = string.ascii_lowercase + string.digits
    core_len = max(1, length - len(prefix) - len(suffix))
    seen, out = set(), []
    for _ in range(count * 6 + 200):
        if len(out) >= count:
            break
        core = "".join(random.choices(pool, k=core_len)).strip("_") or "".join(random.choices(fb, k=core_len))
        u = clean_affix(f"{prefix}{core}{suffix}")
        if len(u) >= 2 and u not in seen:
            seen.add(u)
            out.append(u)
    while len(out) < count:
        u = clean_affix(f"{prefix}{''.join(random.choices(fb, k=max(2, core_len)))}{suffix}")
        if u not in seen:
            seen.add(u)
            out.append(u)
        else:
            out.append(f"{u[:12]}{random.randint(10, 99)}")
    return out[:count]

def check_platform(platform: str, u: str, s: requests.Session) -> tuple[str, str]:
    try:
        if platform == "youtube":
            r = s.get(f"https://www.youtube.com/@{u}", headers=HEADERS, timeout=4)
            if r.status_code == 404:
                return "available", "متاح ظاهرياً (404)"
            if r.status_code == 200 and ("This page isn't available" in r.text or "404 Not Found" in r.text):
                return "available", "متاح ظاهرياً"
            return ("taken", "مأخوذ (200)") if r.status_code == 200 else ("blocked", f"HTTP {r.status_code}")
        if platform == "discord":
            r = s.post("https://discord.com/api/v9/unique-username/username-attempt-unauthenticated", json={"username": u}, headers={**HEADERS, "Content-Type": "application/json"}, timeout=4)
            if r.status_code == 200:
                d = r.json() if r.content else {}
                if d.get("taken") is False:
                    return "available", "متاح ظاهرياً (200)"
                if d.get("taken") is True:
                    return "taken", "مأخوذ (200)"
            return ("blocked", f"HTTP {r.status_code}")
        r = s.get(f"https://www.tiktok.com/@{u}", headers=HEADERS, timeout=4)
        if r.status_code == 404:
            return "available", "متاح ظاهرياً (404)"
        return ("taken", "مأخوذ (200)") if r.status_code == 200 else ("blocked", f"HTTP {r.status_code}")
    except requests.RequestException as e:
        return "blocked", e.__class__.__name__

def check_u(platform: str, u: str, s: requests.Session, t0: float, workers: int) -> None:
    with lock:
        if state["stop"]:
            return
    time.sleep(random.uniform(0.02, 0.12) if workers >= 12 else random.uniform(0.05, 0.15))
    with lock:
        if state["stop"]:
            return
    st, txt = check_platform(platform, u, s)
    with lock:
        if state["stop"]:
            return
        state["done"] += 1
        state["elapsed"] = round(time.perf_counter() - t0, 1)
        if st == "available":
            state["available"] += 1
            if len(state["available_list"]) < MAX_USERNAMES:
                state["available_list"].append(u)
        elif st == "taken":
            state["taken"] += 1
        else:
            state["blocked"] += 1
        state["items"].append({"u": u, "status": st, "txt": txt})
        if len(state["items"]) > MAX_UI_ITEMS:
            state["items"] = state["items"][-MAX_UI_ITEMS:]

def worker_job(platform: str, length: int, count: int, mode: str, prefix: str, suffix: str, workers: int) -> None:
    t0 = time.perf_counter()
    users = gen_users(count, length, mode, prefix, suffix)
    with lock:
        state.update({"running": True, "stop": False, "platform": platform, "done": 0, "total": len(users), "elapsed": 0.0, "available": 0, "taken": 0, "blocked": 0, "available_list": [], "items": []})
    with requests.Session() as s:
        ad = requests.adapters.HTTPAdapter(pool_connections=workers, pool_maxsize=workers)
        s.mount("https://", ad)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(check_u, platform, u, s, t0, workers) for u in users]
            for fut in as_completed(futs):
                with lock:
                    if state["stop"]:
                        ex.shutdown(wait=False, cancel_futures=True)
                        break
                fut.result()
    with lock:
        state["running"] = False
        state["stop"] = False
        state["elapsed"] = round(time.perf_counter() - t0, 1)

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/start", methods=["POST"])
def start():
    with lock:
        if state["running"]:
            return jsonify({"ok": False})
    platform = request.form.get("platform", "tiktok")
    if platform not in {"tiktok", "youtube", "discord"}:
        platform = "tiktok"
    length = max(2, min(16, int(request.form.get("length", 5))))
    count = max(1, min(MAX_USERNAMES, int(request.form.get("count", 500))))
    mode = request.form.get("mode", "alnum")
    prefix = clean_affix(request.form.get("prefix", ""))
    suffix = clean_affix(request.form.get("suffix", ""))
    workers = max(1, min(20, int(request.form.get("workers", 8))))
    threading.Thread(target=worker_job, args=(platform, length, count, mode, prefix, suffix, workers), daemon=True).start()
    return jsonify({"ok": True})

@app.route("/stop", methods=["POST"])
def stop():
    with lock:
        state["stop"] = True
    return jsonify({"ok": True})

@app.route("/status")
def status():
    with lock:
        return jsonify(dict(state))

@app.route("/export")
def export():
    platform = request.args.get("platform", "tiktok")
    with lock:
        free = [f"@{u}" for u in state["available_list"]]
    return Response("\n".join(free) + ("\n" if free else ""), mimetype="text/plain; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=available_{platform}.txt"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
    
