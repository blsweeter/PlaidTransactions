from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd
from datetime import datetime, timedelta
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
import os
import io
import json
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
SECRET = os.getenv("PLAID_SECRET")
ENV = os.getenv("PLAID_ENV", "production")
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", "/data/transactions.xlsx")
ENV_FILE = ".env"

def _load_access_tokens():
    raw = os.getenv("PLAID_ACCESS_TOKENS", "[]")
    try:
        return json.loads(raw)
    except Exception:
        single = os.getenv("PLAID_ACCESS_TOKEN", "")
        return [{"token": single, "institution": "Bank"}] if single else []

def _save_access_tokens(tokens):
    serialized = json.dumps(tokens)
    set_key(ENV_FILE, "PLAID_ACCESS_TOKENS", serialized)
    os.environ["PLAID_ACCESS_TOKENS"] = serialized

host = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}[ENV]

config = Configuration(host=host)
config.api_key["clientId"] = CLIENT_ID
config.api_key["secret"] = SECRET
api_client = ApiClient(config)
client = plaid_api.PlaidApi(api_client)

app = Flask(__name__)
CORS(app)


@app.route("/api/create_link_token", methods=["POST"])
def create_link_token():
    try:
        request_data = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id="user-id"),
            client_name="Plaid Transaction Fetcher",
            products=[Products("transactions")],
            country_codes=[CountryCode("US")],
            language="en",
        )
        response = client.link_token_create(request_data)
        return jsonify({"link_token": response["link_token"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/exchange_token", methods=["POST"])
def exchange_token():
    try:
        public_token = request.json.get("public_token")
        institution_name = request.json.get("institution_name", "Unknown Bank")
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = client.item_public_token_exchange(exchange_request)
        access_token = response["access_token"]
        tokens = _load_access_tokens()
        tokens.append({"token": access_token, "institution": institution_name})
        _save_access_tokens(tokens)
        return jsonify({"success": True, "institution": institution_name, "total_connected": len(tokens)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/remove_account", methods=["POST"])
def remove_account():
    try:
        index = request.json.get("index")
        tokens = _load_access_tokens()
        if index < 0 or index >= len(tokens):
            return jsonify({"error": "Invalid index"}), 400
        removed = tokens.pop(index)
        _save_access_tokens(tokens)
        return jsonify({"success": True, "removed": removed["institution"], "total_connected": len(tokens)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def status():
    tokens = _load_access_tokens()
    return jsonify({
        "connected": len(tokens) > 0,
        "accounts": [t["institution"] for t in tokens],
        "count": len(tokens),
    })


@app.route("/api/fetch_transactions", methods=["POST"])
def fetch_transactions():
    try:
        tokens = _load_access_tokens()
        if not tokens:
            return jsonify({"error": "No accounts connected. Please connect a bank first."}), 400

        existing_t_df = None
        existing_a_df = None
        if "file" in request.files:
            f = request.files["file"]
            contents = f.read()
            existing_t_df = pd.read_excel(io.BytesIO(contents), sheet_name="Transactions")
            existing_a_df = pd.read_excel(io.BytesIO(contents), sheet_name="Account Info")

        all_transactions = []
        all_accounts = []
        start_date = (datetime.now() - timedelta(days=730)).date()
        end_date = datetime.now().date()

        for entry in tokens:
            try:
                txns, accts = _fetch_data(entry["token"], start_date, end_date)
                all_transactions.extend(txns)
                all_accounts.extend(accts)
            except Exception as e:
                print(f"Failed to fetch for {entry['institution']}: {e}")

        transaction_df = _parse_transactions(all_transactions, all_accounts)
        account_df = _parse_account_data(all_accounts)

        if existing_t_df is not None:
            transaction_df = pd.concat([existing_t_df, transaction_df], ignore_index=True)
            transaction_df.drop_duplicates(subset=["Transaction Id"], inplace=True)
            transaction_df.sort_values("Date", ascending=False, inplace=True)

        if existing_a_df is not None:
            account_df = pd.concat([existing_a_df, account_df], ignore_index=True)
            account_df.drop_duplicates(subset=["Account Id"], inplace=True)

        os.makedirs(os.path.dirname(EXCEL_FILE_PATH), exist_ok=True)
        with pd.ExcelWriter(EXCEL_FILE_PATH, engine="openpyxl") as writer:
            transaction_df.to_excel(writer, sheet_name="Transactions", index=False)
            account_df.to_excel(writer, sheet_name="Account Info", index=False)

        return jsonify({
            "success": True,
            "transactions_count": len(transaction_df),
            "accounts_count": len(account_df),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["GET"])
def download():
    if not os.path.exists(EXCEL_FILE_PATH):
        return jsonify({"error": "No file found. Fetch transactions first."}), 404
    return send_file(
        EXCEL_FILE_PATH,
        as_attachment=True,
        download_name="transactions.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _fetch_data(access_token, start_date, end_date):
    transactions = []
    accounts = []
    offset = 0
    while True:
        options = TransactionsGetRequestOptions(count=500, offset=offset)
        req = TransactionsGetRequest(
            client_id=CLIENT_ID,
            options=options,
            access_token=access_token,
            secret=SECRET,
            start_date=start_date,
            end_date=end_date,
        )
        response = client.transactions_get(req)
        batch = response["transactions"]
        transactions.extend(batch)
        if offset == 0:
            accounts.extend(response["accounts"])
        if len(transactions) >= response["total_transactions"]:
            break
        offset += len(batch)
    return transactions, accounts


def _parse_transactions(transactions, accounts):
    account_map = {a["account_id"]: a for a in accounts}
    rows = []
    for t in transactions:
        acct = account_map.get(t["account_id"], {})
        rows.append({
            "Transaction Id": t["transaction_id"],
            "Date": t["date"],
            "Name": t["name"],
            "Merchant Name": t.get("merchant_name"),
            "Amount": t["amount"],
            "Account Name": acct.get("name"),
            "Account Full Name": acct.get("official_name"),
            "Account Id": t["account_id"],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values("Date", ascending=False, inplace=True)
    return df


def _parse_account_data(accounts):
    seen = set()
    rows = []
    for a in accounts:
        if a["account_id"] in seen:
            continue
        seen.add(a["account_id"])
        rows.append({
            "Account Id": a["account_id"],
            "Name": a["name"],
            "Full Name": a["official_name"],
            "Type": a["subtype"],
            "Available Balance": a["balances"]["available"],
            "Current Balance": a["balances"]["current"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)