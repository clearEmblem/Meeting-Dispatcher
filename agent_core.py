import sys
import os
import re
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# --- NEW: Import LLM functions from your ai_service.py file ---
from llm_service import generate_subject_with_llm, reformat_minutes_with_llm
print("agent_core.py: ai_service imported.") # DEBUG

# --- Configuration (Loaded only once per process) ---
load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("GMAIL_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Validate that credentials were loaded
if not SENDER_EMAIL or not APP_PASSWORD:
    print("FATAL ERROR: SENDER_EMAIL or GMAIL_PASSWORD not found in .env file. Please check your .env file.")
    print("Ensure your .env file looks like this:\nSENDER_EMAIL=\"your.email@gmail.com\"\nGMAIL_PASSWORD=\"your_16_digit_app_password\"")
    sys.exit(1)

# --- Helper Functions (Core Agent Logic) ---

def clean_text(text):
    """Cleans the input text by replacing non-breaking spaces and normalizing other whitespace."""
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def send_email_collective(to_email, cc_emails, subject, body):
    """
    Sends a single email with a primary recipient and multiple CC recipients,
    using plain text.
    """
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email

        if cc_emails:
            msg['Cc'] = ", ".join(cc_emails)

        all_recipients = [to_email] + list(cc_emails)
        all_recipients = list(set(all_recipients))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, all_recipients, msg.as_string())

        print(f"✅ Email sent successfully to {to_email} (To) and {len(cc_emails)} (Cc) recipients.")
        return True
    except Exception as e:
        print(f"❌ Failed to send collective email: {e}")
        return False
    
def extract_emails(text):
    """Extracts all unique email addresses from a given text using regex."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return list(set(re.findall(email_pattern, text)))

def read_file_content(filepath):
    """Reads content from a .txt file. Placeholder for PDF/DOCX."""
    if not os.path.exists(filepath):
        print(f"❌ Error: File not found at '{filepath}'")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"❌ Error reading file '{filepath}': {e}")
        return None

# --- Wrapper functions for LLM calls from ai_service.py ---
def get_llm_generated_subject(minutes_text):
    """
    Calls the AI service (ai_service.py) to generate a meeting subject.
    This function acts as a bridge.
    """
    print("agent_core.py: get_llm_generated_subject wrapper called.") # DEBUG
    return generate_subject_with_llm(minutes_text)

def get_llm_reformatted_minutes(minutes_text):
    """
    Calls the AI service (ai_service.py) to reformat meeting minutes.
    This function acts as a bridge.
    """
    print("agent_core.py: get_llm_reformatted_minutes wrapper called.") # DEBUG
    return reformat_minutes_with_llm(minutes_text)