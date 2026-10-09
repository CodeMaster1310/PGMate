# PGMate — Smart PG Expense & Complaint Manager

A small full-stack Python college project using Flask, HTML/CSS, and JSON files. **No database is used.**

## Features
- PG member management
- Expense tracking and deletion
- Equal expense share estimate
- Complaint submission and status updates
- Category and monthly expense reports
- Dashboard with an illustrative PG Health Score

## Run in PyCharm (Windows)
1. Extract the ZIP and open the `PGMate` folder in PyCharm.
2. Open the PyCharm Terminal.
3. Create a virtual environment: `python -m venv .venv`
4. Activate it: `.venv\\Scripts\\activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Run `app.py` using PyCharm's Run button or `python app.py`.
7. Open `http://127.0.0.1:5000` in your browser.

JSON files in `data/` are created automatically if missing.

## JSON storage and cloud persistence warning
The app writes to JSON files under `data/` by default. A typical Render web service has an ephemeral filesystem, so changes can be lost after a restart, redeploy, or instance replacement. This version is fine for a demonstration, but do not store important real-world records in it.

To retain JSON data without a database, attach a persistent disk if your Render plan supports it and set environment variable `PGMATE_DATA_DIR` to the mounted path (for example `/var/data/pgmate`). Check Render's current plan support and pricing before relying on this. Keep this project to one web instance: concurrent multi-instance JSON writes are not safe.

## Security note
This classroom project has no login/authentication. Do not enter sensitive personal details or use it as a private financial service.
