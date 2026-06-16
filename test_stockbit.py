import httpx

def get_html():
    response = httpx.get("https://stockbit.com/#/login")
    print(response.text)

if __name__ == "__main__":
    get_html()
