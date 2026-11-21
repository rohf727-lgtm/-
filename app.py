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

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>صائد يوزرات تيك توك • يوتيوب • ديسكورد</title>
    <style>
        * { box-sizing: border-box; }
        body {
            background: #000000;
            color: #f3f4f6;
            font-family: Tahoma, Arial, sans-serif;
            margin: 0;
            padding: 14px;
        }
        .wrap {
            max-width: 640px;
            margin: 10px auto;
            background: #070709;
            border: 1px solid #2a0a0e;
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 0 35px rgba(220, 38, 38, 0.14);
        }
        .header {
            text-align: center;
            margin-bottom: 14px;
        }
        .header h2 {
            margin: 0;
            color: #ef4444;
            font-size: 20px;
        }
        .header p {
            margin: 6px 0 0;
            color: #9ca3af;
            font-size: 12px;
        }
        .tabs {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 14px;
        }
        .tab-btn {
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #26262b;
            background: #0e0e12;
            color: #d1d5db;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
        }
        .tab-btn.active {
            background: linear-gradient(135deg, #991b1b, #dc2626);
            border-color: #ef4444;
            color: #ffffff;
        }
        .platform-box {
            display: none;
            background: #0c0c10;
            border: 1px solid #1f1f26;
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 12px;
        }
        .platform-box.active {
            display: block;
        }
        .platform-title {
            color: #f87171;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 6px;
        }
        .platform-note {
            color: #9ca3af;
            font-size: 11px;
            line-height: 1.6;
        }
        .row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        label {
            display: block;
            margin-top: 8px;
            font-size: 12px;
            color: #e5e7eb;
        }
        input, select {
            width: 100%;
            margin-top: 4px;
            padding: 9px 11px;
            border-radius: 9px;
            border: 1px solid #26262b;
            background: #050507;
            color: #ffffff;
            font-size: 13px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #ef4444;
        }
        .btns {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 10px;
            margin-top: 14px;
        }
        .btn-main {
            padding: 10px 14px;
            border-radius: 10px;
            border: none;
            background: #dc2626;
            color: #fff;
            font-weight: bold;
            font-size: 14px;
            cursor: pointer;
        }
        .btn-main:hover { background: #b91c1c; }
        .btn-sec {
            padding: 10px 14px;
            border-radius: 10px;
            border: 1px solid #27272a;
            background: #141418;
            color: #f3f4f6;
            font-weight: bold;
            font-size: 12px;
            cursor: pointer;
        }
        button:disabled { opacity: 0.45; cursor: not-allowed; }
        .bar-bg {
            margin-top: 12px;
            height: 9px;
            background: #141418;
            border-radius: 999px;
            overflow: hidden;
        }
        .bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #991b1b, #ef4444);
            transition: width 0.2s;
        }
        .stats {
            margin-top: 10px;
            font-size: 12px;
            color: #d1d5db;
            line-height: 1.7;
        }
        .section {
            margin-top: 12px;
            background: #0c0c10;
            border: 1px solid #1f1f26;
            border-radius: 10px;
            padding: 12px;
        }
        .section-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 8px;
        }
        .section-title {
            font-size: 13px;
            font-weight: bold;
            color: #f87171;
        }
        .avail-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            max-height: 150px;
            overflow-y: auto;
        }
        .chip {
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(74, 222, 128, 0.35);
            color: #4ade80;
            padding: 5px 9px;
            border-radius: 8px;
            font-size: 12px;
            cursor: pointer;
            user-select: none;
        }
        .chip:hover {
            background: rgba(34, 197, 94, 0.24);
        }
        .log-box {
            max-height: 220px;
            overflow-y: auto;
            font-size: 12px;
            line-height: 1.7;
        }
        .ok { color: #4ade80; }
        .taken { color: #f87171; }
        .warn { color: #facc15; }
        .msg {
            margin-top: 6px;
            font-size: 12px;
            color: #4ade80;
            min-height: 16px;
        }
        @media (max-width: 520px) {
            .row { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="wrap">
        <div class="header">
            <h2>صائد يوزرات تيك توك • يوتيوب • ديسكورد</h2>
            <p>كل خانة تفحص منصتها فقط • سرعة حتى 20 • توليد حتى 5,000 يوزر</p>
        </div>

        <div class="tabs">
            <button type="button" class="tab-btn active" data-platform="tiktok">تيك توك</button>
            <button type="button" class="tab-btn" data-platform="youtube">يوتيوب</button>
            <button type="button" class="tab-btn" data-platform="discord">ديسكورد</button>
        </div>

        <div class="platform-box active" id="box-tiktok">
            <div class="platform-title">خانة تيك توك</div>
            <div class="platform-note">يفحص يوزرات تيك توك فقط. النتائج المتاحة ظاهرياً يُنصح بتأكيدها يدوياً داخل التطبيق لضمان التوفر الفعلي.</div>
        </div>

        <div class="platform-box" id="box-youtube">
            <div class="platform-title">خانة يوتيوب</div>
            <div class="platform-note">يفحص معرفات قنوات يوتيوب (@Handle) فقط بنفس إعدادات التوليد والسرعة.</div>
        </div>

        <div class="platform-box" id="box-discord">
            <div class="platform-title">خانة ديسكورد</div>
            <div class="platform-note">يفحص توفر أسماء مستخدمي ديسكورد فقط دون استخدام التوكن أو الباسورد لتغيير الحساب تلقائياً. عند إيجاد يوزر مناسب اضغط عليه لنسخه ثم غيّره يدوياً من إعدادات حسابك.</div>
            <div class="row">
                <div>
                    <label>يوزرك الحالي (اختياري للمرجع)</label>
                    <input type="text" id="dc_ref_user" placeholder="مثال: my_account">
                </div>
                <div>
                    <label>طريقة التغيير</label>
                    <input type="text" value="نسخ اليوزر وتغييره يدوياً في ديسكورد" readonly>
                </div>
            </div>
        </div>

        <form id="f">
            <div class="row">
                <div>
                    <label>طول اليوزر (2 - 16)</label>
                    <input type="number" id="length" min="2" max="16" value="5" required>
                </div>
                <div>
                    <label>عدد اليوزرات (1 - 5000)</label>
                    <input type="number" id="count" min="1" max="5000" value="500" required>
                </div>
            </div>
            <div class="row">
                <div>
                    <label>بداية اليوزر</label>
                    <input type="text" id="prefix" maxlength="8" placeholder="مثال: x_">
                </div>
                <div>
                    <label>نهاية اليوزر</label>
                    <input type="text" id="suffix" maxlength="8" placeholder="مثال: _1">
                </div>
            </div>
            <div class="row">
                <div>
                    <label>نوع اليوزر</label>
                    <select id="mode">
                        <option value="alnum">حروف وأرقام</option>
                        <option value="alpha">حروف فقط</option>
                        <option value="underscore">حروف وأرقام و _</option>
                    </select>
                </div>
                <div>
                    <label>السرعة / العمال (1 - 20)</label>
                    <input type="number" id="workers" min="1" max="20" value="8" required>
                </div>
            </div>
            <div class="btns">
                <button type="submit" class="btn-main" id="startBtn">بدء الفحص</button>
                <button type="button" class="btn-sec" id="stopBtn" disabled>إيقاف</button>
            </div>
        </form>

        <div class="bar-bg"><div class="bar" id="bar"></div></div>
        <div class="stats" id="info">جاهز للبدء.</div>

        <div class="section">
            <div class="section-head">
                <span class="section-title">اليوزرات المتاحة (اضغط على أي يوزر لنسخه)</span>
                <div>
                    <button type="button" class="btn-sec" id="copyAllBtn">نسخ الكل</button>
                    <a id="exportLink" href="/export?platform=tiktok"><button type="button" class="btn-sec">تصدير TXT</button></a>
                </div>
            </div>
            <div class="msg" id="msg"></div>
            <div class="avail-grid" id="availGrid"></div>
        </div>

        <div class="section">
            <div class="section-title" style="margin-bottom:6px;">سجل الفحص</div>
            <div class="log-box" id="list"></div>
        </div>
    </div>

    <script>
        let currentPlatform = "tiktok";
        const tabs = document.querySelectorAll(".tab-btn");
        const exportLink = document.getElementById("exportLink");

        tabs.forEach(btn => {
            btn.onclick = () => {
                currentPlatform = btn.dataset.platform;
                tabs.forEach(b => b.classList.toggle("active", b === btn));
                document.querySelectorAll(".platform-box").forEach(box => box.classList.remove("active"));
                document.getElementById("box-" + currentPlatform).classList.add("active");
                exportLink.href = "/export?platform=" + encodeURIComponent(currentPlatform);
            };
        });

        const f = document.getElementById("f");
        const startBtn = document.getElementById("startBtn");
        const stopBtn = document.getElementById("stopBtn");
        const copyAllBtn = document.getElementById("copyAllBtn");
        const bar = document.getElementById("bar");
        const info = document.getElementById("info");
        const msg = document.getElementById("msg");
        const availGrid = document.getElementById("availGrid");
        const list = document.getElementById("list");
        let availableUsers = [];
        let pollTimer = null;

        async function copyText(text, label) {
            try {
                await navigator.clipboard.writeText(text);
                msg.textContent = label;
            } catch {
                msg.textContent = "تعذر النسخ التلقائي، استخدم زر التصدير.";
            }
        }

        function renderAvailable() {
            availGrid.innerHTML = availableUsers.map(u => {
                const tag = "@" + u;
                return `<span class="chip" data-u="${tag}">${tag}</span>`;
            }).join("");
            availGrid.querySelectorAll(".chip").forEach(chip => {
                chip.onclick = () => copyText(chip.dataset.u, `تم نسخ ${chip.dataset.u}`);
            });
        }

        copyAllBtn.onclick = () => {
            if (!availableUsers.length) {
                msg.textContent = "لا توجد يوزرات متاحة للنسخ حالياً.";
                return;
            }
            copyText(availableUsers.map(u => "@" + u).join("\\n"), `تم نسخ ${availableUsers.length} يوزر.`);
        };

        async function poll() {
            const r = await fetch("/status");
            const d = await r.json();
            availableUsers = d.available_list || [];
            renderAvailable();

            const pct = d.total ? Math.round((d.done / d.total) * 100) : 0;
            bar.style.width = pct + "%";
            info.textContent = `المنصة: ${d.platform} | التقدم: ${d.done}/${d.total} (${pct}%) | المدة: ${d.elapsed}ث | متاح ظاهرياً: ${d.available} | مأخوذ: ${d.taken} | محظور/مقيد: ${d.blocked}`;

            list.innerHTML = (d.items || []).map(x => {
                const cls = x.status === "available" ? "ok" : (x.status === "taken" ? "taken" : "warn");
                return `<div class="${cls}">@${x.u} -> ${x.txt}</div>`;
            }).join("");

            if (!d.running) {
                startBtn.disabled = false;
                stopBtn.disabled = true;
                if (pollTimer) {
                    clearInterval(pollTimer);
                    pollTimer = null;
                }
            }
        }

        stopBtn.onclick = async () => {
            stopBtn.disabled = true;
            await fetch("/stop", { method: "POST" });
            poll();
        };

        f.onsubmit = async (e) => {
            e.preventDefault();
            startBtn.disabled = true;
            stopBtn.disabled = false;
            msg.textContent = "";
            availGrid.innerHTML = "";
            list.innerHTML = "";
            info.textContent = "جاري توليد اليوزرات وبدء الفحص...";

            const body = new URLSearchParams({
                platform: currentPlatform,
                length: document.getElementById("length").value,
                count: document.getElementById("count").value,
                prefix: document.getElementById("prefix").value,
                suffix: document.getElementById("suffix").value,
                mode: document.getElementById("mode").value,
                workers: document.getElementById("workers").value,
            });

            await fetch("/start", { method: "POST", body });
            if (pollTimer) clearInterval(pollTimer);
            pollTimer = setInterval(poll, 350);
            poll();
        };
    </script>
</body>
</html>
"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}
ALLOWED = set(string.ascii_lowercase + string.digits + "_.")


def clean_affix(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c in ALLOWED).strip(".")


def gen_users(count: int, length: int, mode: str, prefix: str, suffix: str) -> list[str]:
    if mode == "alpha":
        pool = string.ascii_lowercase
    elif mode == "underscore":
        pool = string.ascii_lowercase + string.digits + "_"
    else:
        pool = string.ascii_lowercase + string.digits

    fb = string.ascii_lowercase + string.digits
    core_len = max(1, length - len(prefix) - len(suffix))
    seen = set()
    out = []
    max_attempts = count * 6 + 200

    for _ in range(max_attempts):
        if len(out) >= count:
            break
        core = "".join(random.choices(pool, k=core_len)).strip("_") or "".join(random.choices(fb, k=core_len))
        u = clean_affix(f"{prefix}{core}{suffix}")
        if len(u) >= 2 and u not in seen:
            seen.add(u)
            out.append(u)

    while len(out) < count:
        rand_tag = "".join(random.choices(fb, k=max(2, core_len)))
        u = clean_affix(f"{prefix}{rand_tag}{suffix}")
        if u not in seen:
            seen.add(u)
            out.append(u)
        else:
            out.append(f"{u[:12]}{random.randint(10, 99)}")

    return out[:count]


def check_platform_username(platform: str, u: str, session: requests.Session) -> tuple[str, str]:
    try:
        if platform == "youtube":
            r = session.get(f"https://www.youtube.com/@{u}", headers=HEADERS, timeout=4)
            if r.status_code == 404:
                return "available", "غير موجود ظاهرياً (404)"
            if r.status_code == 200:
                if "This page isn't available" in r.text or "404 Not Found" in r.text:
                    return "available", "غير متاح / غير موجود"
                return "taken", "مستخدم (200)"
            if r.status_code in (403, 429):
                return "blocked", f"مقيد مؤقتاً ({r.status_code})"
            return "blocked", f"HTTP {r.status_code}"

        if platform == "discord":
            r = session.post(
                "https://discord.com/api/v9/unique-username/username-attempt-unauthenticated",
                json={"username": u},
                headers={**HEADERS, "Content-Type": "application/json"},
                timeout=4,
            )
            if r.status_code == 200:
                data = r.json() if r.content else {}
                if data.get("taken") is False:
                    return "available", "غير مأخوذ حالياً (200)"
                if data.get("taken") is True:
                    return "taken", "مأخوذ (200)"
                return "blocked", "استجابة غير مؤكدة"
            if r.status_code in (403, 429):
                return "blocked", f"مقيد/حماية ({r.status_code})"
            return "blocked", f"HTTP {r.status_code}"

        r = session.get(f"https://www.tiktok.com/@{u}", headers=HEADERS, timeout=4)
        if r.status_code == 404:
            return "
            
