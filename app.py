from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
import string
import threading
import time
from flask import Flask, Response, jsonify, render_template_string, request
import requests

app = Flask(__name__)
MAX_USERNAMES = 1000

lock = threading.Lock()
state = {
    "running": False,
    "stop": False,
    "done": 0,
    "total": 0,
    "elapsed": 0.0,
    "s404": 0,
    "s200": 0,
    "s403": 0,
    "items": [],
}

HTML_LINES = [
    "<!DOCTYPE html>",
    '<html lang="ar" dir="rtl">',
    "<head>",
    '    <meta charset="UTF-8">',
    '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
    "    <title>صائد يوزرات تيك توك</title>",
    "    <style>",
    "        * { box-sizing: border-box; }",
    "        body { background: #000; color: #e5e7eb; font-family: Tahoma, sans-serif; padding: 12px; margin: 0; }",
    "        .wrap { max-width: 520px; margin: 10px auto; background: #050505; border: 1px solid #18181b; border-radius: 10px; padding: 14px; }",
    "        h2 { margin: 0 0 12px; text-align: center; color: #ef4444; font-size: 18px; }",
    "        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }",
    "        label { display: block; margin-top: 8px; font-size: 12px; color: #d1d5db; }",
    "        input, select, button { width: 100%; margin-top: 4px; padding: 8px 10px; border-radius: 8px; border: 1px solid #18181b; background: #0a0a0c; color: #f9fafb; font-size: 13px; }",
    "        .btns { display: grid; grid-template-columns: 2fr 1fr; gap: 8px; margin-top: 12px; }",
    "        button { margin-top: 0; background: #991b1b; border: none; font-weight: bold; cursor: pointer; }",
    "        button.sec { background: #18181b; font-size: 12px; }",
    "        button:disabled { opacity: 0.45; }",
    "        .bar-bg { margin-top: 10px; height: 8px; background: #111115; border-radius: 6px; overflow: hidden; }",
    "        .bar { height: 100%; width: 0%; background: #ef4444; }",
    "        .box { margin-top: 12px; background: #0a0a0c; border: 1px solid #18181b; border-radius: 8px; padding: 10px; font-size: 12px; max-height: 300px; overflow-y: auto; }",
    "        .c404 { color: #4ade80; }",
    "        .c200 { color: #f87171; }",
    "        .c403 { color: #facc15; }",
    "    </style>",
    "</head>",
    "<body>",
    '    <div class="wrap">',
    "        <h2>صائد يوزرات تيك توك</h2>",
    '        <form id="f">',
    '            <div class="row">',
    "                <div>",
    "                    <label>الطول (3 - 12)</label>",
    '                    <input type="number" id="length" min="3" max="12" value="5" required>',
    "                </div>",
    "                <div>",
    "                    <label>العدد (1 - 1000)</label>",
    '                    <input type="number" id="count" min="1" max="1000" value="300" required>',
    "                </div>",
    "            </div>",
    '            <div class="row">',
    "                <div>",
    "                    <label>بادئة</label>",
    '                    <input type="text" id="prefix" maxlength="5" placeholder="اختياري">',
    "                </div>",
    "                <div>",
    "                    <label>لاحقة</label>",
    '                    <input type="text" id="suffix" maxlength="5" placeholder="اختياري">',
    "                </div>",
    "            </div>",
    '            <div class="row">',
    "                <div>",
    "                    <label>النوع</label>",
    '                    <select id="mode">',
    '                        <option value="alnum">حروف وأرقام</option>',
    '                        <option value="alpha">حروف فقط</option>',
    '                        <option value="underscore">حروف وأرقام و _</option>',
    "                    </select>",
    "                </div>",
    "                <div>",
    "                    <label>العمال (1 - 5)</label>",
    '                    <input type="number" id="workers" min="1" max="5" value="2" required>',
    "                </div>",
    "            </div>",
    '            <div class="btns">',
    '                <button type="submit" id="startBtn">بدء الفحص</button>',
    '                <button type="button" class="sec" id="stopBtn" disabled>إيقاف</button>',
    "            </div>",
    "        </form>",
    '        <div class="bar-bg"><div class="bar" id="bar"></div></div>',
    '        <div class="box" id="box" style="display:none;">',
    '            <div id="info" style="color:#9ca3af;margin-bottom:6px;"></div>',
    '            <div class="row" style="margin-bottom:8px;">',
    '                <button type="button" class="sec" id="copyBtn">نسخ 404</button>',
    '                <a href="/export"><button type="button" class="sec">تصدير 404</button></a>',
    "            </div>",
    '            <div id="msg" style="color:#4ade80;margin-bottom:6px;"></div>',
    '            <div id="list"></div>',
    "        </div>",
    "    </div>",
    "    <script>",
    '        const f = document.getElementById("f");',
    '        const startBtn = document.getElementById("startBtn");',
    '        const stopBtn = document.getElementById("stopBtn");',
    '        const copyBtn = document.getElementById("copyBtn");',
    '        const bar = document.getElementById("bar");',
    '        const box = document.getElementById("box");',
    '        const info = document.getElementById("info");',
    '        const msg = document.getElementById("msg");',
    '        const list = document.getElementById("list");',
    "        let latest = [];",
    "        let t = null;",
    "        async function poll() {",
    '            const r = await fetch("/status");',
    "            const d = await r.json();",
    "            latest = d.items || [];",
    "            const pct = d.total ? Math.round((d.done / d.total) * 100) : 0;",
    '            bar.style.width = pct + "%";',
    '            box.style.display = "block";',
    "            info.textContent = `التقدم: ${d.done}/${d.total} (${pct}%) | المدة: ${d.elapsed}ث | 404: ${d.s404} | 200: ${d.s200} | 403: ${d.s403}`;",
    "            list.innerHTML = latest.slice(-100).map(x => {",
    '                const cls = x.code === "404" ? "c404" : (x.code === "200" ? "c200" : (x.code === "403" ? "c403" : ""));',
    "                return `<div class=\"${cls}\">@${x.u} -> ${x.txt}</div>`;",
    '            }).join("");',
    "            if (!d.running) {",
    "                startBtn.disabled = false;",
    "                stopBtn.disabled = true;",
    "                if (t) { clearInterval(t); t = null; }",
    "            }",
    "        }",
    "        copyBtn.onclick = async () => {",
    '            const free = latest.filter(x => x.code === "404").map(x => "@" + x.u);',
    '            if (!free.length) { msg.textContent = "لا توجد نتائج 404."; return; }',
    "            try {",
    '                await navigator.clipboard.writeText(free.join("\\n"));',
    "                msg.textContent = `تم نسخ ${free.length} يوزر.`;",
    "            } catch {",
    '                msg.textContent = "تعذر النسخ، استخدم تصدير 404.";',
    "            }",
    "        };",
    "        stopBtn.onclick = async () => {",
    "            stopBtn.disabled = true;",
    '            await fetch("/stop", { method: "POST" });',
    "            poll();",
    "        };",
    "        f.onsubmit = async (e) => {",
    "            e.preventDefault();",
    "            startBtn.disabled = true;",
    "            stopBtn.disabled = false;",
    '            msg.textContent = "";',
    '            box.style.display = "block";',
    '            info.textContent = "جاري البدء...";',
    '            list.innerHTML = "";',
    "            const body = new URLSearchParams({",
    '                length: document.getElementById("length").value,',
    '                count: document.getElementById("count").value,',
    '                prefix: document.getElementById("prefix").value,',
    '                suffix: document.getElementById("suffix").value,',
    '                mode: document.getElementById("mode").value,',
    '                workers: document.getElementById("workers").value,',
    "            });",
    '            await fetch("/start", { method: "POST", body });',
    "            if (t) clearInterval(t);",
    "            t = setInterval(poll, 400);",
    "            poll();",
    "        };",
    "    </script>",
    "</body>",
    "</html>",
]
HTML = "\n".join(HTML_LINES)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
}
ALLOWED = set(string.ascii_lowercase + string.digits + "_.")


