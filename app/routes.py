from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
from .main import translate_text, parse_srt, extract_sentences_from_srt, translate_sentences, rebuild_srt
from app.db import get_db_connection
from datetime import datetime


main_bp = Blueprint("main", __name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@main_bp.route("/")
def home():
    return render_template("home.html")


#자막등록
@main_bp.route("/translate", methods=["GET"])
def show_translate_form():
    from app.db import get_db_connection
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return render_template("translate_form.html", clients=clients)

#자막 업로드
@main_bp.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("srt_file")
    client_id = request.form.get("client_id")
    order_id = request.form.get("order_id")

    if not file or not file.filename.endswith(".srt"):
        return "유효한 SRT 파일을 업로드해 주세요."

    if not order_id:
        return "order_id가 누락되었습니다."
    conn = get_db_connection()
    order = conn.execute("SELECT order_number FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()

    if not order:
        return "해당 주문을 찾을 수 없습니다."

    order_number = order["order_number"]
    filename = f"{order_number}.srt"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return redirect(url_for("main.edit_translation", order_id=order_id))
    file.save(filepath)
    return render_template("translate.html", filename=filename, client_id=client_id)


#자막 번역
@main_bp.route("/translate", methods=["POST"])
def translate_uploaded_file():
    client_id = request.form.get("client_id")
    filename = request.form.get("filename")
    filepath = os.path.join("uploads", filename)

    if not os.path.exists(filepath):
        return "파일이 존재하지 않습니다."

    with open(filepath, "r", encoding="utf-8") as f:
        srt_content = f.read()

    subtitles = parse_srt(srt_content)
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}:{m:02}:{s:02}"

    def parse_timestamp(ts):
        start_str, end_str = ts.split(" --> ")

        def to_seconds(t):
            h, m, rest = t.split(":")
            s, ms = rest.split(",")
            return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

        return to_seconds(start_str), to_seconds(end_str)

    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}:{m:02}:{s:02}"

    for s in subtitles:
        start_sec, end_sec = parse_timestamp(s['timestamp'])
        s['start_formatted'] = format_time(start_sec)
        s['end_formatted'] = format_time(end_sec)


    sentences = extract_sentences_from_srt(srt_content)
    translated = translate_sentences(sentences, client_id=client_id)

    return render_template(
        "edit.html",
        zipped=zip(subtitles, translated),
        filename=filename
    )


#자막 다운로드
@main_bp.route("/download/<path:filename>")
def download_file(filename):
    upload_dir = os.path.join(os.path.dirname(__file__), "../uploads")
    return send_from_directory(upload_dir, filename, as_attachment=True)

