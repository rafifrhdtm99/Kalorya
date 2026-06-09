import sys

with open(r'C:\Users\PC-MARKETING-01\.gemini\antigravity\scratch\kalorya\app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
inside_tab1 = False
for i, line in enumerate(lines):
    if i == 300: # line 301 in 1-based
        new_lines.append('tab1, tab2 = st.tabs(["🏠 Beranda Hari Ini", "📅 Rekap & Riwayat"])\n')
        new_lines.append('with tab1:\n')
        inside_tab1 = True
        
    if inside_tab1 and i >= 300:
        if line.strip() == '':
            new_lines.append(line)
        else:
            new_lines.append('    ' + line)
    else:
        new_lines.append(line)

new_lines.append('\n')
new_lines.append('with tab2:\n')
new_lines.append('    st.markdown("<h3 style=\'color:#5D4037; font-weight:700;\'>📅 Rekap Kalori Harian</h3>", unsafe_allow_html=True)\n')
new_lines.append('    \n')
new_lines.append('    daily_records = st.session_state.get("daily_records", {})\n')
new_lines.append('    if not daily_records:\n')
new_lines.append('        st.info("Belum ada riwayat makanan di hari-hari sebelumnya.")\n')
new_lines.append('    else:\n')
new_lines.append('        import pandas as pd\n')
new_lines.append('        df_rekapan = pd.DataFrame([{"Tanggal": k, "Kalori": v["calories"]} for k, v in daily_records.items()])\n')
new_lines.append('        df_rekapan["Tanggal"] = pd.to_datetime(df_rekapan["Tanggal"])\n')
new_lines.append('        df_rekapan = df_rekapan.sort_values("Tanggal")\n')
new_lines.append('        st.bar_chart(df_rekapan.set_index("Tanggal"))\n')
new_lines.append('        \n')
new_lines.append('        st.markdown("<hr style=\'border-top: 2px dashed #FFE2E2; margin: 30px 0;\'>", unsafe_allow_html=True)\n')
new_lines.append('        st.markdown("<h3 style=\'color:#5D4037; font-weight:700;\'>🍽️ Cek Makanan Masa Lalu</h3>", unsafe_allow_html=True)\n')
new_lines.append('        tanggal_pilihan = st.date_input("Pilih Tanggal:")\n')
new_lines.append('        tgl_str = tanggal_pilihan.strftime("%Y-%m-%d")\n')
new_lines.append('        if tgl_str in daily_records:\n')
new_lines.append('            st.success(f"Total Kalori pada {tgl_str}: **{daily_records[tgl_str][\'calories\']} kcal**")\n')
new_lines.append('            for meal in daily_records[tgl_str]["meals"]:\n')
new_lines.append('                jam_teks = meal.get("time", "Waktu tak dicatat")\n')
new_lines.append('                st.markdown(f"""<div class=\\"meal-item\\"><div style=\\"font-size: 0.8rem; color: #8D6E63; margin-bottom: 4px;\\">🕰️ {jam_teks}</div><div class=\\"meal-name\\">🍽️ {meal[\'name\']}</div><div class=\\"meal-cal\\">+{meal[\'calories\']} kcal</div></div>""", unsafe_allow_html=True)\n')
new_lines.append('        else:\n')
new_lines.append('            st.warning("Tidak ada catatan makanan pada tanggal ini.")\n')

with open(r'C:\Users\PC-MARKETING-01\.gemini\antigravity\scratch\kalorya\app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
