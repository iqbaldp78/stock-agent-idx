from playwright.sync_api import sync_playwright
import os

def test():
    username = os.getenv("STOCKBIT_USERNAME")
    password = os.getenv("STOCKBIT_PASSWORD")
    
    def handle_response(response):
        if "login/v6/username" in response.url and response.request.method == "POST":
            print("Intercepted POST to", response.url)
            try:
                data = response.json()
                print("JSON DATA:", data)
            except Exception as e:
                print("Failed to parse json:", e)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.on("response", handle_response)
        
        page.goto("https://stockbit.com/#/login", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('input#username', timeout=15000)
        
        page.fill('input#username', username)
        page.fill('input#password', password)
        page.locator('button#email-login-button').click()
        
        page.wait_for_timeout(10000)
        browser.close()

if __name__ == "__main__":
    test()
