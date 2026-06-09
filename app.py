import streamlit as st
import google.generativeai as genai
from PIL import Image
import re
import uuid
import json
from datetime import datetime
import pandas as pd

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
        st.error("⚠️ Menunggu Perbaikan Kunci Firebase Anda...")
else:
    try:
        db = firestore.client()
        firebase_configured = True
    except Exception:
        pass

# --- STATE LOGIN (MULTI-USER) ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- FUNGSI DATABASE ---
def load_data_from_db():
    if not firebase_configured or db is None or not st.session_state.logged_in_user:
        return
    try:
        username = st.session_state.logged_in_user.lower().strip()
        doc_ref = db.collection('kalorya_users').document(username)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            st.session_state.consumed_calories = data.get('consumed_calories', 0)
            st.session_state.consumed_carbs = data.get('consumed_carbs', 0)
            st.session_state.consumed_protein = data.get('consumed_protein', 0)
            st.session_state.consumed_fat = data.get('consumed_fat', 0)
            st.session_state.meal_history = data.get('meal_history', [])
            st.session_state.target_calories = data.get('target_calories', 1800)
            
            # Profil Tubuh & Tracker
            st.session_state.bb = data.get('bb', 50)
            st.session_state.tb = data.get('tb', 160)
            st.session_state.umur = data.get('umur', 20)
            st.session_state.gender = data.get('gender', 'Perempuan')
            st.session_state.weight_history = data.get('weight_history', {})
    except Exception as e:
        print(f"Error loading from db: {e}")

