import os
import sys

# Tambahkan path root agar bisa import module 'data'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.fetcher_stockbit import refresh_stockbit_token

def main():
    # Menggunakan refresh token dari user untuk test
    user_refresh_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImExNWQ5OGE2LTdkYzgtNDM3NS05NDk0LTEyOWJlM2RlODVkNCIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7InR5cCI6InJlZnJlc2giLCJ1c2UiOiJpcWJhbGRwNzgiLCJlbWEiOiJpcWJhbGRwNzhAZ21haWwuY29tIiwiZnVsIjoiaXFiYWwgZHAiLCJzZXMiOiI2TWV1azdieW9QNks3eUpXIiwiZHZjIjoiNTY1MGEyY2ZmMzM1MDAzNmZlNGEzOGJhMDdmZjNiYjAiLCJ1aWQiOjU2NTEzMDIsImNvdSI6IklEIn0sImV4cCI6MTc4MjE5MjQyNSwiaWF0IjoxNzgxNTg3NjI1LCJpc3MiOiJTVE9DS0JJVCIsImp0aSI6ImRiNGM4NWQ2LTc1MzUtNDM1MS1hNzU1LTk2MDJjZDM1Njg0YyIsIm5iZiI6MTc4MTU4NzYyNSwidmVyIjoidjEifQ.L36Ogr5xqJYy7ucvYnwa6lD2zp_xq9MKgUXglwc_5ILlLL7t8SNT6dYQhMN3JH1tquJzDMrrh464l88TobAhpdj049zGILhy0o97hcN4A2C32OOP3ArAZY-xuza6fGQLBdEHW90uHBJJIQh4vDCeYglEGhs4b5YGytH7T3VGIm7u8LZddxH-xFSvrx-SYpSjQkZ9LbcP_dFubaIraUHIZSXe4VepwQ0TmG6hck5Ij5y4ZtPN08W21VaERSBIQ_JS2cYsf-IiG0SRcjaqB_AT6_Mv7fMQgba5Zk7mmD_S6jYT2xtKLmtCGaRlFRNV4sm_-keQ2Te9wmv573236pf6lg"
    
    # Set env var agar tidak perlu merubah .env saat test
    os.environ["STOCKBIT_REFRESH_TOKEN"] = user_refresh_token
    
    print("Mencoba refresh token...")
    try:
        new_token = refresh_stockbit_token()
        print(f"BERHASIL! Access Token Baru (awalannya): {new_token[:30]}...")
        
        # Cek apakah refresh token diperbarui
        new_refresh = os.environ.get("STOCKBIT_REFRESH_TOKEN")
        if new_refresh and new_refresh != user_refresh_token:
            print("INFO: Stockbit juga memberikan Refresh Token baru!")
    except Exception as e:
        print(f"GAGAL: {e}")

if __name__ == "__main__":
    main()
