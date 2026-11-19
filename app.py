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

HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>صائد يوزرات تيك توك</title>
    <style>
        * { box-sizing: border-box; }
        body { background: #000; color: #e5e7eb; font-family: Tahoma, sans-serif; padding: 12px; margin: 0; }
        .wrap { max-width: 520px; margin: 10px auto; background: #050505; border: 1px solid #18181b; border-radius: 10px; padding: 14px; }
        h2 { margin: 0 0 12px; text-align: center; color: #ef4444; font-size: 18px; }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        label { display: block; margin-top: 8px; font-size: 12px; color: #d1d5db; }
        input, select, button { width: 100%; margin-top: 4px; padding: 8px 10px; border-radius: 8px; border: 1px solid #18181b; background: #0a0a0c; color: #f9fafb; font-size: 13px; }
        .btns { display: grid; grid-template-columns: 2fr 1fr; gap: 8px; margin-top: 12px; }
        button { margin-top: 0; background: #991b1b; border: none; font-weight: bold; cursor: pointer; }
        button.sec { background: #18181b; font-size: 12px; }
        button:disabled { opacity: 0.45; }
        .bar-bg { margin-top: 10px; height: 8px; background: #111115; border-radius: 6px; overflow: hidden; }
        .bar { height: 100%; width: 0%; background: #ef4444; }
        .box { margin-top: 12px; background: #0a0a0c; border: 1px solid #18181b; border-radius: 8px; padding: 10px; font-size: 12px; max-height: 300px; overflow-y: auto; }
        .c404 { color: #4ade80; }
        .c200 { color: #f87171; }
        .c403 { color: #facc15; }
    </style>
</head>
<body>
    <div class="wrap">
        <h2>صائد يوزرات تيك توك</h2>
        <form id="f">
            <div class="row">
                <div>
                    <label>الطول (3 - 12)</label>
                    <input type="number" id="length" min="3" max="12" value="5" required>
                </div>
                <div>
                    <label>العدد (1 - 1000)</label>
                    <input type="number" id="count" min="1" max="1000" value="300" required>
                </div>
            </div>
            <div class="row">
                <div>
                    <label>بادئة</label>
                    <input type="text" id="prefix" maxlength="5" placeholder="اختياري">
                </div>
                <div>
                    <label>لاحقة</label>
                    <input type="text" id="suffix" maxlength="5" placeholder="اختياري">
                </div>
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
                <div>
                    <label>العمال (1 - 5)</label>
                    <input type="number" id="workers" min="1" max="5" value="2" required>
                </div>
            </div>
            <div class="btns">
                <button type="submit" id
                
