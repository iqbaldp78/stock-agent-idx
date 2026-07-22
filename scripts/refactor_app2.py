import os

with open("ui/app.py", "r") as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('if page == "📈 Top Picks":'):
        start_idx = i
    elif start_idx != -1 and line.startswith('elif page == "💹 Trading Engine":'):
        end_idx = i
        break

top_picks_orig = lines[start_idx:end_idx]

# Find where '    elif signals:' starts and ends
db_block_start = -1
db_block_end = -1
for i, line in enumerate(top_picks_orig):
    if line.startswith('    elif signals:'):
        db_block_start = i
    elif db_block_start != -1 and line.startswith('    else:'):
        db_block_end = i
        break

db_block = top_picks_orig[db_block_start + 1: db_block_end]

# Extract it into a function `render_signals_list`
new_func = ["def render_signals_list(signals):\n", "    if not signals:\n", "        return\n"]
for line in db_block:
    if line.startswith("    "):
        new_func.append(line[4:])
    else:
        new_func.append(line)

new_top_picks = []
new_top_picks.append('if page == "📈 Top Picks":\n')
new_top_picks.append('    st.title("📈 TOP PICKS")\n')
new_top_picks.append('\n')

for line in new_func:
    new_top_picks.append("    " + line)

new_top_picks.append('\n')
new_top_picks.append('''    tab_regular, tab_konglo = st.tabs(["📊 Regular Top Picks", "🐋 Konglo Play Picks"])

    with tab_regular:
        latest_meta_reg = query_db("""
            SELECT MAX(run_date) AS max_run_date
            FROM signals
            WHERE batch_id IS NOT NULL AND is_konglo = FALSE
        """)
        latest_run_date_reg = latest_meta_reg[0]["max_run_date"] if latest_meta_reg else None
        
        latest_batch_reg = None
        if latest_run_date_reg is not None:
            latest_batch_res = query_db("""
                SELECT batch_id
                FROM signals
                WHERE run_date = %s
                AND batch_id IS NOT NULL AND is_konglo = FALSE
                LIMIT 1
            """, (latest_run_date_reg,))
            latest_batch_reg = (latest_batch_res[0]["batch_id"] if latest_batch_res else None)
            
        signals_reg = []
        if latest_run_date_reg is not None:
            if latest_batch_reg:
                signals_reg = query_db("""
                    SELECT * FROM signals
                    WHERE batch_id = %s
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_batch_reg,))
            else:
                signals_reg = query_db("""
                    SELECT * FROM signals
                    WHERE run_date = %s
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_run_date_reg,))
                
        if signals_reg:
            render_signals_list(signals_reg)
        else:
            st.info("Belum ada Regular Picks. Silahkan jalankan analisis terlebih dahulu.")
            
    with tab_konglo:
        latest_meta_konglo = query_db("""
            SELECT MAX(run_date) AS max_run_date
            FROM signals
            WHERE batch_id IS NOT NULL AND is_konglo = TRUE
        """)
        latest_run_date_konglo = latest_meta_konglo[0]["max_run_date"] if latest_meta_konglo else None
        
        latest_batch_konglo = None
        if latest_run_date_konglo is not None:
            latest_batch_res = query_db("""
                SELECT batch_id
                FROM signals
                WHERE run_date = %s
                AND batch_id IS NOT NULL AND is_konglo = TRUE
                LIMIT 1
            """, (latest_run_date_konglo,))
            latest_batch_konglo = (latest_batch_res[0]["batch_id"] if latest_batch_res else None)
            
        signals_konglo = []
        if latest_run_date_konglo is not None:
            if latest_batch_konglo:
                signals_konglo = query_db("""
                    SELECT * FROM signals
                    WHERE batch_id = %s
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_batch_konglo,))
            else:
                signals_konglo = query_db("""
                    SELECT * FROM signals
                    WHERE run_date = %s
                    AND rank IS NOT NULL
                    ORDER BY rank
                    LIMIT 3
                """, (latest_run_date_konglo,))
                
        if signals_konglo:
            render_signals_list(signals_konglo)
        else:
            st.info("👋 Belum ada data Konglo Picks. Silahkan jalankan 'Konglo Analysis' dari menu Konglo Play terlebih dahulu.")

''')

new_app_lines = lines[:start_idx] + new_top_picks + lines[end_idx:]

with open("ui/app_new.py", "w") as f:
    f.writelines(new_app_lines)
