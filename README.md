# AI Comm Assistant — Streamlit Prototype (In-memory)

Files:
- app.py     => Streamlit dashboard (single-file entry)
- utils.py   => Email fetcher (IMAP + demo), analysis, reply generator
- .env       => Example env file for IMAP credentials
- requirements.txt

## Goal
Run a local Streamlit app (PowerShell friendly) that:
- Fetches emails from IMAP (if configured) or demo samples
- Filters subjects with keywords: Support, Query, Request, Help
- Analyzes sentiment (positive/negative/neutral) and urgency
- Prioritizes urgent emails and shows suggested replies

## Setup (PowerShell)
1. Create a virtual environment and install deps:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. (Optional) Configure IMAP in `.env` or set environment variables:
   ```
   IMAP_HOST=imap.example.com
   IMAP_USER=you@example.com
   IMAP_PASS=yourpassword
   IMAP_MAILBOX=INBOX
   ```
   For Gmail, enable IMAP and use an App Password or OAuth2. OAuth2 is not implemented here.
3. Run the Streamlit app:
   ```powershell
   streamlit run app.py
   ```
4. Use the sidebar to fetch demo emails or, if configured, fetch from IMAP.

## Notes
- This is an in-memory prototype: tickets and replies are stored in Streamlit session state only and will reset when the app restarts.
- For production, swap the in-memory store for SQLite or an external DB and replace template replies with an LLM (OpenAI) integration if desired.