def clean_affix(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c in ALLOWED).strip(".")


def gen_users(count: int, length: int, mode: str, prefix: str, suffix: str) -> list[str]:
    pool = (
        string.ascii_lowercase
        if mode == "alpha"
        else (
            string.ascii_lowercase + string.digits + "_"
            if mode == "underscore"
            else string.ascii_lowercase + string.digits
        )
    )
    fb = string.ascii_lowercase + string.digits
    core_len = max(1, length - len(prefix) - len(suffix))
    seen = set()
    out = []
    for _ in range(count * 4):
        if len(out) >= count:
            break
        core = "".join(random.choices(pool, k=core_len)).strip("_") or "".join(
            random.choices(fb, k=core_len)
        )
        u = clean_affix(f"{prefix}{core}{suffix}")
        if len(u) >= 2 and u not in seen:
            seen.add(u)
            out.append(u)
    while len(out) < count:
        u = clean_affix(f"{prefix}{''.join(random.choices(fb, k=core_len))}{suffix}")
        out.append(u)
    return out[:count]


def check_u(u: str, session: requests.Session, t0: float) -> None:
    with lock:
        if state["stop"]:
            return
    time.sleep(random.uniform(0.15, 0.35))
    with lock:
        if state["stop"]:
            return
    try:
        r = session.get(f"https://www.tiktok.com/@{u}", headers=HEADERS, timeout=3)
        sc = str(r.status_code)
        txt = (
            "غير مستخدم ظاهرياً (404)"
            if r.status_code == 404
            else ("مستخدم (200)" if r.status_code == 200 else f"HTTP {r.status_code}")
        )
    except requests.RequestException as e:
        sc = "err"
        txt = e.__class__.__name__

    with lock:
        if state["stop"]:
            return
        state["done"] += 1
        state["elapsed"] = round(time.perf_counter() - t0, 1)
        if sc == "404":
            state["s404"] += 1
        elif sc == "200":
            state["s200"] += 1
        elif sc == "403":
            state["s403"] += 1
        state["items"].append({"u": u, "code": sc, "txt": txt})


def worker_job(length: int, count: int, mode: str, prefix: str, suffix: str, workers: int) -> None:
    t0 = time.perf_counter()
    users = gen_users(count, length, mode, prefix, suffix)
    with lock:
        state.update({
            "running": True,
            "stop": False,
            "done": 0,
            "total": len(users),
            "elapsed": 0.0,
            "s404": 0,
            "s200": 0,
            "s403": 0,
            "items": [],
        })

    with requests.Session() as s:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(check_u, u, s, t0) for u in users]
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
    length = max(3, min(12, int(request.form.get("length", 5))))
    count = max(1, min(MAX_USERNAMES, int(request.form.get("count", 300))))
    mode = request.form.get("mode", "alnum")
    prefix = clean_affix(request.form.get("prefix", ""))
    suffix = clean_affix(request.form.get("suffix", ""))
    workers = max(1, min(5, int(request.form.get("workers", 2))))
    threading.Thread(
        target=worker_job, args=(length, count, mode, prefix, suffix, workers), daemon=True
    ).start()
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
    with lock:
        free = [f"@{x['u']}" for x in state["items"] if x["code"] == "404"]
    return Response(
        "\n".join(free) + ("\n" if free else ""),
        mimetype="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=404.txt"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
