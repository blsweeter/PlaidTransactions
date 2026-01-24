import pandas as pd
from datetime import datetime, timedelta
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
import os   
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
SECRET = os.getenv("PLAID_SECRET")
ACCESS_TOKEN = os.getenv("PLAID_ACCESS_TOKEN")
ENV = os.getenv("PLAID_ENV", "sandbox")

EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH")

# Sandbox used for fake data and program testing. Development for read data. Change in env file.
host = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}[ENV]

# Configure client for API setup
config = Configuration(host=host)
config.api_key["clientId"] = CLIENT_ID
config.api_key["secret"] = SECRET
api_client = ApiClient(config)
client = plaid_api.PlaidApi(api_client)

def fetchData():
    # Fetch Transactions using Plaid API
    transactions = []
    accounts = []
    
    start_date = (datetime.now() - timedelta(days=365)).date()
    end_date = datetime.now().date()

    options = TransactionsGetRequestOptions(count=100, offset=0)
    request = TransactionsGetRequest(client_id=CLIENT_ID, options=options, access_token=ACCESS_TOKEN, secret=SECRET, start_date=start_date, end_date=end_date)

    response = client.transactions_get(request)
    
    fetched_transactions = response["transactions"]
    fetched_accounts = response["accounts"]
    transactions.extend(fetched_transactions)
    accounts.extend(fetched_accounts)

    return [transactions, accounts]

    
def parse_transactions(transactions, accounts):
    rows = []
    # For each transactions, get the 
    for t in transactions:
        # Get the account name from fetched accounts
        acct = next((a for a in accounts if a["account_id"] == t["account_id"]), {})
        name = acct.get("name")
        official_name = acct.get("official_name")
        
        rows.append({
            "Transaction Id": t["transaction_id"],
            "Name": t["name"],
            "Merchant Name": t["merchant_name"],
            "Date": t["date"],
            "Account Id": t["account_id"],
            "Account Name": name,
            "Account Full Name": official_name,                
            "Amount": t["amount"]
        })

    return pd.DataFrame(rows)

    
# Parses account data to useful pandas dataframe
def parse_account_data(accounts):
    rows = []
    for a in accounts:
        rows.append({
            "Account Id": a["account_id"],
            "Available Balance": a["balances"]["available"],
            "Current Balance": a["balances"]["current"],
            "Name": a["name"],
            "Full Name": a["official_name"],
            "Type": a["subtype"]
        })  
    
    return pd.DataFrame(rows)
    


def append_data_deduplicate(transactions_df, account_df):
    if os.path.exists(EXCEL_FILE_PATH):
        print("It Exists!")
        with pd.ExcelWriter(EXCEL_FILE_PATH) as writer:
            current_t_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="Transactions")
            t_df = pd.concat([current_t_df, transactions_df], ignore_index=True)
            t_df.drop_duplicates(subset=["Transaction Id"], inplace=True)
            t_df.to_excel(writer, sheet_name="Transactions")

            current_a_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="Account Info")
            a_df = pd.concat([current_a_df, account_df], ignore_index=True)
            a_df.drop_duplicates(subset=["account_id"], inplace=True)
            a_df.to_excel(writer, sheet_name="Account Info")
    else:
        with pd.ExcelWriter(EXCEL_FILE_PATH) as writer:
            transactions_df.to_excel(writer, sheet_name="Transactions")
            account_df.to_excel(writer, sheet_name="Account Info")



# Main function to run
if __name__ == "__main__":
    # Fetch Transactional data
    [transactions, accounts] = fetchData()

    transaction_df = parse_transactions(transactions, accounts)
    account_df = parse_account_data(accounts)

    # Append data to excel file
    append_data_deduplicate(transaction_df, account_df)
