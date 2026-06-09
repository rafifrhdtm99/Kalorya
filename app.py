import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Kalorya", page_icon="🌸", layout="centered")

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
    
    /* Menyembunyikan elemen bawaan Streamlit agar bersih */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background-color: #FEF9F8;}
    
    /* Desain Kartu Kaca (Glass Card) */
    .cute-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(255, 183, 178, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.8);
        margin-bottom: 24px;
    }
    
    /* Mempercantik tombol upload Streamlit menjadi mirip tombol kamera */
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
    [data-testid="stFileUploadDropzone"] svg {
        fill: white !important;
        width: 40px;
        height: 40px;
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

st.write("") # Spasi

# --- WIDGET LINGKARAN KALORI (HTML CUSTOM) ---
consumed = 1250
target = 1800
progress = min((consumed / target) * 100, 100)
dash_offset = 439.8 - (439.8 * progress / 100)

ring_html = f"""<div class="cute-card">
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
<div style="width: 55px; height: 6px; background: #E0F2F1; border-radius: 3px; margin: 0 auto 8px;">
<div style="width: 80%; height: 100%; background: #4DD0E1; border-radius: 3px;"></div>
</div>
<div style="font-weight: 700; color: #5D4037; font-size: 1.1rem;">120g</div>
</div>
<div style="text-align: center;">
<div style="font-size: 0.85rem; color: #8D6E63; font-weight: 600; margin-bottom: 8px;">Protein</div>
<div style="width: 55px; height: 6px; background: #FFE2E2; border-radius: 3px; margin: 0 auto 8px;">
<div style="width: 75%; height: 100%; background: #FFB7B2; border-radius: 3px;"></div>
</div>
<div style="font-weight: 700; color: #5D4037; font-size: 1.1rem;">45g</div>
</div>
<div style="text-align: center;">
<div style="font-size: 0.85rem; color: #8D6E63; font-weight: 600; margin-bottom: 8px;">Lemak</div>
<div style="width: 55px; height: 6px; background: #E8F5E9; border-radius: 3px; margin: 0 auto 8px;">
<div style="width: 80%; height: 100%; background: #81C784; border-radius: 3px;"></div>
</div>
<div style="font-weight: 700; color: #5D4037; font-size: 1.1rem;">40g</div>
</div>
</div>
</div>"""
st.markdown(ring_html, unsafe_allow_html=True)


# --- FITUR UTAMA: SCAN KAMERA & AI ---
st.write("")
st.markdown("<h3 style='color:#5D4037; text-align:center; font-weight:700;'>Scan Makananmu Di Sini! 📸</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8D6E63; margin-top:-10px; margin-bottom:20px;'>Klik tombol pink di bawah untuk memfoto atau upload gambar makananmu.</p>", unsafe_allow_html=True)

if not api_key_configured:
    st.error("⚠️ Menunggu Kunci Rahasia... Minta panduan dari developer untuk memasukkan API Key di Streamlit Secrets.")

# Tombol Upload yang sudah dipercantik CSS menjadi tombol kamera
uploaded_file = st.file_uploader("Scan Kalori!", type=["jpg", "png", "jpeg", "webp"], label_visibility="collapsed")

if uploaded_file is not None and api_key_configured:
    st.image(uploaded_file, caption="Makanan yang sedang diproses...", use_container_width=True)
    
    with st.spinner("✨ AI Kalorya sedang menebak kalori makananmu..."):
        try:
            image = Image.open(uploaded_file)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = """
            Kamu adalah asisten diet wanita gen z yang ramah, manis, dan suportif bernama Kalorya.
            Tolong tebak makanan apa yang ada di gambar ini dan berikan estimasi kasar nutrisinya.
            
            Format balasan harus persis seperti ini:
            **Nama Makanan:** [Tebakanmu]
            **Estimasi Kalori:** [Angka] kcal
            **Karbohidrat:** [Angka] g
            **Protein:** [Angka] g
            **Lemak:** [Angka] g
            
            Berikan 1 atau 2 kalimat suportif dan lucu khas gen z di bagian paling bawah untuk menyemangati dia!
            """
            
            response = model.generate_content([prompt, image])
            teks_hasil = response.text
            
            st.markdown(f"""
            <div class="cute-card" style="background-color: #FFF0F5; border: 2px solid #FFB7B2;">
                <h4 style="color: #FFB7B2; margin-top:0;">✨ Hasil Scan Kalorya:</h4>
                <div style="color: #5D4037; font-size: 1.05rem; line-height: 1.6;">
                    {teks_hasil.replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Duh, mataku (AI) agak blur. Ada error nih: {e}")

st.markdown("<br><br>", unsafe_allow_html=True)
