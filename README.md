# BillSnap

BillSnap is a Streamlit-based receipt and bill-splitting assistant that helps users:
- upload or describe a receipt
- extract key bill details
- summarize totals and charges
- send the final summary via email

It uses Google Gemini for AI processing and Gmail for email delivery.

## Features
- Receipt image upload support
- Bill item extraction and totals
- Smart summary generation
- Email delivery of final bill summary
- Clean, user-friendly Streamlit interface

## Tech Stack
- Python
- Streamlit
- Google Gemini API
- Gmail SMTP
- HTML email formatting

## Project Structure
```text
bill-snap/
├── app.py
├── prompts.py
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── secrets.toml
└── README.md
my app URL:https://bill-snap-ccixymjgxnakz2cxs8pqk6.streamlit.app/
