import re
with open("web-frontend/src/app/(app)/layout.tsx", "r") as f:
    content = f.read()

content = content.replace('{ href: "/history", label: "AI Track Record", icon: "📊", id: "history" },', '{ href: "/history", label: "AI Performance", icon: "📊", id: "history" },')

with open("web-frontend/src/app/(app)/layout.tsx", "w") as f:
    f.write(content)
