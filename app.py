import streamlit as st
import google.generativeai as genai
from PIL import Image
import re
import uuid
import json
from datetime import datetime

# Impor Firebase
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Kalorya", page_icon="🌸", layout="centered")

# --- KONFIGURASI FIREBASE ---
db = None
firebase_configured = False
if not firebase_admin._apps:
    try:
        if "FIREBASE_KEY" in st.secrets:
            key_dict = json.loads(st.secrets["FIREBASE_KEY"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            firebase_configured = True
    except Exception as e:
        st.error(f"⚠️ Menunggu Perbaikan Kunci Firebase Anda...")
else:
    try:
        db = firestore.client()
        firebase_configured = True
    except Exception:
        pass

# --- FUNGSI DATABASE ---
def load_data_from_db():
    if not firebase_configured or db is None:
        return
    try:
        doc_ref = db.collection('kalorya').document('user_data')
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            st.session_state.consumed_calories = data.get('consumed_calories', 0)
            st.session_state.consumed_carbs = data.get('consumed_carbs', 0)
            st.session_state.consumed_protein = data.get('consumed_protein', 0)
            st.session_state.consumed_fat = data.get('consumed_fat', 0)
            st.session_state.meal_history = data.get('meal_history', [])
            st.session_state.target_calories = data.get('target_calories', 1800)
    except Exception as e:
        print(f"Error loading from db: {e}")

def save_data_to_db():
    if not firebase_configured or db is None:
        return
    try:
        doc_ref = db.collection('kalorya').document('user_data')
        doc_ref.set({
            'consumed_calories': st.session_state.consumed_calories,
            'consumed_carbs': st.session_state.consumed_carbs,
            'consumed_protein': st.session_state.consumed_protein,
            'consumed_fat': st.session_state.consumed_fat,
            'meal_history': st.session_state.meal_history,
            'target_calories': st.session_state.target_calories,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error saving to db: {e}")

# --- INISIALISASI STATE (MEMORI APLIKASI) ---
if 'consumed_calories' not in st.session_state:
    st.session_state.consumed_calories = 0
if 'consumed_carbs' not in st.session_state:
    st.session_state.consumed_carbs = 0
if 'consumed_protein' not in st.session_state:
    st.session_state.consumed_protein = 0
if 'consumed_fat' not in st.session_state:
    st.session_state.consumed_fat = 0
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'last_response' not in st.session_state:
    st.session_state.last_response = ""
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = str(uuid.uuid4())
if 'meal_history' not in st.session_state:
    st.session_state.meal_history = [] 
if 'target_calories' not in st.session_state:
    st.session_state.target_calories = 1800

# Muat data dari Firebase SAAT PERTAMA KALI dibuka (Autoload)
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = True
    load_data_from_db()

# --- KONFIGURASI GEMINI AI ---
api_key_configured = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        api_key_configured = True
except Exception:
    pass

# --- INJEKSI CSS (UI SUPER CUTE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif !important;
        background-color: #FEF9F8 !important;
        color: #5D4037 !important;
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background-color: #FEF9F8;}
    
    .cute-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(255, 183, 178, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.8);
        margin-bottom: 24px;
    }
    
    [data-testid="stFileUploadDropzone"] {
        background-color: #FFB7B2 !important;
        border: 2px dashed #FFF !important;
        border-radius: 24px !important;
        padding: 20px !important;
    }
    [data-testid="stFileUploadDropzone"] div, [data-testid="stFileUploadDropzone"] span {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    
    .stButton>button {
        background-color: #FFF0F5 !important;
        color: #FFB7B2 !important;
        border: 2px solid #FFB7B2 !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #FFB7B2 !important;
        color: white !important;
        transform: scale(1.02);
    }
    
    .meal-item {
        background-color: #FFF0F5;
        border-left: 4px solid #FFB7B2;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .meal-name {
        font-weight: 700;
        color: #5D4037;
        font-size: 1rem;
    }
    .meal-cal {
        font-weight: 700;
        color: #FFB7B2;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER APP ---
col1, col2 = st.columns([1, 4])
with col1:
    st.image("kalorya_logo.png.jpeg", width=65)
with col2:
    st.markdown("<h1 style='margin-bottom:0; padding-bottom:0; font-size:2.2rem; color:#5D4037;'>Hai cantik! 🌸</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8D6E63; font-weight:600; margin-top:0;'>Kalorya - Tetep konsisten, ya!</p>", unsafe_allow_html=True)

st.write("") 

# --- PENGATURAN TARGET KALORI ---
with st.expander("⚙️ Atur Target Kalori Harian"):
    st.session_state.target_calories = int(st.number_input(
        "Berapa batas kalori kamu hari ini?", 
        min_value=500, max_value=5000, 
        value=st.session_state.target_calories, 
        step=50,
        on_change=save_data_to_db
    ))

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
    for index, meal in enumerate(st.session_state.meal_history):
        jam_teks = meal.get('time', 'Waktu tak dicatat')
        st.markdown(f"""
        <div class="meal-item">
            <div>
                <div style="font-size: 0.8rem; color: #8D6E63; margin-bottom: 4px;">🕰️ {jam_teks}</div>
                <div class="meal-name">🍽️ {meal['name']}</div>
            </div>
            <div class="meal-cal">+{meal['calories']} kcal</div>
        </div>
        """, unsafe_allow_html=True)

# --- FITUR UTAMA: SCAN KAMERA & AI ---
st.markdown("<hr style='border-top: 2px dashed #FFE2E2; margin: 30px 0;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#5D4037; text-align:center; font-weight:700;'>Scan Makananmu Di Sini! 📸</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8D6E63; margin-top:-10px; margin-bottom:20px;'>Klik tombol pink di bawah untuk memfoto atau upload gambar makananmu.</p>", unsafe_allow_html=True)

if not api_key_configured:
    st.error("⚠️ Menunggu Kunci Rahasia... Minta panduan dari developer untuk memasukkan API Key di Streamlit Secrets.")

if not firebase_configured:
    st.warning("🗄️ Database belum terhubung dengan sempurna. Data Anda hari ini mungkin belum tersimpan permanen.")

uploaded_file = st.file_uploader("Scan Kalori!", type=["jpg", "png", "jpeg", "webp"], label_visibility="collapsed", key=st.session_state.uploader_key)

if uploaded_file is not None and api_key_configured:
    st.image(uploaded_file, caption="Makanan yang sedang diproses...", use_container_width=True)
    
    file_id = uploaded_file.file_id
    
    if file_id not in st.session_state.processed_files:
        
        # Tambahkan Input Jam Makan
        waktu_makan = st.time_input("Jam berapa kamu makan ini? 🕰️ (Opsional)", value=None)
        
        # Tambahkan tombol Hitung agar AI tidak langsung berjalan otomatis
        if st.button("Hitung Kalorinya Sekarang! ✨", use_container_width=True):
            with st.spinner("✨ AI Kalorya sedang menebak kalori makananmu..."):
                try:
                    image = Image.open(uploaded_file)
                    prompt = """
                    Kamu adalah asisten diet wanita gen z yang ramah, manis, dan suportif bernama Kalorya.
                    Tolong tebak makanan apa yang ada di gambar ini dan berikan estimasi nutrisinya.
                    
                    SANGAT PENTING: Untuk nilai angka, kamu WAJIB menjawab dengan satu ANGKA BULAT saja. Dilarang keras menggunakan rentang (seperti 10-20), dilarang menggunakan kurang dari/lebih dari, dilarang koma/desimal. Jika ragu, tebak satu angka pasti!
                    
                    Format balasan harus persis seperti ini (hanya isi kurung siku dengan format yang diminta):
                    **Nama Makanan:** [Tebakan Nama Makanan Singkat]
                    **Estimasi Kalori:** [Angka Bulat] kcal
                    **Karbohidrat:** [Angka Bulat] g
                    **Protein:** [Angka Bulat] g
                    **Lemak:** [Angka Bulat] g
                    
                    Berikan 1 atau 2 kalimat suportif dan lucu khas gen z di bagian paling bawah untuk menyemangati dia!
                    """
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content([prompt, image])
                    teks_hasil = response.text
                    
                    # Ekstraksi angka & teks menggunakan Regex
                    nama_match = re.search(r'\*\*Nama Makanan:\*\*\s*(.+)', teks_hasil)
                    kalori_match = re.search(r'\*\*Estimasi Kalori:\*\*\s*(\d+)', teks_hasil)
                    karbo_match = re.search(r'\*\*Karbohidrat:\*\*\s*(\d+)', teks_hasil)
                    protein_match = re.search(r'\*\*Protein:\*\*\s*(\d+)', teks_hasil)
                    lemak_match = re.search(r'\*\*Lemak:\*\*\s*(\d+)', teks_hasil)
                    
                    # Update Angka Kalori dkk
                    kalori_baru = 0
                    if kalori_match: 
                        kalori_baru = int(kalori_match.group(1))
                        st.session_state.consumed_calories += kalori_baru
                    if karbo_match: st.session_state.consumed_carbs += int(karbo_match.group(1))
                    if protein_match: st.session_state.consumed_protein += int(protein_match.group(1))
                    if lemak_match: st.session_state.consumed_fat += int(lemak_match.group(1))
                    
                    # Format Waktu
                    jam_str = waktu_makan.strftime('%H:%M') if waktu_makan else "Waktu tak dicatat"
                    
                    # Tambahkan ke Jurnal Riwayat Makanan
                    nama_makanan_baru = "Makanan Lezat"
                    if nama_match:
                        nama_makanan_baru = nama_match.group(1).strip()
                    
                    st.session_state.meal_history.append({
                        "name": nama_makanan_baru,
                        "calories": kalori_baru,
                        "time": jam_str
                    })
                    
                    # Tandai foto ini sudah diproses
                    st.session_state.processed_files.add(file_id)
                    
                    # Format tebal (bold) untuk ditampilkan dan simpan riwayatnya
                    teks_hasil_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', teks_hasil)
                    st.session_state.last_response = teks_hasil_html
                    
                    # Lakukan AUTOSAVE ke Firebase sebelum layar direfresh!
                    save_data_to_db()
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Duh, mataku (AI) agak blur. Ada error nih: {e}")
    else:
        if st.session_state.last_response:
            st.markdown(f"""
            <div class="cute-card" style="background-color: #FFF0F5; border: 2px solid #FFB7B2;">
                <h4 style="color: #FFB7B2; margin-top:0;">✨ Hasil Scan Kalorya:</h4>
                <div style="color: #5D4037; font-size: 1.05rem; line-height: 1.6;">
                    {st.session_state.last_response.replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# --- TOMBOL RESTART ---
if st.button("Restart Hitungan Hari Ini 🔄", use_container_width=True):
    st.session_state.consumed_calories = 0
    st.session_state.consumed_carbs = 0
    st.session_state.consumed_protein = 0
    st.session_state.consumed_fat = 0
    st.session_state.processed_files = set()
    st.session_state.last_response = ""
    st.session_state.meal_history = []
    st.session_state.uploader_key = str(uuid.uuid4())
    
    # Kosongkan juga isi database di Firebase
    save_data_to_db()
    
    st.rerun()
