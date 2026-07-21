import streamlit as st
from db import SessionLocal
from db.models import Universe
import pandas as pd
import re
from services.konglo_screener import run_konglo_screen

def render_konglo_play_page():
    st.title("🐋 Konglo Play")
    st.caption("Identifikasi saham dengan potensi fast-gain berdasarkan akumulasi broker & momentum teknikal, mengabaikan fundamental.")

    tab1, tab2 = st.tabs(["🚀 Top Picks (Debate)", "📋 Kelola Universe"])

    with tab2:
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

    with tab1:
        st.subheader("🚀 Top Picks (Konglo Mode)")
        if st.button("⚡ Jalankan Analisis (Background)", type="primary", use_container_width=True):
            import subprocess
            subprocess.Popen(["python", "scripts/run_konglo_analysis.py"])
            st.success("Analisis sedang berjalan di background (termasuk debat & IM). Mohon tunggu 2-3 menit lalu refresh halaman ini.")

        st.divider()
        st.subheader("Hasil Analisis Terakhir")
        db = SessionLocal()
        from db.models import Signal
        from sqlalchemy import desc
        
        latest_signal = db.query(Signal).filter_by(batch_id="KONGLO_PICKS").order_by(desc(Signal.run_date)).first()
        if latest_signal:
            latest_date = latest_signal.run_date
            st.caption(f"Update Terakhir: {latest_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            picks = db.query(Signal).filter_by(batch_id="KONGLO_PICKS", run_date=latest_date).order_by(Signal.rank).all()
            
            cols = st.columns(2)
            for i, p in enumerate(picks):
                badge_color = 'good' if p.conviction == 'HIGH' else 'warning' if p.conviction == 'MEDIUM' else 'critical'
                
                with cols[i % 2]:
                    st.markdown(f"""
                    <div class="card" style="margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin:0; color: #2563eb;">#{p.rank} {p.ticker}</h3>
                            <span class="badge badge-{badge_color}">{p.conviction}</span>
                        </div>
                        <hr style="opacity: 0.2">
                        <p><strong>Signal:</strong> {p.signal} | <strong>Entry:</strong> {p.entry_low} - {p.entry_high}</p>
                        <p><strong>Targets:</strong> TP1: {p.target_1}, TP2: {p.target_2}, TP3: {p.target_3} | <strong>SL:</strong> {p.stop_loss}</p>
                        <p><strong>Tesis:</strong></p>
                        <pre style="white-space: pre-wrap; font-family: inherit; background: transparent; border: none;">{p.thesis}</pre>
                        <div style="display: flex; gap: 10px; font-size: 0.8rem; color: #6b7280; margin-top: 10px;">
                            <span>Broker Utama: {p.broker_utama}</span>|
                            <span>Bandar Avg (1M): {p.bandar_avg_1m}</span>|
                            <span>Composite: {p.composite_score}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Belum ada hasil analisis Konglo Picks.")
        db.close()

