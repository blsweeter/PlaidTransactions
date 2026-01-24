# PlaidTransactions
Use Plaid API to retrieve bank and card transactions. Will clean and export transactions on excel file.

To get Access code:


To run:
- Clone repository on local machine
- Create a copy of the .env.example file called .env
- Fill in ClientID and Sandbox Secret information
- Create python virtual environment
- Install plaid-python, pandas, openpyxl, python-dotenv, requests ('pip install plaid-python pandas openpyxl python-dotenv requests') [See requirements.txt]
- Run get_access_token.py
- Paste the access_token in the new access_token.txt into the .env file
- Fill in rest of information in .env file
- Run run.py
