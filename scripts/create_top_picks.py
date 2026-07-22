import os

with open('scratch/top_picks_orig.py', 'r') as f:
    lines = f.readlines()

# The original code has:
# lines[0] is 'if page == "📈 Top Picks":\n'
# We want to extract the rendering logic for DB signals.
# Let's find '    elif signals:\n'
start_db_idx = -1
end_db_idx = -1
for i, line in enumerate(lines):
    if line.startswith('    elif signals:'):
        start_db_idx = i
        break
for i in range(start_db_idx + 1, len(lines)):
    if line.startswith('elif page =='): # Shouldn't happen here
        break

# Let's find '    if top_picks_live:\n'
start_live_idx = -1
for i, line in enumerate(lines):
    if line.startswith('    if top_picks_live:'):
        start_live_idx = i
        break

# So live block is from start_live_idx to start_db_idx
live_block = lines[start_live_idx:start_db_idx]
# DB block is from start_db_idx to end
db_block = lines[start_db_idx:]

with open('scratch/extract_test.txt', 'w') as f:
    f.write(f"Live block starts at {start_live_idx}, DB block starts at {start_db_idx}\n")
    f.write(f"Live block length: {len(live_block)}, DB block length: {len(db_block)}\n")

