from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
import string
import threading
import time
from flask import Flask, Response, jsonify, render_template_string, request
import requests

app = Flask(__name__)
MAX_USERNAMES = 50000
MAX_UI_ITEMS = 1000

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
    "last_error": "",
    "available_list": [],
    "blocked_list": [],
    "items": [],
}

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>صائد يوزرات الأقصى</title>
<style>
*{box-sizing:border-box}
body{background:#000;color:#f3f4f6;font-family:Tahoma,sans-serif;margin:0;padding:12px}
.wrap{max-width:760px;margin:8px auto;background:#070709;border:1px solid #330c11;border-radius:16px;padding:16px;box-shadow:0 0 36px rgba(220,38,38,.18)}
h2{margin:0 0 12px;text-align:center;color:#ef4444;font-size:21px}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.tab{padding:9px;border-radius:10px;border:1px solid #26262b;background:#0e0e12;color:#d1d5db;font-weight:bold;cursor:pointer}
.tab.active{background:#dc2626;border-color:#ef4444;color:#fff}
.pbox{display:none;background:#0c0c10;border:1px solid #1f1f26;border-radius:10px;padding:10px;margin-bottom:10px;font-size:12px;color:#9ca3af;line-height:1.6}
.pbox.active{display:block}
.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.row3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
label{display:block;margin-top:8px;font-size:12px;color:#e5e7eb}
input,select{width:100%;margin-top:4px;padding:8px 10px;border-radius:8px;border:1px solid #26262b;background:#050507;color:#fff;font-size:13px}
.chk{display:flex;align-items:center;gap:6px;margin-top:10px;font-size:12px;color:#d1d5db}
.chk input{width:auto;margin:0}
.btns{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:8px;margin-top:12px}
button{padding:9px 12px;border-radius:9px;border:none;font-weight:bold;cursor:pointer}
.main{background:#dc2626;color:#fff}
.sec{background:#18181b;color:#f3f4f6}
.link-btn{display:inline-block;margin-top:8px;padding:6px 10px;border-radius:8px;background:#18181b;color:#f87171;text-decoration:none;font-size:12px;border:1px solid #331317}
button:disabled{opacity:.45}
.bar-bg{margin-top:10px;height:10px;background:#141418;border-radius:999px;overflow:hidden}
.bar{height:100%;width:0%;background:linear-gradient(90deg,#7f1d1d,#dc2626,#ef4444);transition:width .18s}
.stats{margin-top:8px;font-size:12px;color:#d1d5db;line-height:1.7}
.err{margin-top:6px;font-size:12px;color:#f87171;min-height:16px}
.sec-box{margin-top:12px;background:#0c0c10;border:1px solid #1f1f26;border-radius:10px;padding:10px}
.grid{display:flex;flex-wrap:wrap;gap:6px;max-height:180px;overflow-y:auto;margin-top:8px}
.chip{background:rgba(34,197,94,.14);border:1px solid rgba(74,222,128,.4);color:#4ade80;padding:4px 8px;border-radius:7px;font-size:12px;cursor:pointer}
.logs{max-height:250px;overflow-y:auto;font-size:12px;margin-top:6px;line-height:1.6}
.ok{color:#4ade80}.taken{color:#f87171}.warn{color:#facc15}
.msg{color:#4ade80;font-size:12px;min-height:16px;margin-top:6px}
@media(max-width:600px){.row,.row3,.btns{grid-template-columns:1fr}}
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
  <div class="pbox active" id="p-tiktok">فحص فائق ليوزرات تيك توك فقط مع تحقق سريع. راجع اليوزر داخل التطبيق قبل اعتماده.</div>
  <div class="pbox" id="p-youtube">فحص فائق لمعرفات يوتيوب (@Handle) فقط بنفس الإعدادات والسرعة القصوى.</div>
  <div class="pbox" id="p-discord">
    فحص توفر أسماء ديسكورد فقط دون تغيير تلقائي للحساب. اضغط على اليوزر المتاح لنسخه وتغييره يدوياً من إعدادات ديسكورد.
    <div class="row">
      <div><label>يوزر حسابك (اختياري للتذكير)</label><input type="text" id="dc_user" placeholder="مثال: my_user"></div>
      <div><label>طريقة التغيير</label><input type="text" value="نسخ وتغيير يدوي آمن" readonly></div>
    </div>
    <a class="link-btn" href="https://discord.com/channels/@me" target="_blank" rel="noopener noreferrer">فتح ديسكورد لتغيير اليوزر يدوياً</a>
  </div>
  <form id="f">
    <div class="row3">
      <div><label>الطول (2 - 16)</label><input type="number" id="length" min="2" max="16" value="5" required></div>
      <div><label>العدد (1 - 50000)</label><input type="number" id="count" min="1" max="50000" value="2000" required></div>
      <div><label>السرعة / العمال (1 - 50)</label><input type="number" id="workers" min="1" max="50" value="20" required></div>
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
          <option value="dots">حروف وأرقام و .</option>
          <option value="syllable">مقاطع نطقية + أرقام</option>
          <option value="digits">أرقام فقط</option>
        </select>
      </div>
      <label class="chk"><input type="checkbox" id="sound" checked> تنبيه صوتي عند صيد يوزر متاح</label>
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
      <span style="color:#f87171;font-size:13px;font-weight:bold">اليوزرات المتاحة (اضغط للنسخ)</span>
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
    <div style="color:#f87171;font-size:13px;font-weight:bold">سجل الفحص المباشر</div>
    <div class="logs" id="logs"></div>
  </div>
</div>
<script>
let plat="tiktok",avail=[],lastAvailCount=0,timer=null;
function beep(){
  if(!sound.checked)return;
  try{
    const ctx=new(window.AudioContext||window.webkitAudioContext)();
    const o=ctx.createOscillator(),g=ctx.createGain();
    o.type="triangle";o.frequency.value=960;g.gain.value=0.09;
    o.connect(g);g.connect(ctx.destination);o.start();
    setTimeout(()=>{o.stop();ctx.close();},140);
  }catch{}
}
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
copyRaw.onclick=()=>avail.length?cp(avail.join("\\n"),`تم نسخ ${avail.length} يوزر بدون @.`):msg.textContent="لا توجد يوزرات متاحة.";
clearBtn.onclick=()=>{logs.innerHTML="";grid.innerHTML="";msg.textContent="";errBox.textContent="";bar.style.width="0%";info.textContent="جاهز.";lastAvailCount=0;};
async function poll(){
  try{
    const d=await(await fetch("/status")).json();
    avail=d.available_list||[];
    if(avail.length>lastAvailCount){lastAvailCount=avail.length;beep();}
    renderAvail();
    const pct=d.total?Math.round((d.done/d.total)*100):0;
    bar.style.width=pct+"%";
    info.textContent=`${d.platform} | ${d.done}/${d.total} (${pct}%) | ${d.elapsed}ث (${d.rate}/ث) | متبقي ~${d.eta}ث | متاح: ${d.available} | مأخوذ: ${d.taken} | مقيد: ${d.blocked}`;
    errBox.textContent=d.last_error||"";
    logs.innerHTML=(d.items||[]).slice().reverse().map(x=>`<div class="${x.status==="available"?"ok":(x.status==="taken"?"taken":"warn")}">@${x.u} -> ${x.txt}</div>`).join("");
    if(!d.running){
      startBtn.disabled=false;stopBtn.disabled=true;
      retryBtn.disabled=(d.blocked<=0);
      if(timer){clearInterval(timer);timer=null;}
    }else{
      retryBtn.disabled=true;
    }
  }catch(e){
    errBox.textContent="خطأ في قراءة الحالة: "+e.message;
  }
}
stopBtn.onclick=async()=>{stopBtn.disabled=true;await fetch("/stop",{method:"POST"});poll();};
retryBtn.onclick=async()=>{
  startBtn.disabled=true;stopBtn.disabled=false;retryBtn.disabled=true;msg.textContent="";errBox.textContent="";
  try{
    const body=new URLSearchParams({platform:plat,workers:workers.value});
    const res=await fetch("/retry-blocked",{method:"POST",body});
    const data=await res.json();
    if(!data.ok){errBox.textContent=data.error||"لا توجد يوزرات مقيدة لإعادتها.";startBtn.disabled=false;stopBtn.disabled=true;return;}
    if(timer)clearInterval(timer);
    timer=setInterval(poll,150);
    poll();
  }catch(err){
    errBox.textContent="فشل إعادة الفحص: "+err.message;startBtn.disabled=false;stopBtn.disabled=true;
  }
};
f.onsubmit=async e=>{
  e.preventDefault();startBtn.disabled=true;stopBtn.disabled=false;retryBtn.disabled=true;msg.textContent="";errBox.textContent="";grid.innerHTML="";logs.innerHTML="";lastAvailCount=0;info.textContent="جاري البدء...";
  try{
    const body=new URLSearchParams({platform:plat,length:length.value,count:count.value,prefix:prefix.value,suffix:suffix.value,mode:mode.value,workers:workers.value});
    const res=await fetch("/start",{method:"POST",body});
    const data=await res.json();
    if(!data.ok){errBox.textContent=data.error||"تعذر بدء الفحص.";startBtn.disabled=false;stopBtn.disabled=true;return;}
    if(timer)clearInterval(timer);
    timer=setInterval(poll,150);
    poll();
  }catch(err){
    errBox.textContent="فشل إرسال طلب البدء: "+err.message;startBtn.disabled=false;stopBtn.disabled=true;
  }
};
</script>
</body>
</html>"""
