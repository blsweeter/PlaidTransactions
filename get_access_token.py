# get_access_token.py
import requests
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
SECRET = os.getenv("PLAID_SECRET")

def create_public_token():
    url = "https://sandbox.plaid.com/sandbox/public_token/create"
    payload = {
        "client_id": CLIENT_ID,
        "secret": SECRET,
        "institution_id": "ins_109508",
        "initial_products": ["auth", "transactions"]
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if "public_token" not in data:
        raise Exception(f"Failed to get public token: {data}")
    return data["public_token"]

def exchange_public_token(public_token):
    url = "https://sandbox.plaid.com/item/public_token/exchange"
    payload = {
        "client_id": CLIENT_ID,
        "secret": SECRET,
        "public_token": public_token
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if "access_token" not in data:
        raise Exception(f"Failed to get access token: {data}")
    return data["access_token"]

def main():
    try:
        print("Creating sandbox public token...")
        public_token = create_public_token()
        print("Public token:", public_token)

        print("Exchanging public token for access token...")
        access_token = exchange_public_token(public_token)

        with open("access_token.txt", "w") as f:
            f.write(access_token)
        print("Access token saved to access_token.txt!")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()