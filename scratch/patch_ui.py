import re

with open("web-frontend/src/app/(app)/trading/page.tsx", "r") as f:
    content = f.read()

# 1. Add states for performance
state_addition = """
  // Tabs
  const [activeTab, setActiveTab] = useState<'desk' | 'analytics'>('desk');
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);
"""
content = content.replace("  // Quick Buy tab & picks states", state_addition + "\n  // Quick Buy tab & picks states")

# 2. Add fetch function
fetch_addition = """
  const fetchPerformanceData = async () => {
    setPerformanceLoading(true);
    try {
      const res = await fetch("/api/trading/performance", {
        headers: { 'Authorization': `Bearer ${localStorage.getItem("token")}` }
      });
      if (res.ok) {
        const json = await res.json();
        if (json.status === "success") {
          setPerformanceData(json.data);
        }
      }
    } catch (err) {
      console.error("Gagal mengambil metrik performance:", err);
    } finally {
      setPerformanceLoading(false);
    }
  };
"""
content = content.replace("  const fetchEquityData = async () => {", fetch_addition + "\n  const fetchEquityData = async () => {")

# 3. Add to useEffect
content = content.replace("fetchEquityData();\n\n    authenticatedFetch", "fetchEquityData();\n    fetchPerformanceData();\n\n    authenticatedFetch")
content = content.replace("fetchTradingData(); fetchEquityData(); }", "fetchTradingData(); fetchEquityData(); fetchPerformanceData(); }")


with open("web-frontend/src/app/(app)/trading/page.tsx", "w") as f:
    f.write(content)

print("UI state patched")