#자막 수정
@main_bp.route("/orders/<int:order_id>/edit")
def edit_translation(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT order_number, client_id FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()

    if not order:
        return "해당 주문을 찾을 수 없습니다.", 404

    order_number = order["order_number"]
    filename = f"{order_number}.srt"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    translated_path = os.path.join(UPLOAD_FOLDER, f"{order_number}_translated.srt")

    if not os.path.exists(filepath):
        return "원문 자막 파일이 존재하지 않습니다.", 404

    with open(filepath, "r", encoding="utf-8") as f:
        srt_content = f.read()
    subtitles = parse_srt(srt_content)
    if os.path.exists(translated_path):
        with open(translated_path, "r", encoding="utf-8") as tf:
            translated = [line.strip() for line in tf.readlines()]
    else:
        sentences = extract_sentences_from_srt(srt_content)
        translated = translate_sentences(sentences, client_id=order["client_id"])

    return render_template(
        "edit.html",
        zipped=zip(subtitles, translated),
        filename=filename
    )
@main_bp.route("/save_edited", methods=["POST"])
def save_edited():
    filename = request.form.get("filename")  # 원본 파일명 (ORD-xxxx.srt)
    base_name, _ = os.path.splitext(filename)
    translated_filename = f"{base_name}_translated.srt"
    translated_path = os.path.join("uploads", translated_filename)

    filepath = os.path.join("uploads", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        srt_content = f.read()
    subtitles = parse_srt(srt_content)

    edited_translations = []
    for i in range(len(subtitles)):
        edited = request.form.get(f"translation_{i}", "").strip()
        edited_translations.append(edited)
    with open(translated_path, "w", encoding="utf-8") as f:
        for t in edited_translations:
            f.write(t + "\n")

    download_link = url_for("main.download_file", filename=translated_filename)
    return f"""
    <div style="max-width: 600px; margin: 60px auto; text-align: center; font-family: 'Segoe UI', sans-serif;">
    <div style="background: #fff0f5; padding: 40px; border-radius: 20px; box-shadow: 0 4px 12px rgba(255,120,180,0.15);">
        <div style="font-size: 2rem; margin-bottom: 20px;">✅ 저장 완료!</div>
        <p style="font-size: 1.1rem; margin-bottom: 30px;">수정된 번역 파일이 저장되었습니다.</p>
        <a href="{download_link}" style="
            display: inline-block;
            background-color: #ff4c8b;
            color: white;
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 1rem;
            text-decoration: none;
            margin: 0 10px;
        ">📥 다운로드</a>
        <a href="/orders" style="
            display: inline-block;
            background-color: #ccc;
            color: #333;
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 1rem;
            text-decoration: none;
            margin: 0 10px;
        ">📋 의뢰 목록</a>
    </div>
    </div>
    """

@main_bp.route("/save_draft", methods=["POST"])
def save_draft():
    filename = request.form.get("filename")  # 예: ORD-25-0001.srt
    base_name, _ = os.path.splitext(filename)
    translated_filename = f"{base_name}_translated.srt"
    translated_path = os.path.join("uploads", translated_filename)

    filepath = os.path.join("uploads", filename)
    if not os.path.exists(filepath):
        return "원문 자막 파일이 존재하지 않습니다.", 404

    with open(filepath, "r", encoding="utf-8") as f:
        srt_content = f.read()
    subtitles = parse_srt(srt_content)

    edited_translations = []
    for i in range(len(subtitles)):
        edited = request.form.get(f"translation_{i}", "").strip()
        edited_translations.append(edited)

    with open(translated_path, "w", encoding="utf-8") as f:
        for t in edited_translations:
            f.write(t + "\n")

    return """
    <div style="max-width: 600px; margin: 60px auto; text-align: center; font-family: 'Segoe UI', sans-serif;">
    <div style="background: #fff0f5; padding: 40px; border-radius: 20px; box-shadow: 0 4px 12px rgba(255,120,180,0.15);">
        <div style="font-size: 2rem; margin-bottom: 20px;">📥 임시 저장 완료</div>
        <p style="font-size: 1.1rem; margin-bottom: 30px;">창을 닫거나 다른 메뉴로 이동해도 수정 내용은 유지됩니다.</p>
        <a href="/orders" style="
            display: inline-block;
            background-color: #ccc;
            color: #333;
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 1rem;
            text-decoration: none;
        ">📋 의뢰 목록으로 돌아가기</a>
    </div>
    </div>
    """

#클라이언트
@main_bp.route("/clients")
def client_list():
    from app.db import get_db_connection
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return render_template("clients.html", clients=clients)

#클라이언트 추가
@main_bp.route("/clients/add", methods=["GET", "POST"])
def add_client():
    from app.db import get_db_connection
    if request.method == "POST":
        name = request.form.get("name")
        rate = request.form.get("rate")
        glossary_path = request.form.get("glossary_path")
        channel = request.form.get("channel")
        channel_link = request.form.get("channel_link")
        others = request.form.get("others")

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO clients (name, rate, glossary_path, channel, channel_link, others)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, rate, glossary_path, channel, channel_link, others)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("main.client_list"))

    return render_template("add_client.html")

#클라이언트 용어집
@main_bp.route("/clients/<int:client_id>/glossary", methods=["GET", "POST"])
def manage_glossary(client_id):
    from app.db import get_db_connection
    conn = get_db_connection()

    if request.method == "POST":
        korean = request.form.get("korean")
        english = request.form.get("english")

        conn.execute(
            "INSERT INTO glossaries (client_id, korean, english) VALUES (?, ?, ?)",
            (client_id, korean, english)
        )
        conn.commit()

    # glossary 목록 불러오기
    glossary = conn.execute(
        "SELECT * FROM glossaries WHERE client_id = ?", (client_id,)
    ).fetchall()
    conn.close()

    return render_template("glossary.html", glossary=glossary, client_id=client_id)

