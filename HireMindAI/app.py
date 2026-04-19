# =========================================================
# 📦 IMPORTS
# =========================================================
from flask import Flask, render_template, request, jsonify
from flask import Flask, render_template, jsonify, request   # duplicate import (kept but unused)
from flask_cors import CORS
import os
import time

from pypdf import PdfReader
from docx import Document

from groq import Groq, RateLimitError
from dotenv import load_dotenv

from functools import wraps

import edge_tts
import asyncio

# ❌ OPENAI NOT USED ANYMORE (Groq is used instead)
# from openai import OpenAI
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

resume_text = ""


# =========================================================
# ⚙️ APP INITIALIZATION
# =========================================================
app = Flask(__name__)
CORS(app)
load_dotenv()

os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)
app.config["UPLOAD_FOLDER"] = "uploads"


# =========================================================
# 🔑 API CLIENTS
# =========================================================
GROQ_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_KEY)


# =========================================================
# 🧠 GLOBAL AI SETTINGS
# =========================================================
FAST_MODEL = "llama-3.1-8b-instant"
SMART_MODEL = "llama-3.3-70b-versatile"


# =========================================================
# 🤖 UNIVERSAL GROQ CALL
# =========================================================
def ask_groq(messages, model=FAST_MODEL, temperature=0.7):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature
        )
        return chat_completion.choices[0].message.content

    except RateLimitError:
        print("⚠️ Groq Rate Limit Hit")
        return "AI busy. Please wait 2–3 minutes."

    except Exception as e:
        print("❌ Groq Error:", e)
        return "AI temporarily unavailable."


# =========================================================
# 🧠 MEMORY
# =========================================================
resume_uploaded = False
resume_filename = ""
resume_analysis = ""
resume_filepath = ""
resume_text = ""
chat_history = []
resume_data_json = ""   # ⭐ missing variable FIXED


# =========================================================
# 📄 FILE VALIDATION
# =========================================================
ALLOWED_EXTENSIONS = {"pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def check_resume_uploaded():
    return resume_uploaded


# =========================================================
# 🔐 GLOBAL RESUME GUARD (Blocks API until resume uploaded)
# =========================================================
def require_resume(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global resume_uploaded
        if not resume_uploaded:
            return jsonify({
                "error": "resume_required",
                "message": "🤖 पहले अपना resume upload करें 😊"
            }), 400
        return func(*args, **kwargs)
    return wrapper


# =========================================================
# 🏠 ROUTES
# =========================================================
@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# 📄 TEXT EXTRACTION
# =========================================================
def extract_text_from_pdf(path):
    text = ""
    reader = PdfReader(path)
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(path):
    text = ""
    doc = Document(path)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_resume_text(filepath):
    if filepath.endswith(".pdf"):
        return extract_text_from_pdf(filepath)
    elif filepath.endswith(".docx"):
        return extract_text_from_docx(filepath)
    return ""


# =========================================================
# 📄 RESUME → STRUCTURED JSON  ⭐ MISSING FUNCTION ADDED
# =========================================================
def extract_resume_structured_data(text):
    prompt = f"""
Resume ko analyze karke structured JSON banao.

Fields:
name
skills
projects
experience
education

Resume:
{text}
"""
    return ask_groq([{"role": "user", "content": prompt}], model=FAST_MODEL)


# =========================================================
# 📤 RESUME UPLOAD (FULL AI PIPELINE)
# =========================================================
@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    global resume_uploaded, resume_filename, resume_filepath
    global resume_text, resume_data_json, resume_analysis

    file = request.files.get("resume")
    if not file:
        return jsonify({"message": "No file uploaded"}), 400

    new_filename = str(int(time.time())) + "_" + file.filename
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
    file.save(filepath)

    resume_text = extract_resume_text(filepath)[:8000]
    if resume_text.strip() == "":
        return jsonify({"message": "Resume text not found"}), 400

    print("📄 Resume text extracted")

    resume_data_json = extract_resume_structured_data(resume_text)
    print("🧠 Resume structured JSON created")

    resume_analysis = analyze_resume_with_ai(resume_text)
    print("🔎 Resume analysis completed")

    resume_uploaded = True
    resume_filename = new_filename
    resume_filepath = filepath

    return jsonify({"message": "Resume uploaded & analyzed successfully"})


# =========================================================
# 📄 RESUME ANALYSIS
# =========================================================
def analyze_resume_with_ai(text):
    prompt = f"""
आप एक SENIOR HR RECRUITER हैं।
उत्तर केवल हिन्दी में दें।

Resume:
{text}
"""
    return ask_groq([{"role": "user", "content": prompt}], model=SMART_MODEL)


# =========================================================
# 🎙️ VOICE GENERATOR
# =========================================================
def detect_language(text):
    hindi_chars = "अआइईउऊएऐओऔकखगघचछजझटठडढतथदधनपफबभमयरलवशषसह"
    for ch in text:
        if ch in hindi_chars:
            return "hindi"
    return "english"


def generate_voice(text):
    try:
        audio_path = "static/voice.mp3"

        # ⭐ LANGUAGE AUTO DETECT
        lang = detect_language(text)

        if lang == "hindi":
            voice = "hi-IN-SwaraNeural"     # Hindi Female 🇮🇳
        else:
            voice = "en-IN-NeerjaNeural"    # English Female 🇮🇳

        async def tts():
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate="+5%",
                pitch="+2Hz"
            )
            await communicate.save(audio_path)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(tts())
        loop.close()

        print("🔊 Voice generated:", voice)
        return "/static/voice.mp3"

    except Exception as e:
        print("Voice error:", e)
        return None


# =========================================================
# 🤖 INTERVIEW AI
# =========================================================
def ask_interviewer_ai(user_message):
    global chat_history, resume_text, resume_analysis

    SYSTEM_PROMPT = f"""
You are a SENIOR HR INTERVIEWER.
Ask resume-based interview questions in Hindi.

Resume:
{resume_text}

HR Notes:
{resume_analysis}
"""

    chat_history.append({"role": "user", "content": user_message})
    chat_history[:] = chat_history[-10:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
    ai_reply = ask_groq(messages)

    chat_history.append({"role": "assistant", "content": ai_reply})
    return ai_reply


# =========================================================
# 💬 CHAT ROUTE
# =========================================================
@app.route("/chat", methods=["POST"])
@require_resume
def chat():
    if not check_resume_uploaded():
        return jsonify({"error": "Upload resume first"}), 400

    user_message = request.json.get("message")
    ai_reply = ask_interviewer_ai(user_message)
    audio = generate_voice(ai_reply)

    return jsonify({"reply": ai_reply, "audio": audio})


# =========================================================
# 🎤 START INTERVIEW WITH RESUME (FINAL)
# =========================================================
@app.route("/start_interview_resume", methods=["POST"])
@require_resume
def start_interview_resume():
    global chat_history, resume_text

    print("🎤 Resume interview started")

    chat_history = []

    first_q = f"""
Namaste! Aapke resume ko dhyan se padhne ke baad
main aapka AI HR interviewer hoon 😊

Chaliye interview shuru karte hain.

Sabse pehla sawal:

Aap apne baare me batayein aur apne recent projects
aur skills ka short introduction dein.
"""

    chat_history.append({"role": "assistant", "content": first_q})

    audio = generate_voice(first_q)

    return jsonify({
        "question": first_q,
        "audio": audio
    })


# =========================================================
# ▶ RUN
# =========================================================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)