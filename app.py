import streamlit as st

st.set_page_config(page_title="Kalorya", page_icon="🌸", layout="centered")

# Custom CSS
st.markdown("""
<style>
    /* Custom styling to make it look like our pastel mockup */
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #FFB7B2;
        font-weight: 700;
    }
    
    .stProgress > div > div > div > div {
        background-color: #FFB7B2;
    }
    
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
        color: #8D6E63;
    }
    
    /* Make headers look cute */
    h1, h2, h3 {
        color: #5D4037 !important;
    }
    
    /* Hide default Streamlit elements for app-like feel */
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Header
col1, col2 = st.columns([1, 4])
with col1:
    st.image("kalorya_logo.png", width=60)
with col2:
    st.markdown("<h1 style='margin-bottom:0; padding-bottom:0; font-size:2.2rem;'>Hai cantik! 🌸</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8D6E63; font-weight:600; margin-top:0;'>Kalorya - Tetep konsisten, ya!</p>", unsafe_allow_html=True)

st.divider()

# Calorie Dashboard
st.subheader("Ringkasan Hari Ini")
st.progress(70, text="Kalori Terisi: 1.250 / 1.800 kcal")

cc, cp, cf = st.columns(3)
cc.metric("Karbo", "120g", "Target: 150g", delta_color="off")
cp.metric("Protein", "45g", "Target: 60g", delta_color="off")
cf.metric("Lemak", "40g", "Target: 50g", delta_color="off")

st.divider()

# Weight Progress
st.subheader("Target Berat Badan")
st.progress(30, text="Saat ini: 62 kg | Target: 55 kg | Awal: 65 kg")
if st.button("➕ Update Berat Badan", use_container_width=True):
    st.info("Fitur form update berat badan akan muncul di sini.")

st.divider()

# Main Feature: Camera / Upload
st.subheader("Makan Apa Hari Ini? 📸")
st.markdown("Upload foto makananmu, AI akan menghitung kalorinya!")

uploaded_file = st.file_uploader("Pilih foto makanan", type=["jpg", "png", "jpeg"], label_visibility="collapsed")

if uploaded_file is not None:
    st.success("Foto berhasil diupload! AI sedang mengenali makananmu... ✨")
    st.image(uploaded_file, caption="Makanan yang difoto", use_container_width=True)
    
    # Mock AI Result
    st.info("✨ **Wah, makan siangmu terlihat enak!** Berdasarkan analisis AI, ini mengandung sekitar 600 kcal. Masih ada ruang **550 kalori** untuk cemilan manis sore ini 🍰")

st.divider()

# History
st.subheader("Riwayat Dietmu")
st.success("🎯 **Rabu, 8 Jun:** Sempurna! Defisit tercapai (1.500 kcal)")
st.warning("🍰 **Selasa, 7 Jun:** Agak Berlebihan. Lebih 200 kalori dari target")
st.success("✨ **Senin, 6 Jun:** Bagus Banget! Tepat di angka 1.750 kcal")