def save_data_to_db():
    if not firebase_configured or db is None or not st.session_state.logged_in_user:
        return
    try:
        username = st.session_state.logged_in_user.lower().strip()
        doc_ref = db.collection('kalorya_users').document(username)
        doc_ref.set({
            'consumed_calories': st.session_state.consumed_calories,
            'consumed_carbs': st.session_state.consumed_carbs,
            'consumed_protein': st.session_state.consumed_protein,
            'consumed_fat': st.session_state.consumed_fat,
            'meal_history': st.session_state.meal_history,
            'target_calories': st.session_state.target_calories,
            'bb': st.session_state.get('bb', 50),
            'tb': st.session_state.get('tb', 160),
            'umur': st.session_state.get('umur', 20),
            'gender': st.session_state.get('gender', 'Perempuan'),
            'weight_history': st.session_state.get('weight_history', {}),
            'last_updated': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error saving to db: {e}")

# --- HALAMAN LOGIN ---
if st.session_state.logged_in_user is None:
    st.markdown("<h1 style='text-align:center; color:#FFB7B2; font-family:Quicksand;'>Selamat Datang di Kalorya! 🌸</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8D6E63;'>Silakan masuk dengan namamu agar data jurnal dan berat badanmu tidak bercampur dengan orang lain.</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        username_input = st.text_input("Siapa namamu?", placeholder="Misal: Sarah")
        submit = st.form_submit_button("Masuk 🚀", use_container_width=True)
        
        if submit and username_input:
            st.session_state.logged_in_user = username_input
            # Reset state default
            st.session_state.consumed_calories = 0
            st.session_state.consumed_carbs = 0
            st.session_state.consumed_protein = 0
            st.session_state.consumed_fat = 0
            st.session_state.processed_files = set()
            st.session_state.last_response = ""
            st.session_state.uploader_key = str(uuid.uuid4())
            st.session_state.meal_history = [] 
            st.session_state.target_calories = 1800
            st.session_state.weight_history = {}
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
if 'target_calories' not in st.session_state: st.session_state.target_calories = 1800
if 'bb' not in st.session_state: st.session_state.bb = 50
if 'tb' not in st.session_state: st.session_state.tb = 160
if 'umur' not in st.session_state: st.session_state.umur = 20
if 'gender' not in st.session_state: st.session_state.gender = 'Perempuan'
if 'weight_history' not in st.session_state: st.session_state.weight_history = {}

# --- KONFIGURASI GEMINI AI ---
api_key_configured = False
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        api_key_configured = True
except Exception:
    pass

# --- INJEKSI CSS ---
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
    .meal-name {font-weight: 700; color: #5D4037;}
    .meal-cal {font-weight: 700; color: #FFB7B2;}
</style>
""", unsafe_allow_html=True)

# --- HEADER APP ---
col1, col2 = st.columns([1, 4])
with col1:
    st.image("kalorya_logo.png.jpeg", width=65)
with col2:
    st.markdown(f"<h1 style='margin-bottom:0; padding-bottom:0; font-size:2.2rem; color:#5D4037;'>Hai cantik, {st.session_state.logged_in_user.title()}! 🌸</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8D6E63; font-weight:600; margin-top:0;'>Kalorya - Tetep konsisten, ya!</p>", unsafe_allow_html=True)

st.write("") 

# --- WIDGET PROFIL TUBUH ---
with st.expander("👤 Profil Tubuh & Target Cerdas"):
    st.markdown("Isi data di bawah ini agar Kalorya bisa menghitung target kalorimu secara presisi sesuai rumus medis (Mifflin-St Jeor).")
    colA, colB = st.columns(2)
    with colA:
        input_bb = st.number_input("Berat Badan (kg)", 30, 200, st.session_state.bb)
        input_umur = st.number_input("Umur (tahun)", 10, 100, st.session_state.umur)
    with colB:
        input_tb = st.number_input("Tinggi Badan (cm)", 100, 250, st.session_state.tb)
        input_gender = st.selectbox("Jenis Kelamin", ["Perempuan", "Laki-laki"], index=0 if st.session_state.gender == 'Perempuan' else 1)
        
    # Hitung TDEE Dasar (BMR * 1.2 untuk Sedentary)
    if input_gender == "Laki-laki":
        bmr = (10 * input_bb) + (6.25 * input_tb) - (5 * input_umur) + 5
    else:
        bmr = (10 * input_bb) + (6.25 * input_tb) - (5 * input_umur) - 161
    rekomendasi_tdee = int(bmr * 1.2)
    
    st.info(f"💡 Rekomendasi Medis: Tubuhmu membakar sekitar **{rekomendasi_tdee} kcal** per hari. Kalau mau nurunin berat badan, usahakan target kalorimu di bawah angka tersebut (misal: kurangi 300-500).")
    
    # Input Target Kalori Tetap Bisa Diubah Manual
    target_pilihan = st.number_input("Atur Target Kalori Harianmu:", 500, 5000, value=st.session_state.target_calories, step=50)
    
    if st.button("Simpan Profil & Catat BB Hari Ini"):
        st.session_state.bb = input_bb
        st.session_state.tb = input_tb
        st.session_state.umur = input_umur
        st.session_state.gender = input_gender
        st.session_state.target_calories = target_pilihan
        
        # Simpan ke Weight Tracker
        today_str = datetime.now().strftime("%Y-%m-%d")
        st.session_state.weight_history[today_str] = input_bb
        
        save_data_to_db()
        st.success("Data berhasil diamankan ke brankas! 🔒")

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
    for meal in st.session_state.meal_history:
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

# --- PELACAK BERAT BADAN (WEIGHT TRACKER) ---
if st.session_state.weight_history:
    st.markdown("<h3 style='color:#5D4037; font-weight:700; margin-top:30px; margin-bottom:15px;'>📈 Perjalanan Berat Badanku</h3>", unsafe_allow_html=True)
    # Ubah dict ke dataframe untuk chart
    df_weight = pd.DataFrame(list(st.session_state.weight_history.items()), columns=['Tanggal', 'Berat (kg)'])
    df_weight['Tanggal'] = pd.to_datetime(df_weight['Tanggal'])
    df_weight = df_weight.sort_values('Tanggal')
    
    # Line chart Streamlit bawaan sangat bagus dan rapi
    st.line_chart(df_weight.set_index('Tanggal'))


# --- FITUR UTAMA: SCAN KAMERA & AI ---
st.markdown("<hr style='border-top: 2px dashed #FFE2E2; margin: 30px 0;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#5D4037; text-align:center; font-weight:700;'>Scan Makananmu Di Sini! 📸</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8D6E63; margin-top:-10px; margin-bottom:20px;'>Klik tombol pink di bawah untuk memfoto atau upload gambar makananmu.</p>", unsafe_allow_html=True)

if not api_key_configured:
    st.error("⚠️ Menunggu Kunci Rahasia... Minta panduan dari developer.")

uploaded_file = st.file_uploader("Scan Kalori!", type=["jpg", "png", "jpeg", "webp"], label_visibility="collapsed", key=st.session_state.uploader_key)

if uploaded_file is not None and api_key_configured:
    st.image(uploaded_file, caption="Makanan yang sedang diproses...", use_container_width=True)
    file_id = uploaded_file.file_id
    if file_id not in st.session_state.processed_files:
        waktu_makan = st.time_input("Jam berapa kamu makan ini? 🕰️ (Opsional)", value=None)
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
                    response = model.generate_content([prompt, image], generation_config={"temperature": 0.0})
                    teks_hasil = response.text
                    
                    nama_match = re.search(r'\*\*Nama Makanan:\*\*\s*(.+)', teks_hasil)
                    kalori_match = re.search(r'\*\*Estimasi Kalori:\*\*\s*(\d+)', teks_hasil)
                    karbo_match = re.search(r'\*\*Karbohidrat:\*\*\s*(\d+)', teks_hasil)
                    protein_match = re.search(r'\*\*Protein:\*\*\s*(\d+)', teks_hasil)
                    lemak_match = re.search(r'\*\*Lemak:\*\*\s*(\d+)', teks_hasil)
                    
                    kalori_baru = 0
                    if kalori_match: 
                        kalori_baru = int(kalori_match.group(1))
                        st.session_state.consumed_calories += kalori_baru
                    if karbo_match: st.session_state.consumed_carbs += int(karbo_match.group(1))
                    if protein_match: st.session_state.consumed_protein += int(protein_match.group(1))
                    if lemak_match: st.session_state.consumed_fat += int(lemak_match.group(1))
                    
                    jam_str = waktu_makan.strftime('%H:%M') if waktu_makan else "Waktu tak dicatat"
                    nama_makanan_baru = nama_match.group(1).strip() if nama_match else "Makanan Lezat"
                    
                    st.session_state.meal_history.append({"name": nama_makanan_baru, "calories": kalori_baru, "time": jam_str})
                    st.session_state.processed_files.add(file_id)
                    st.session_state.last_response = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', teks_hasil)
                    
                    save_data_to_db()
                    st.rerun()
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "quota" in error_msg.lower():
                        st.error("⏳ Oops! Terlalu banyak foto yang di-scan beruntun! Tunggu sekitar 1 menit lagi ya cantik, baru klik tombol hitung lagi! 🌸")
                    else:
                        st.error(f"Duh, mataku (AI) agak blur. Ada error nih: {e}")
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
    save_data_to_db()
    st.rerun()

# Tombol Logout
st.markdown("<hr style='border-top: 1px solid #FFE2E2;'>", unsafe_allow_html=True)
if st.button("Keluar Akun (Logout)", type="secondary"):
    st.session_state.logged_in_user = None
    st.rerun()
