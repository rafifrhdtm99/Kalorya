# -*- coding: utf-8 -*-
import streamlit as st
import google.generativeai as genai
from PIL import Image
import re
import uuid
import json
from datetime import datetime, timezone, timedelta

# Zona waktu WIB (GMT+7)
WIB = timezone(timedelta(hours=7))

def get_today_str():
    return datetime.now(WIB).strftime("%Y-%m-%d")
import pandas as pd
import base64

# Impor Firebase
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Kalorya", page_icon="🌸", layout="centered")

# --- KONFIGURASI FIREBASE ---
db = None
firebase_configured = False

has_firebase_key = False
try:
    if "FIREBASE_KEY" in st.secrets:
        has_firebase_key = True
except Exception:
    pass

if has_firebase_key:
    if not firebase_admin._apps:
        try:
            key_dict = json.loads(st.secrets["FIREBASE_KEY"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            firebase_configured = True
        except Exception as e:
            print(f"Gagal memuat kunci Firebase: {e}")
    else:
        try:
            db = firestore.client()
            firebase_configured = True
        except Exception:
            pass

# --- DATABASE LOKAL (PERSISTENCE FALLBACK) ---
LOCAL_DB_FILE = "kalorya_local_db.json"

def load_local_db():
    import os
    if not os.path.exists(LOCAL_DB_FILE):
        return {}
    try:
        with open(LOCAL_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_local_db(data):
    try:
        with open(LOCAL_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Gagal menyimpan database lokal: {e}")

# --- STATE LOGIN (MULTI-USER) ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None
if 'user_pin' not in st.session_state:
    st.session_state.user_pin = ""

# --- FUNGSI DATABASE ---
def load_data_from_db():
    if not st.session_state.logged_in_user:
        return
    
    username = st.session_state.logged_in_user.lower().strip()
    data = None

    if firebase_configured and db is not None:
        try:
            doc_ref = db.collection('kalorya_users').document(username)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
        except Exception as e:
            print(f"Error loading from Firestore: {e}")
            
    if data is None:
        # Fallback ke database lokal
        local_db = load_local_db()
        data = local_db.get(username)

    if data:
        today_str = get_today_str()
        
        st.session_state.daily_records = data.get('daily_records', {})
        st.session_state.target_calories = data.get('target_calories', 1800)
        
        # Profil Tubuh & Tracker
        st.session_state.bb = data.get('bb', 50)
        st.session_state.bb_awal = data.get('bb_awal', st.session_state.bb)
        st.session_state.bb_target = data.get('bb_target', st.session_state.bb - 5)
        st.session_state.tb = data.get('tb', 160)
        st.session_state.umur = data.get('umur', 20)
        st.session_state.gender = data.get('gender', 'Perempuan')
        st.session_state.weight_history = data.get('weight_history', {})
        
        last_active_date = data.get('last_active_date', today_str)
        st.session_state.last_active_date = last_active_date
        
        if last_active_date != today_str:
            st.session_state.consumed_calories = 0
            st.session_state.consumed_carbs = 0
            st.session_state.consumed_protein = 0
            st.session_state.consumed_fat = 0
            st.session_state.meal_history = []
            st.session_state.last_active_date = today_str
            # Simpan data reset ke DB setelah variabel lain terisi
            save_data_to_db()
        else:
            st.session_state.consumed_calories = data.get('consumed_calories', 0)
            st.session_state.consumed_carbs = data.get('consumed_carbs', 0)
            st.session_state.consumed_protein = data.get('consumed_protein', 0)
            st.session_state.consumed_fat = data.get('consumed_fat', 0)
            st.session_state.meal_history = data.get('meal_history', [])

def save_data_to_db():
    if not st.session_state.logged_in_user:
        return
    
    username = st.session_state.logged_in_user.lower().strip()
    today_str = get_today_str()
    
    daily_records = st.session_state.get('daily_records', {})
    daily_records[today_str] = {
        'calories': st.session_state.consumed_calories,
        'carbs': st.session_state.consumed_carbs,
        'protein': st.session_state.consumed_protein,
        'fat': st.session_state.consumed_fat,
        'meals': st.session_state.meal_history
    }
    
    user_data = {
        'last_active_date': today_str,
        'daily_records': daily_records,
        'consumed_calories': st.session_state.consumed_calories,
        'consumed_carbs': st.session_state.consumed_carbs,
        'consumed_protein': st.session_state.consumed_protein,
        'consumed_fat': st.session_state.consumed_fat,
        'meal_history': st.session_state.meal_history,
        'target_calories': st.session_state.target_calories,
        'bb': st.session_state.get('bb', 50),
        'bb_awal': st.session_state.get('bb_awal', 50),
        'bb_target': st.session_state.get('bb_target', 50),
        'tb': st.session_state.get('tb', 160),
        'umur': st.session_state.get('umur', 20),
        'gender': st.session_state.get('gender', 'Perempuan'),
        'weight_history': st.session_state.get('weight_history', {}),
        'pin': st.session_state.get('user_pin', '')
    }

    # Simpan secara lokal
    local_db = load_local_db()
    local_db[username] = user_data
    save_local_db(local_db)

    # Simpan ke Firestore jika terhubung
    if firebase_configured and db is not None:
        try:
            doc_ref = db.collection('kalorya_users').document(username)
            firestore_data = user_data.copy()
            firestore_data['last_updated'] = firestore.SERVER_TIMESTAMP
            doc_ref.set(firestore_data)
        except Exception as e:
            print(f"Error saving to Firestore: {e}")

# --- HALAMAN LOGIN ---
if st.session_state.logged_in_user is None:
    st.markdown("<h1 style='text-align:center; color:#FFB7B2; font-family:Quicksand;'>Selamat Datang di Kalorya! 🌸</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8D6E63;'>Langkah pertamamu menuju <i>body goals</i> dimulai di sini! Tulis nama panggilanmu dan buat sebuah PIN rahasia biar ruanganmu tidak bisa diintip orang lain. ✨</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        username_input = st.text_input("Siapa namamu?", placeholder="Misal: Sarah")
        pin_input = st.text_input("Buat / Masukkan PIN Rahasia (Bebas Angka/Huruf)", type="password", placeholder="••••")
        submit = st.form_submit_button("Masuk / Buka Ruangan 🚀", use_container_width=True)
        
        if submit and username_input and pin_input:
            username_clean = username_input.lower().strip()
            
            # Coba verifikasi dengan Firestore jika terhubung
            verified = False
            pin_checked = False
            if firebase_configured and db is not None:
                try:
                    doc_ref = db.collection('kalorya_users').document(username_clean)
                    doc = doc_ref.get()
                    if doc.exists:
                        data = doc.to_dict()
                        saved_pin = data.get('pin', '')
                        pin_checked = True
                        if saved_pin != "" and saved_pin != pin_input:
                            st.error("Oops! PIN yang kamu masukkan salah. Coba lagi ya! ❌")
                            st.stop()
                        verified = True
                except Exception:
                    pass

            # Jika tidak terverifikasi via Firestore, coba via database lokal
            if not pin_checked:
                local_db = load_local_db()
                if username_clean in local_db:
                    saved_pin = local_db[username_clean].get('pin', '')
                    if saved_pin != "" and saved_pin != pin_input:
                        st.error("Oops! PIN yang kamu masukkan salah. Coba lagi ya! ❌")
                        st.stop()
            
            st.session_state.logged_in_user = username_input
            st.session_state.user_pin = pin_input
            # Reset state default
            st.session_state.consumed_calories = 0
            st.session_state.consumed_carbs = 0
            st.session_state.consumed_protein = 0
            st.session_state.consumed_fat = 0
            st.session_state.processed_files = set()
            st.session_state.last_response = ""
            st.session_state.uploader_key = str(uuid.uuid4())
            st.session_state.meal_history = [] 
            st.session_state.daily_records = {}
            st.session_state.target_calories = 1800
            st.session_state.weight_history = {}
            st.session_state.bb_awal = 50
            st.session_state.bb_target = 50
            st.session_state.scan_success_message = ""
            # Muat data usernya
            load_data_from_db()
            st.rerun()
    st.stop() # Berhenti di sini kalau belum login

# --- INISIALISASI STATE UTAMA ---
# (Pastikan variabel ada untuk mencegah error)
if 'consumed_calories' not in st.session_state: st.session_state.consumed_calories = 0
if 'consumed_carbs' not in st.session_state: st.session_state.consumed_carbs = 0
if 'consumed_protein' not in st.session_state: st.session_state.consumed_protein = 0
if 'consumed_fat' not in st.session_state: st.session_state.consumed_fat = 0
if 'processed_files' not in st.session_state: st.session_state.processed_files = set()
if 'last_response' not in st.session_state: st.session_state.last_response = ""
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = str(uuid.uuid4())
if 'meal_history' not in st.session_state: st.session_state.meal_history = [] 
if 'daily_records' not in st.session_state: st.session_state.daily_records = {}
if 'target_calories' not in st.session_state: st.session_state.target_calories = 1800
if 'bb' not in st.session_state: st.session_state.bb = 50
if 'bb_awal' not in st.session_state: st.session_state.bb_awal = 50
if 'bb_target' not in st.session_state: st.session_state.bb_target = 50
if 'tb' not in st.session_state: st.session_state.tb = 160
if 'umur' not in st.session_state: st.session_state.umur = 20
if 'gender' not in st.session_state: st.session_state.gender = 'Perempuan'
if 'weight_history' not in st.session_state: st.session_state.weight_history = {}
if 'scan_success_message' not in st.session_state: st.session_state.scan_success_message = ""

# --- CEK PERGANTIAN HARI (MIDNIGHT RESET) ---
today_str = get_today_str()
if 'last_active_date' not in st.session_state:
    st.session_state.last_active_date = today_str

if st.session_state.last_active_date != today_str:
    # 1. Simpan data hari kemarin ke daily_records
    prev_date = st.session_state.last_active_date
    if 'daily_records' not in st.session_state:
        st.session_state.daily_records = {}
        
    st.session_state.daily_records[prev_date] = {
        'calories': st.session_state.consumed_calories,
        'carbs': st.session_state.consumed_carbs,
        'protein': st.session_state.consumed_protein,
        'fat': st.session_state.consumed_fat,
        'meals': st.session_state.meal_history
    }
    
    # 2. Reset tracker harian ke 0 untuk hari baru
    st.session_state.consumed_calories = 0
    st.session_state.consumed_carbs = 0
    st.session_state.consumed_protein = 0
    st.session_state.consumed_fat = 0
    st.session_state.meal_history = []
    st.session_state.processed_files = set()
    st.session_state.last_response = ""
    st.session_state.uploader_key = str(uuid.uuid4())
    
    st.session_state.last_active_date = today_str
    
    # 3. Simpan ke database
    save_data_to_db()
    st.rerun()

# --- KONFIGURASI GEMINI AI ---
api_key_configured = False
has_gemini_key = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        has_gemini_key = True
except Exception:
    pass

if has_gemini_key:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        api_key_configured = True
    except Exception:
        pass

# --- FUNGSI BANTUAN UI ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

bg_base64 = get_base64_of_bin_file("doodle_bg.png")

# --- INJEKSI CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Quicksand', sans-serif !important;
        color: #5D4037 !important;
    }}
    /* Memperlebar tampilan dan memperbesar font di komputer */
    @media (min-width: 768px) {{
        .block-container {{
            max-width: 900px !important;
        }}
        html {{
            font-size: 18px !important;
        }}
    }}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .viewerBadge_container__1QSob, 
    div[class^="viewerBadge"], 
    .viewerBadge_link__1S137,
    a[href*="streamlit"] {{
        display: none !important;
    }}
    .stDeployButton {{display: none !important;}}
    [data-testid="stToolbar"] {{display: none !important;}}
    .stApp {{
        background-color: #FEF9F8 !important;
        background-image: linear-gradient(rgba(254, 249, 248, 0.9), rgba(254, 249, 248, 0.9)), url("data:image/png;base64,{bg_base64}");
        background-size: auto, 350px;
        background-repeat: repeat;
    }}
    .cute-card {{
        background: rgba(255, 255, 255, 0.95);
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(255, 183, 178, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.8);
        margin-bottom: 24px;
    }}
    [data-testid="stFileUploadDropzone"] {{
        background-color: #FFB7B2 !important;
        border: 2px dashed #FFF !important;
        border-radius: 24px !important;
        padding: 20px !important;
    }}
    .meal-item {{
        background-color: #FFF0F5;
        border-left: 4px solid #FFB7B2;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .meal-name {{font-weight: 700; color: #5D4037;}}
    .meal-cal {{font-weight: 700; color: #FFB7B2;}}
</style>
""", unsafe_allow_html=True)

# --- JS SNIPER UNTUK WATERMARK STREAMLIT CLOUD ---
js_sniper = """
<img src="x" onerror="
    setInterval(function() {
        var divs = window.parent.document.querySelectorAll('div');
        for (var i = 0; i < divs.length; i++) {
            var text = divs[i].innerText || '';
            if ((text.includes('Hosted with Streamlit') || text.includes('Created by')) && text.length < 50) {
                divs[i].style.display = 'none';
            }
        }
        var footers = window.parent.document.querySelectorAll('footer');
        for(var i=0; i<footers.length; i++) footers[i].style.display = 'none';
    }, 500);
" style="display:none;">
"""
st.markdown(js_sniper, unsafe_allow_html=True)

# --- HEADER APP ---

logo_base64 = get_base64_of_bin_file("kalorya_logo.png.jpeg")

if st.session_state.gender == 'Laki-laki':
    sapaan_teks = f"Halo, Bro {st.session_state.logged_in_user.title()}! 💪"
else:
    sapaan_teks = f"Hai cantik, {st.session_state.logged_in_user.title()}! 🌸"

header_html = f"""
<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: nowrap;">
    <img src="data:image/jpeg;base64,{logo_base64}" style="width: clamp(45px, 15vw, 65px); height: auto; border-radius: 12px; box-shadow: 0 4px 10px rgba(255,183,178,0.3); flex-shrink: 0;">
    <div>
        <h1 style="margin: 0; padding: 0; font-size: clamp(1.4rem, 6vw, 2.2rem); color: #5D4037; line-height: 1.2;">{sapaan_teks}</h1>
        <p style="margin: 0; padding: 0; color: #8D6E63; font-weight: 600; font-size: clamp(0.85rem, 3.5vw, 1rem);">Kalorya - Tetep konsisten, ya!</p>
    </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)
st.write("")
tab1, tab2, tab3 = st.tabs(["🏠 Beranda Hari Ini", "📅 Rekap & Riwayat", "📈 Pantau Berat Badan"])
with tab1:
    # --- WIDGET LINGKARAN KALORI ---
    consumed = st.session_state.consumed_calories
    karbo = st.session_state.consumed_carbs
    protein = st.session_state.consumed_protein
    lemak = st.session_state.consumed_fat
    target = st.session_state.target_calories
    progress = min((consumed / target) * 100, 100) if target > 0 else 100
    dash_offset = 439.8 - (439.8 * progress / 100)

    ring_html = f"""<div class="cute-card">
    <h3 style="text-align: center; color: #FFB7B2; margin-top: 0; margin-bottom: 20px; font-weight: 700;">Kalori kamu hari ini</h3>
    <div style="position: relative; width: 180px; height: 180px; margin: 0 auto 20px;">
    <svg width="180" height="180" viewBox="0 0 160 160" style="transform: rotate(-90deg);">
    <circle cx="80" cy="80" r="70" fill="none" stroke="#FFE2E2" stroke-width="14" />
    <circle cx="80" cy="80" r="70" fill="none" stroke="#FFB7B2" stroke-width="14" stroke-dasharray="439.8" stroke-dashoffset="{dash_offset}" stroke-linecap="round" />
    </svg>
    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
    <div style="font-size: 2.2rem; font-weight: 700; color: #5D4037;">{consumed}</div>
    <div style="font-size: 1rem; color: #8D6E63; font-weight: 500;">/ {target} kcal</div>
    </div>
    </div>
    <div style="display: flex; justify-content: space-around; margin-top: 10px;">
    <div style="text-align: center;">
    <div style="font-size: 0.85rem; color: #8D6E63; font-weight: 600; margin-bottom: 8px;">Karbo</div>
    <div style="font-weight: 700; color: #4DD0E1; font-size: 1.1rem;">{karbo}g</div>
    </div>
    <div style="text-align: center;">
    <div style="font-size: 0.85rem; color: #8D6E63; font-weight: 600; margin-bottom: 8px;">Protein</div>
    <div style="font-weight: 700; color: #FFB7B2; font-size: 1.1rem;">{protein}g</div>
    </div>
    <div style="text-align: center;">
    <div style="font-size: 0.85rem; color: #8D6E63; font-weight: 600; margin-bottom: 8px;">Lemak</div>
    <div style="font-weight: 700; color: #81C784; font-size: 1.1rem;">{lemak}g</div>
    </div>
    </div>
    </div>"""
    st.markdown(ring_html, unsafe_allow_html=True)

    # --- JURNAL MAKANAN HARI INI ---
    st.markdown("<h3 style='color:#5D4037; font-weight:700; margin-top:20px; margin-bottom:15px;'>Jurnal Makananmu 📖</h3>", unsafe_allow_html=True)
    if len(st.session_state.meal_history) == 0:
        st.markdown("<p style='color:#8D6E63; font-style:italic;'>Belum ada makanan yang dicatat hari ini. Yuk scan makan siangmu!</p>", unsafe_allow_html=True)
    else:
        for idx, meal in enumerate(st.session_state.meal_history):
            jam_teks = meal.get('time', 'Waktu tak dicatat')
            
            # Kolom info dan kolom hapus
            col_info, col_del = st.columns([7, 1])
            with col_info:
                st.markdown(f"""
                <div class="meal-item" style="margin-bottom: 0;">
                    <div>
                        <div style="font-size: 0.8rem; color: #8D6E63; margin-bottom: 4px;">🕰️ {jam_teks}</div>
                        <div class="meal-name">🍽️ {meal['name']}</div>
                    </div>
                    <div class="meal-cal">+{meal['calories']} kcal</div>
                </div>
                """, unsafe_allow_html=True)
            with col_del:
                st.write("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                if st.button("❌", key=f"del_meal_{idx}", help=f"Hapus {meal['name']}", use_container_width=True):
                    meal_to_delete = st.session_state.meal_history[idx]
                    
                    st.session_state.consumed_calories = max(0, st.session_state.consumed_calories - meal_to_delete.get("calories", 0))
                    st.session_state.consumed_carbs = max(0, st.session_state.consumed_carbs - meal_to_delete.get("carbs", 0))
                    st.session_state.consumed_protein = max(0, st.session_state.consumed_protein - meal_to_delete.get("protein", 0))
                    st.session_state.consumed_fat = max(0, st.session_state.consumed_fat - meal_to_delete.get("fat", 0))
                    
                    st.session_state.meal_history.pop(idx)
                    save_data_to_db()
                    st.success(f"Berhasil menghapus {meal_to_delete['name']}! 🗑️")
                    st.rerun()
            st.write("")

    # --- FITUR UTAMA: SCAN KAMERA & AI ---
    st.markdown("<hr style='border-top: 2px dashed #FFE2E2; margin: 30px 0;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#5D4037; text-align:center; font-weight:700;'>Scan Makananmu Di Sini! 📸</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8D6E63; margin-top:-10px; margin-bottom:20px;'>Klik tombol pink di bawah untuk memfoto atau upload gambar makananmu.</p>", unsafe_allow_html=True)

    if not api_key_configured:
        st.error("⚠️ Menunggu Kunci Rahasia... Minta panduan dari developer.")

    if st.session_state.get('scan_success_message'):
        st.success(st.session_state.scan_success_message)
        st.session_state.scan_success_message = ""

    uploaded_file = st.file_uploader("Scan Kalori!", type=["jpg", "png", "jpeg", "webp"], label_visibility="collapsed", key=st.session_state.uploader_key)

    if uploaded_file is not None and api_key_configured:
        st.image(uploaded_file, caption="Makanan yang sedang diproses...", use_container_width=True)
        file_id = uploaded_file.file_id
        if file_id not in st.session_state.processed_files:
            col_tgl, col_jam = st.columns(2)
            with col_tgl:
                tanggal_makan = st.date_input("Tanggal makan 📅", value=datetime.now(WIB).date())
            with col_jam:
                waktu_makan = st.time_input("Jam makan 🕰️ (Opsional)", value=None)
            
            detail_makanan = st.text_input(
                "Detail makanan / petunjuk untuk AI 📝 (Opsional):", 
                placeholder="Misal: Udang tepung (bukan ayam goreng), nasi sop bakso"
            )
            
            if st.button("Hitung Kalorinya Sekarang! ✨", use_container_width=True):
                with st.spinner("✨ AI Kalorya sedang menebak kalori makananmu..."):
                    try:
                        image = Image.open(uploaded_file)
                    
                        sapaan_ai = "teman bro nge-gym yang asik dan suportif" if st.session_state.gender == "Laki-laki" else "wanita gen z yang ramah, manis, dan suportif"
                    
                        petunjuk_tambahan = ""
                        if detail_makanan.strip():
                            petunjuk_tambahan = f"\nPengguna memberikan petunjuk tambahan tentang makanan ini: '{detail_makanan.strip()}'. Gunakan petunjuk ini untuk membantu mengidentifikasi makanan dengan tepat."

                        prompt = f"""
                        Kamu adalah asisten diet {sapaan_ai} bernama Kalorya.
                        Tolong tebak makanan apa yang ada di gambar ini dan berikan estimasi nutrisinya.{petunjuk_tambahan}
                        SANGAT PENTING: Untuk nilai angka, kamu WAJIB menjawab dengan satu ANGKA BULAT saja. Dilarang keras menggunakan rentang (seperti 10-20), dilarang menggunakan kurang dari/lebih dari, dilarang koma/desimal. Jika ragu, tebak satu angka pasti!
                        Format balasan harus persis seperti ini (hanya isi kurung siku dengan format yang diminta):
                        **Nama Makanan:** [Tebakan Nama Makanan Singkat]
                        **Estimasi Kalori:** [Angka Bulat] kcal
                        **Karbohidrat:** [Angka Bulat] g
                        **Protein:** [Angka Bulat] g
                        **Lemak:** [Angka Bulat] g
                        Berikan 1 or 2 kalimat suportif khas gen z di bagian paling bawah untuk menyemangati dia!
                        """
                        # Coba beberapa model secara bergantian jika ada yang terkena limit kuota 429
                        models_to_try = ['gemini-flash-latest', 'gemini-flash-lite-latest']
                        teks_hasil = None
                        last_error = None
                        
                        for model_name in models_to_try:
                            try:
                                model = genai.GenerativeModel(model_name)
                                response = model.generate_content([prompt, image], generation_config={"temperature": 0.0})
                                teks_hasil = response.text
                                break
                            except Exception as ex:
                                last_error = ex
                                error_msg = str(ex)
                                if "429" in error_msg or "quota" in error_msg.lower():
                                    continue
                                else:
                                    raise ex
                                    
                        if teks_hasil is None:
                            raise last_error
                    
                        nama_match = re.search(r'\*\*Nama Makanan:\*\*\s*(.+)', teks_hasil)
                        kalori_match = re.search(r'\*\*Estimasi Kalori:\*\*\s*(\d+)', teks_hasil)
                        karbo_match = re.search(r'\*\*Karbohidrat:\*\*\s*(\d+)', teks_hasil)
                        protein_match = re.search(r'\*\*Protein:\*\*\s*(\d+)', teks_hasil)
                        lemak_match = re.search(r'\*\*Lemak:\*\*\s*(\d+)', teks_hasil)
                    
                        kalori_baru = 0
                        karbo_baru = 0
                        protein_baru = 0
                        lemak_baru = 0
                        
                        if kalori_match: 
                            kalori_baru = int(kalori_match.group(1))
                        if karbo_match: 
                            karbo_baru = int(karbo_match.group(1))
                        if protein_match: 
                            protein_baru = int(protein_match.group(1))
                        if lemak_match: 
                            lemak_baru = int(lemak_match.group(1))
                    
                        jam_str = waktu_makan.strftime('%H:%M') if waktu_makan else "Waktu tak dicatat"
                        nama_makanan_baru = nama_match.group(1).strip() if nama_match else "Makanan Lezat"
                        
                        # Tentukan tanggal tujuan log
                        tgl_str = tanggal_makan.strftime("%Y-%m-%d")
                        today_str = get_today_str()
                        
                        new_meal = {
                            "name": nama_makanan_baru, 
                            "calories": kalori_baru, 
                            "carbs": karbo_baru,
                            "protein": protein_baru,
                            "fat": lemak_baru,
                            "time": jam_str
                        }
                        
                        if tgl_str == today_str:
                            st.session_state.consumed_calories += kalori_baru
                            st.session_state.consumed_carbs += karbo_baru
                            st.session_state.consumed_protein += protein_baru
                            st.session_state.consumed_fat += lemak_baru
                            st.session_state.meal_history.append(new_meal)
                            st.session_state.scan_success_message = f"Berhasil mencatat {nama_makanan_baru} (+{kalori_baru} kcal) ke Jurnal hari ini! 🍽️"
                        else:
                            if 'daily_records' not in st.session_state:
                                st.session_state.daily_records = {}
                            if tgl_str not in st.session_state.daily_records:
                                st.session_state.daily_records[tgl_str] = {
                                    'calories': 0,
                                    'carbs': 0,
                                    'protein': 0,
                                    'fat': 0,
                                    'meals': []
                                }
                            
                            st.session_state.daily_records[tgl_str]['calories'] += kalori_baru
                            st.session_state.daily_records[tgl_str]['carbs'] = st.session_state.daily_records[tgl_str].get('carbs', 0) + karbo_baru
                            st.session_state.daily_records[tgl_str]['protein'] = st.session_state.daily_records[tgl_str].get('protein', 0) + protein_baru
                            st.session_state.daily_records[tgl_str]['fat'] = st.session_state.daily_records[tgl_str].get('fat', 0) + lemak_baru
                            st.session_state.daily_records[tgl_str]['meals'].append(new_meal)
                            
                            try:
                                tgl_dt = datetime.strptime(tgl_str, "%Y-%m-%d")
                                tgl_cantik = tgl_dt.strftime("%d %b %Y")
                            except Exception:
                                tgl_cantik = tgl_str
                            st.session_state.scan_success_message = f"Berhasil mencatat {nama_makanan_baru} (+{kalori_baru} kcal) ke riwayat tanggal {tgl_cantik}! 📅"
                    
                        st.session_state.processed_files.add(file_id)
                        st.session_state.last_response = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', teks_hasil)
                    
                        save_data_to_db()
                        st.rerun()
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "quota" in error_msg.lower():
                            st.error("⏳ Oops! Semua model AI pendukung sedang terkena batas kuota gratis harian (limit 20 request/hari per model). Silakan tunggu beberapa saat atau coba besok ya cantik! 🌸")
                            with st.expander("Detail Teknis Error (untuk Developer)"):
                                st.write(error_msg)
                        else:
                            st.error(f"Duh, mataku (AI) agak blur. Detail error: {e}")
        else:
            if st.session_state.last_response:
                st.markdown(f"""
                <div class="cute-card" style="background-color: #FFF0F5; border: 2px solid #FFB7B2;">
                    <h4 style="color: #FFB7B2; margin-top:0;">✨ Hasil Scan Kalorya:</h4>
                    <div style="color: #5D4037; font-size: 1.05rem; line-height: 1.6;">{st.session_state.last_response.replace(chr(10), '<br>')}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    if st.button("Restart Hitungan Hari Ini 🔄", use_container_width=True):
        st.session_state.consumed_calories = 0
        st.session_state.consumed_carbs = 0
        st.session_state.consumed_protein = 0
        st.session_state.consumed_fat = 0
        st.session_state.processed_files = set()
        st.session_state.last_response = ""
        st.session_state.meal_history = []
        st.session_state.uploader_key = str(uuid.uuid4())
        st.session_state.scan_success_message = ""
        save_data_to_db()
        st.rerun()

    # Tombol Logout
    st.markdown("<hr style='border-top: 1px solid #FFE2E2;'>", unsafe_allow_html=True)
    if st.button("Keluar Akun (Logout)", type="secondary"):
        st.session_state.logged_in_user = None
        st.rerun()

with tab2:
    st.markdown("<h3 style='color:#5D4037; font-weight:700;'>📅 Rekap Kalori Harian</h3>", unsafe_allow_html=True)
    
    daily_records = st.session_state.get("daily_records", {})
    if not daily_records:
        st.info("Belum ada riwayat makanan di hari-hari sebelumnya.")
    else:
        import pandas as pd
        df_rekapan = pd.DataFrame([{"Tanggal": k, "Kalori": v["calories"]} for k, v in daily_records.items()])
        df_rekapan["Tanggal"] = pd.to_datetime(df_rekapan["Tanggal"])
        df_rekapan = df_rekapan.sort_values("Tanggal")
        st.bar_chart(df_rekapan.set_index("Tanggal"))
        
        st.markdown("<hr style='border-top: 2px dashed #FFE2E2; margin: 30px 0;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#5D4037; font-weight:700;'>🍽️ Cek Makanan Masa Lalu</h3>", unsafe_allow_html=True)
        tanggal_pilihan = st.date_input("Pilih Tanggal:")
        tgl_str = tanggal_pilihan.strftime("%Y-%m-%d")
        if tgl_str in daily_records:
            st.success(f"Total Kalori pada {tgl_str}: **{daily_records[tgl_str]['calories']} kcal**")
            for idx, meal in enumerate(daily_records[tgl_str]["meals"]):
                jam_teks = meal.get("time", "Waktu tak dicatat")
                col_info, col_del = st.columns([7, 1])
                with col_info:
                    st.markdown(f"""
                    <div class="meal-item" style="margin-bottom: 0;">
                        <div>
                            <div style="font-size: 0.8rem; color: #8D6E63; margin-bottom: 4px;">🕰️ {jam_teks}</div>
                            <div class="meal-name">🍽️ {meal['name']}</div>
                        </div>
                        <div class="meal-cal">+{meal['calories']} kcal</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    st.write("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                    if st.button("❌", key=f"del_past_meal_{idx}_{tgl_str}", help=f"Hapus {meal['name']}", use_container_width=True):
                        meal_to_delete = daily_records[tgl_str]["meals"][idx]
                        
                        # Kurangi total harian untuk tanggal tersebut
                        daily_records[tgl_str]["calories"] = max(0, daily_records[tgl_str]["calories"] - meal_to_delete.get("calories", 0))
                        daily_records[tgl_str]["carbs"] = max(0, daily_records[tgl_str].get("carbs", 0) - meal_to_delete.get("carbs", 0))
                        daily_records[tgl_str]["protein"] = max(0, daily_records[tgl_str].get("protein", 0) - meal_to_delete.get("protein", 0))
                        daily_records[tgl_str]["fat"] = max(0, daily_records[tgl_str].get("fat", 0) - meal_to_delete.get("fat", 0))
                        
                        # Hapus item dari list
                        daily_records[tgl_str]["meals"].pop(idx)
                        
                        # Sinkronisasi dengan today's session state jika yang dihapus adalah makanan hari ini
                        today_str = get_today_str()
                        if tgl_str == today_str:
                            st.session_state.consumed_calories = daily_records[tgl_str]["calories"]
                            st.session_state.consumed_carbs = daily_records[tgl_str]["carbs"]
                            st.session_state.consumed_protein = daily_records[tgl_str]["protein"]
                            st.session_state.consumed_fat = daily_records[tgl_str]["fat"]
                            st.session_state.meal_history = daily_records[tgl_str]["meals"]
                            
                        st.session_state.daily_records = daily_records
                        save_data_to_db()
                        st.success(f"Berhasil menghapus {meal_to_delete['name']} dari riwayat! 🗑️")
                        st.rerun()
                st.write("")
        else:
            st.warning("Tidak ada catatan makanan pada tanggal ini.")

with tab3:
    st.markdown("<h3 style='color:#5D4037; font-weight:700;'>📈 Pantau Berat Badan</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8D6E63;'>Pantau target berat badan Anda dan pacar Anda secara berkala di sini. ✨</p>", unsafe_allow_html=True)

    # --- WIDGET MONITORING PROGRESS BERAT BADAN ---
    bb_awal = st.session_state.bb_awal
    bb_target = st.session_state.bb_target
    bb_sekarang = st.session_state.bb
    
    total_diff = abs(bb_awal - bb_target)
    if total_diff == 0:
        progress_persen = 100.0
    else:
        if bb_target < bb_awal:  # Nurunin BB
            progress_persen = max(0.0, min(100.0, ((bb_awal - bb_sekarang) / total_diff) * 100))
        else:  # Naikin BB
            progress_persen = max(0.0, min(100.0, ((bb_sekarang - bb_awal) / total_diff) * 100))
            
    berat_hilang = bb_awal - bb_sekarang
    if bb_target < bb_awal:
        label_status = f"Turun {abs(berat_hilang):.1f} kg" if berat_hilang >= 0 else f"Naik {abs(berat_hilang):.1f} kg"
        if berat_hilang > 0:
            motivasi = f"Hebat! Defisit kalorimu berhasil memotong <b>{abs(berat_hilang):.1f} kg</b> dari target penurunan <b>{total_diff:.1f} kg</b>! 💪✨"
        else:
            motivasi = f"Semangat! Konsisten defisit kalori, hasil penurunan berat badan akan segera terlihat! 🌸"
    else:
        label_status = f"Naik {abs(berat_hilang):.1f} kg" if berat_hilang <= 0 else f"Turun {abs(berat_hilang):.1f} kg"
        if berat_hilang < 0:
            motivasi = f"Keren! Berat badanmu sudah bertambah <b>{abs(berat_hilang):.1f} kg</b> dari target bulking <b>{total_diff:.1f} kg</b>! 💪🍳"
        else:
            motivasi = f"Ayo makan bergizi dengan kalori surplus untuk meningkatkan berat badanmu! 🍎"
            
    weight_bar_html = f"""<div class="cute-card">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: nowrap; gap: 8px;">
<h3 style="margin: 0; font-size: clamp(1rem, 4.5vw, 1.25rem); color: #5D4037; font-weight: 700;">🎯 Target Berat Badan</h3>
<span style="font-size: 0.85rem; font-weight: 700; color: #FFB7B2; background: #FFE2E2; padding: 4px 10px; border-radius: 12px; white-space: nowrap;">{label_status}</span>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; color: #8D6E63; margin-bottom: 8px;">
<span>Awal: <b>{bb_awal} kg</b></span>
<span>Target: <b>{bb_target} kg</b></span>
</div>
<div style="background: #FFE2E2; height: 14px; border-radius: 7px; position: relative; margin-bottom: 24px; width: 100%;">
<div style="background: #FFB7B2; height: 100%; width: {progress_persen}%; border-radius: 7px; position: relative; transition: width 0.5s ease;">
<div style="position: absolute; right: 0; top: -24px; background: #FF9B94; color: white; font-size: 0.75rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; transform: translateX(50%); white-space: nowrap; box-shadow: 0 2px 4px rgba(255,155,148,0.3);">
{bb_sekarang} kg ({int(progress_persen)}%)
</div>
</div>
</div>
<div style="font-size: 0.85rem; color: #8D6E63; text-align: center; line-height: 1.4;">
{motivasi}
</div>
</div>"""
    st.markdown(weight_bar_html, unsafe_allow_html=True)

    # --- FORM UPDATE BERAT BADAN LANGSUNG ---
    st.markdown("<h4 style='color:#5D4037; font-weight:700; margin-top:20px; margin-bottom:10px;'>📝 Perbarui Berat Badan & Target Hari Ini</h4>", unsafe_allow_html=True)
    with st.form("update_weight_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            input_bb_awal = st.number_input("Berat Badan Awal (kg)", 30, 200, int(st.session_state.bb_awal))
        with col2:
            input_bb_sekarang = st.number_input("Berat Badan Sekarang (kg)", 30, 200, int(st.session_state.bb))
        with col3:
            input_bb_target = st.number_input("Target Berat Badan (kg)", 30, 200, int(st.session_state.bb_target))
            
        submitted = st.form_submit_button("Simpan & Perbarui Progress 🚀", use_container_width=True)
        if submitted:
            st.session_state.bb_awal = input_bb_awal
            st.session_state.bb = input_bb_sekarang
            st.session_state.bb_target = input_bb_target
            
            # Simpan ke Weight Tracker
            today_str = get_today_str()
            st.session_state.weight_history[today_str] = input_bb_sekarang
            
            # Hitung TDEE target calories ulang dengan BB Sekarang
            if st.session_state.gender == "Laki-laki":
                bmr = (10 * input_bb_sekarang) + (6.25 * st.session_state.tb) - (5 * st.session_state.umur) + 5
            else:
                bmr = (10 * input_bb_sekarang) + (6.25 * st.session_state.tb) - (5 * st.session_state.umur) - 161
            rekomendasi_tdee = int(bmr * 1.2)
            
            diet_plan = st.session_state.get('diet_plan', "Turunkan Berat Badan (Normal: -500 kcal/hari)")
            if "Normal: -500" in diet_plan:
                target_rekomendasi = rekomendasi_tdee - 500
            elif "Santai: -250" in diet_plan:
                target_rekomendasi = rekomendasi_tdee - 250
            elif "Agresif: -750" in diet_plan:
                target_rekomendasi = rekomendasi_tdee - 750
            elif "Bulking Santai: +250" in diet_plan:
                target_rekomendasi = rekomendasi_tdee + 250
            elif "Bulking Normal: +500" in diet_plan:
                target_rekomendasi = rekomendasi_tdee + 500
            else:
                target_rekomendasi = rekomendasi_tdee
                
            min_safe_cal = 1200 if st.session_state.gender == "Perempuan" else 1500
            if target_rekomendasi < min_safe_cal and "Turunkan" in diet_plan:
                target_rekomendasi = min_safe_cal
                
            st.session_state.target_calories = int(target_rekomendasi)
            
            save_data_to_db()
            st.success("Progress berat badan berhasil diperbarui! 🎉")
            st.rerun()

    # --- TOMBOL RESET BERAT BADAN ---
    if st.button("Reset Data & Riwayat Berat Badan 🔄", type="secondary", use_container_width=True):
        st.session_state.bb_awal = 50
        st.session_state.bb = 50
        st.session_state.bb_target = 50
        st.session_state.weight_history = {}
        save_data_to_db()
        st.success("Data berat badan dan riwayat berhasil di-reset! Silakan masukkan data baru Anda. 🔄")
        st.rerun()

    # --- WIDGET PROFIL TUBUH & TARGET CERDAS ---
    with st.expander("⚙️ Pengaturan Profil & Rencana Kalori"):
        st.markdown("Isi data profil tubuh di bawah ini untuk menghitung rekomendasi TDEE secara otomatis.")
        colA, colB = st.columns(2)
        with colA:
            input_tb = st.number_input("Tinggi Badan (cm)", 100, 250, st.session_state.tb)
            input_umur = st.number_input("Umur (tahun)", 10, 100, st.session_state.umur)
        with colB:
            input_gender = st.selectbox("Jenis Kelamin", ["Perempuan", "Laki-laki"], index=0 if st.session_state.gender == 'Perempuan' else 1)
        
        # Hitung TDEE Dasar (BMR * 1.2 untuk Sedentary)
        if input_gender == "Laki-laki":
            bmr = (10 * st.session_state.bb) + (6.25 * input_tb) - (5 * input_umur) + 5
        else:
            bmr = (10 * st.session_state.bb) + (6.25 * input_tb) - (5 * input_umur) - 161
        rekomendasi_tdee = int(bmr * 1.2)
    
        st.info(f"💡 Rekomendasi Medis (TDEE): Tubuhmu membakar sekitar **{rekomendasi_tdee} kcal** per hari (berdasarkan BB sekarang: **{st.session_state.bb} kg**).")
        
        # Pilihan Rencana Diet
        tujuan_opsi = [
            "Turunkan Berat Badan (Santai: -250 kcal/hari)",
            "Turunkan Berat Badan (Normal: -500 kcal/hari)",
            "Turunkan Berat Badan (Agresif: -750 kcal/hari)",
            "Pertahankan Berat Badan (TDEE)",
            "Naikkan Berat Badan (Bulking Santai: +250 kcal/hari)",
            "Naikkan Berat Badan (Bulking Normal: +500 kcal/hari)"
        ]
        
        if 'diet_plan' not in st.session_state:
            st.session_state.diet_plan = "Turunkan Berat Badan (Normal: -500 kcal/hari)"
            
        try:
            default_plan_idx = tujuan_opsi.index(st.session_state.diet_plan)
        except ValueError:
            default_plan_idx = 1
            
        diet_plan_pilihan = st.selectbox("Rencana Target Kalori:", tujuan_opsi, index=default_plan_idx)
        
        # Hitung penyesuaian kalori
        if "Normal: -500" in diet_plan_pilihan:
            target_rekomendasi = rekomendasi_tdee - 500
        elif "Santai: -250" in diet_plan_pilihan:
            target_rekomendasi = rekomendasi_tdee - 250
        elif "Agresif: -750" in diet_plan_pilihan:
            target_rekomendasi = rekomendasi_tdee - 750
        elif "Bulking Santai: +250" in diet_plan_pilihan:
            target_rekomendasi = rekomendasi_tdee + 250
        elif "Bulking Normal: +500" in diet_plan_pilihan:
            target_rekomendasi = rekomendasi_tdee + 500
        else:
            target_rekomendasi = rekomendasi_tdee
            
        # Batasi batas kalori aman (wanita min 1200 kcal, pria min 1500 kcal)
        min_safe_cal = 1200 if input_gender == "Perempuan" else 1500
        if target_rekomendasi < min_safe_cal and "Turunkan" in diet_plan_pilihan:
            st.warning(f"⚠️ Target kalori ({target_rekomendasi} kcal) berada di bawah batas kalori aman harian ({min_safe_cal} kcal). Target kalori secara otomatis disesuaikan agar tetap aman bagi kesehatan.")
            target_rekomendasi = min_safe_cal

        target_pilihan = st.number_input("Target Kalori Harianmu (Bisa diedit manual):", 500, 5000, value=int(target_rekomendasi), step=50)
    
        if st.button("Simpan Profil & Rencana Kalori"):
            st.session_state.tb = input_tb
            st.session_state.umur = input_umur
            st.session_state.gender = input_gender
            st.session_state.diet_plan = diet_plan_pilihan
            st.session_state.target_calories = target_pilihan
        
            save_data_to_db()
            st.success("Profil & Rencana Kalori berhasil diperbarui! 🔒")
            st.rerun()

    # --- RIWAYAT BERAT BADAN (WEIGHT HISTORY LIST) ---
    if st.session_state.weight_history:
        st.markdown("<h3 style='color:#5D4037; font-weight:700; margin-top:30px; margin-bottom:15px;'>📅 Catatan Berat Badan</h3>", unsafe_allow_html=True)
        
        # Urutkan riwayat berdasarkan tanggal (ascending) untuk menghitung selisihnya
        sorted_history = sorted(st.session_state.weight_history.items(), key=lambda x: x[0])
        
        history_items = []
        for idx, (tgl, berat) in enumerate(sorted_history):
            if idx == 0:
                perubahan = "Awal"
                color = "#8D6E63"  # Cokelat default
            else:
                diff = berat - sorted_history[idx-1][1]
                if diff < 0:
                    perubahan = f"⬇️ -{abs(diff):.1f} kg"
                    color = "#81C784"  # Hijau (penurunan berat)
                elif diff > 0:
                    perubahan = f"⬆️ +{abs(diff):.1f} kg"
                    color = "#E57373"  # Merah (kenaikan berat)
                else:
                    perubahan = "Tetap"
                    color = "#8D6E63"
            
            try:
                tgl_dt = datetime.strptime(tgl, "%Y-%m-%d")
                tgl_cantik = tgl_dt.strftime("%d %b %Y")
            except Exception:
                tgl_cantik = tgl
                
            history_items.append({
                "tanggal": tgl_cantik,
                "berat": f"{berat} kg",
                "perubahan": perubahan,
                "color": color
            })
            
        # Balik urutan agar data terbaru berada paling atas
        history_items.reverse()
        
        for item in history_items:
            st.markdown(f"""
            <div class="meal-item" style="border-left: 4px solid {item['color']}; padding: 12px 16px; margin-bottom: 8px;">
                <div style="font-weight: 700; color: #5D4037;">🗓️ {item['tanggal']}</div>
                <div style="font-weight: 700; color: #5D4037; display: flex; gap: 12px; align-items: center;">
                    <span>⚖️ {item['berat']}</span>
                    <span style="color: {item['color']}; font-size: 0.95rem; font-weight: 700;">({item['perubahan']})</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
