# Blockchain Banking System

Academic/demo project using Python Flask, SQLite and a custom blockchain.

## Features
- User registration and login
- Password hashing
- Simulated bank balance
- Deposit
- Withdrawal
- Account-to-account transfer
- Transaction history
- Blockchain explorer
- Blockchain integrity verification
- REST API for blockchain data

## Run

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create a virtual environment:

Windows:
python -m venv venv
venv\Scripts\activate

macOS/Linux:
python3 -m venv venv
source venv/bin/activate

4. Install dependencies:

pip install -r requirements.txt

5. Start:

python app.py

6. Open:
https://blockchain-banking-system.vercel.app/

The SQLite database `bank.db` is created automatically.

## Run with Docker

1. Install Docker Desktop.
2. Create a `.env` file and set a strong session secret:

	```env
	SECRET_KEY=replace-with-a-long-random-value
	```

3. Build and start the backend:

	```bash
	docker compose up --build
	```

4. Open http://127.0.0.1:5000.

SQLite is stored in the named `banking_data` volume and remains available when the container is recreated. Stop the service with `docker compose down`.

## Demo

Register two accounts. Deposit simulated money into account 1, then transfer some amount to account 2. Open Blockchain to see the blocks and Verify Blockchain to check integrity.

This is an educational simulation. It does not connect to real banks, cards, UPI, cryptocurrency networks or real money.
