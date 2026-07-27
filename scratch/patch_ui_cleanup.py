import re

with open("web-frontend/src/app/(app)/trading/page.tsx", "r") as f:
    content = f.read()

# We need to remove the old "Closed Trades" section completely because it's now inside the Analytics tab
# We find it and remove it.
start_str = "{/* Closed Trades */}"
end_str = "</>"

start_idx = content.find(start_str)

if start_idx != -1:
    # Find the SECOND occurrence of start_str since we just injected one.
    first_idx = content.find(start_str)
    second_idx = content.find(start_str, first_idx + 1)
    
    if second_idx != -1:
        # We need to find the matching </> for the whole <> block
        # It's at the very end of the return statement
        # Instead, let's just use string slicing carefully
        
        # We know the old Closed trades section starts with <div>\s*<h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📜</span> Trade History (Closed)</h3>
        old_start = content.find('<div>\n              <h3 className="text-lg font-bold text-text mb-4 flex items-center gap-2"><span>📜</span> Trade History (Closed)</h3>')
        
        if old_start != -1:
            # Delete from old_start up to </> (exclusive)
            end_tag = content.find("</>", old_start)
            if end_tag != -1:
                content = content[:old_start] + content[end_tag:]

with open("web-frontend/src/app/(app)/trading/page.tsx", "w") as f:
    f.write(content)

print("UI content cleanup done")
