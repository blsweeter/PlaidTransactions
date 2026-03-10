# Project Structure

plaid-app/
├── .env                        # Credentials (never commit this)
├── docker-compose.yml          # Spins up backend + frontend together
├── data/                       # Excel output files written here (auto-created)
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                  # Flask server (Plaid API + transaction logic)
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        └── App.jsx             # React app with Plaid Link button

# How to run
1. Fill in .env with your real Plaid credentials
2. docker-compose up --build  (Install docker if not found)
3. Open http://localhost:3000
4. Click "Connect Bank" → complete Plaid Link flow
5. Click "Fetch Transactions" → Excel file saved to ./data/transactions.xlsx