#작업의뢰
@main_bp.route("/orders/add", methods=["GET", "POST"])
def add_order():
    conn = get_db_connection()
    if request.method == "POST":
        client_id = int(request.form["client_id"])
        video_link = request.form["video_link"]
        rate = int(request.form["rate_per_minute"])
        video_length = request.form["video_length"]
        deadline = request.form["deadline"]
        settlement_due = request.form["settlement_due"]
        h, m, s = map(int, video_length.split(":"))
        total_minutes = h * 60 + m + s / 60
        price = round(total_minutes * rate)

        order_number = generate_order_number(client_id)

        conn.execute("""
            INSERT INTO orders (
                client_id, video_link, rate_per_minute, video_length,
                price, deadline, settlement_due, order_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (client_id, video_link, rate, video_length, price, deadline, settlement_due, order_number))
        conn.commit()
        conn.close()
        return redirect(url_for("main.view_orders"))

    clients = conn.execute("SELECT id, name FROM clients").fetchall()
    conn.close()
    return render_template("add_order.html", clients=clients)

#의뢰목록
@main_bp.route("/orders")
def view_orders():
    import os

    conn = get_db_connection()
    raw_orders = conn.execute("""
        SELECT o.*, c.name AS client_name
        FROM orders o
        JOIN clients c ON o.client_id = c.id
        ORDER BY o.created_at DESC
    """).fetchall()
    conn.close()

    orders = []
    for order in raw_orders:
        order = dict(order)  # sqlite3.Row → dict 변환
        edited_filename = f"edited_{order['order_number']}.srt"
        edited_path = os.path.join("uploads", edited_filename)
        order["edited_srt_exists"] = os.path.exists(edited_path)
        orders.append(order)

    return render_template("orders.html", orders=orders, datetime=datetime)
@main_bp.route("/orders/update_status", methods=["POST"])
def update_order_status():
    import json
    from flask import jsonify

    data = request.get_json()
    order_id = data.get("order_id")
    field = data.get("field")
    value = data.get("value")

    if field not in [
        "delivered", "revision_requested", "revision_completed", "settlement_completed"
    ]:
        return jsonify({"error": "Invalid field"}), 400

    conn = get_db_connection()
    conn.execute(f"UPDATE orders SET {field} = ? WHERE id = ?", (value, order_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True})
@main_bp.route("/orders/<int:order_id>/translate")
def translate_order(order_id):
    conn = get_db_connection()
    order = conn.execute("""
        SELECT o.*, c.name AS client_name
        FROM orders o
        JOIN clients c ON o.client_id = c.id
        WHERE o.id = ?
    """, (order_id,)).fetchone()
    conn.close()

    if order is None:
        return "해당 의뢰를 찾을 수 없습니다.", 404
    
    conn = get_db_connection()
    clients = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()

    return render_template("translate_form.html", order=order, clients=clients)

#주문번호
def generate_order_number(client_id):
    year_short = datetime.now().strftime("%y")
    client_str = str(client_id).zfill(2)  

    prefix = f"ORD-{year_short}-{client_str}" 
    like_pattern = prefix + "%"

    conn = get_db_connection()
    latest = conn.execute("""
        SELECT order_number FROM orders
        WHERE order_number LIKE ?
        ORDER BY order_number DESC LIMIT 1
    """, (like_pattern,)).fetchone()

    if latest:
        last_num_str = latest["order_number"][-2:] 
        last_num = int(last_num_str)
        new_num = last_num + 1 if last_num < 99 else 1 
    else:
        new_num = 1

    conn.close()

    order_num = f"{prefix}{str(new_num).zfill(2)}"
    return order_num

#작업저장
@main_bp.route("/orders/<int:order_id>/handle")
def handle_order_click(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT order_number FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()

    if not order:
        return "해당 주문을 찾을 수 없습니다.", 404

    filename = f"{order['order_number']}.srt"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(filepath):
        return redirect(url_for("main.edit_translation", order_id=order_id))
    else:
        return redirect(url_for("main.translate_order", order_id=order_id))
