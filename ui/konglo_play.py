import streamlit as st
from db import SessionLocal
from db.models import Universe
import pandas as pd
import re
from services.konglo_screener import run_konglo_screen

def render_konglo_play_page():
    st.title("🐋 Konglo Play")
    st.caption("Identifikasi saham dengan potensi fast-gain berdasarkan akumulasi broker & momentum teknikal, mengabaikan fundamental.")

    st.subheader("➕ Tambah Ticker Konglo Play")
    with st.form("add_konglo_form"):
        new_tickers = st.text_area(
            "Masukkan ticker (pisahkan dengan koma, spasi, atau baris baru):",
            placeholder="GOTO, PANI\nBRIS AMRT"
        )
        submitted = st.form_submit_button("Tambahkan ke Konglo Universe")
        if submitted and new_tickers:
            tickers = [t.strip().upper() for t in re.split(r'[,\s\n]+', new_tickers) if t.strip()]
            if tickers:
                db = SessionLocal()
                added = 0
                for t in tickers:
                    existing = db.query(Universe).filter_by(ticker=t).first()
                    if not existing:
                        db.add(Universe(ticker=t, is_custom=True, active=True, is_konglo=True))
                        added += 1
                    elif not existing.is_konglo:
                        existing.is_konglo = True
                        if not existing.active:
                            existing.active = True
                        added += 1
                db.commit()
                db.close()
                st.success(f"Berhasil menambahkan atau mengaktifkan {added} ticker untuk Konglo Play.")
                st.rerun()

    st.divider()
    
    st.subheader("🚀 Trigger Analisis Konglo")
    if st.button("⚡ Jalankan Analisis (Background)", type="primary", use_container_width=True):
        import subprocess
        subprocess.Popen(["python", "scripts/run_konglo_analysis.py"])
        st.success("Analisis sedang berjalan di background. Mohon tunggu beberapa menit, hasilnya akan muncul di menu Top Picks utama.")

    st.divider()

    st.subheader("📋 Daftar Konglo Universe")
    db = SessionLocal()
    records = db.query(Universe).filter_by(is_konglo=True).order_by(Universe.ticker).all()
    db.close()

    if records:
        df = pd.DataFrame([{
            "id": r.id,
            "ticker": r.ticker,
            "active": r.active,
            "remove_from_konglo": False
        } for r in records])

        st.caption("Centang kolom **Active** untuk on/off dari Konglo Play, atau **Hapus** untuk menghapus dari list ini.")
        edited_df = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=["id", "ticker"],
            column_config={
                "active": st.column_config.CheckboxColumn("Active"),
                "remove_from_konglo": st.column_config.CheckboxColumn("🗑️ Hapus dari Konglo"),
            },
            key="konglo_editor"
        )

        if st.button("💾 Simpan Perubahan Konglo", type="primary"):
            rows_to_remove = edited_df[edited_df['remove_from_konglo'] == True]
            changed_rows = edited_df[(edited_df['active'] != df['active']) & (edited_df['remove_from_konglo'] == False)]

            if not rows_to_remove.empty or not changed_rows.empty:
                db = SessionLocal()
                for _, row in rows_to_remove.iterrows():
                    u = db.query(Universe).filter_by(id=row['id']).first()
                    if u:
                        u.is_konglo = False
                for _, row in changed_rows.iterrows():
                    u = db.query(Universe).filter_by(id=row['id']).first()
                    if u:
                        u.active = bool(row['active'])
                db.commit()
                db.close()
                st.success("Perubahan berhasil disimpan.")
                st.rerun()
            else:
                st.info("Tidak ada perubahan.")

