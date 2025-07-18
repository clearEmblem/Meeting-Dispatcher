import tkinter as tk
from tkinter import filedialog, scrolledtext
import sys
import os # For file operations
import re # For email extraction
import smtplib # For sending emails
from email.mime.text import MIMEText # For email formatting
from datetime import datetime # For fallback subject if LLM not ready
from dotenv import load_dotenv

load_dotenv() # <--- NEW: This loads variables from .env into environment

# --- Configuration (Keep these at the top) ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL") # <--- NEW: Read from environment
APP_PASSWORD = os.getenv("GMAIL_PASSWORD") # <--- NEW: Read from environment
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

if not SENDER_EMAIL or not APP_PASSWORD:
    print("FATAL ERROR: SENDER_EMAIL or GMAIL_PASSWORD not found in .env file. Please check your .env file.")
    sys.exit(1) # Exit if essential credentials are missing
    
# --- LLM Configuration (Placeholder for now) ---
# You'll need to uncomment and fill this out when we get to LLM integration
# import google.generativeai as genai
# GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
# if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
#     print("WARNING: Gemini API key is not set. LLM features will not work.")
#     # This means you'll fallback to rule-based subject
# else:
#     genai.configure(api_key=GEMINI_API_KEY)


# --- Helper Functions (Copy your working ones here) ---

def clean_text(text):
    """Cleans the input text by replacing non-breaking spaces and normalizing other whitespace."""
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def send_email(receiver_email, subject, body):
    """Sends an email to a single recipient."""
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email 

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {receiver_email}: {e}") # This print will be redirected to GUI log
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

def get_meeting_subject_rule_based(minutes_text):
    """Fallback: Extracts a meeting subject using simple rule-based heuristics."""
    for line in minutes_text.split('\n'):
        if line.lower().startswith("meeting title:"):
            return line[len("meeting title:"):].strip()
        elif line.lower().startswith("subject:"):
            return line[len("subject:"):].strip()
    return "Meeting Minutes - " + datetime.now().strftime("%Y-%m-%d")


# --- Text Redirector Class (for GUI logging) ---
class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str_to_write): # Renamed 'str' to 'str_to_write' to avoid shadowing built-in str
        self.widget.config(state='normal')
        self.widget.insert(tk.END, str_to_write, (self.tag,))
        self.widget.see(tk.END)
        self.widget.config(state='disabled')

    def flush(self):
        pass # Required for file-like objects


# --- GUI Application Class ---
class MeetingDispatcherApp:
    def __init__(self, master):
        self.master = master
        master.title("Meeting Dispatcher AI Agent")

        # --- Widgets ---
        # Frame for file input
        file_frame = tk.Frame(master)
        file_frame.pack(pady=10)

        tk.Label(file_frame, text="File Path:").pack(side=tk.LEFT, padx=5)
        self.file_path_entry = tk.Entry(file_frame, width=50)
        self.file_path_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_button = tk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.load_button = tk.Button(file_frame, text="Load from File", command=self.load_minutes_from_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        # Minutes Input/Display Area
        tk.Label(master, text="Meeting Minutes:").pack(pady=5)
        self.minutes_text_widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20)
        self.minutes_text_widget.pack(pady=5, padx=10)

        # Dispatch Button
        self.dispatch_button = tk.Button(master, text="Dispatch Meeting Minutes", command=self.dispatch_minutes, height=2, width=30)
        self.dispatch_button.pack(pady=15)

        # Log/Output Area
        tk.Label(master, text="Agent Log:").pack(pady=5)
        self.log_text_widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=10, state='disabled')
        self.log_text_widget.pack(pady=5, padx=10)
        
        # Redirect print statements to the log widget
        self.old_stdout = sys.stdout # Store original stdout
        sys.stdout = TextRedirector(self.log_text_widget, "stdout")

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Meeting Minutes File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, filepath)
            self.log_message(f"Selected file: {os.path.basename(filepath)}") # Show only filename in log

    def load_minutes_from_file(self):
        filepath = self.file_path_entry.get()
        if not filepath:
            self.log_message("Please select a file path first.")
            return

        minutes_content = read_file_content(filepath)
        if minutes_content:
            self.minutes_text_widget.delete(1.0, tk.END)
            self.minutes_text_widget.insert(tk.END, minutes_content)
            self.log_message("Minutes loaded successfully from file.")
        else:
            self.log_message("Failed to load minutes from file. Check path or content.")
            
    def log_message(self, message):
        """Helper to print messages to the GUI log."""
        # Using print() will automatically redirect due to TextRedirector
        print(message) 

    def dispatch_minutes(self):
        self.log_message("\n--- Starting Meeting Minutes Dispatch ---")
        
        # Get content from the ScrolledText widget (can be typed or loaded from file)
        raw_minutes = self.minutes_text_widget.get(1.0, tk.END).strip()

        if not raw_minutes: # After stripping, if empty, then no content
            self.log_message("Error: No meeting minutes provided in the text area.")
            return

        cleaned_minutes = clean_text(raw_minutes)
        self.log_message("Minutes cleaned and normalized.")

        recipient_emails = extract_emails(cleaned_minutes)
        if not recipient_emails:
            self.log_message("⚠️ No email addresses found in the provided minutes. Cannot send emails.")
            return

        self.log_message(f"Found {len(recipient_emails)} unique email(s): {', '.join(recipient_emails)}")
        
        # --- Subject and Description Generation (Placeholder for LLM) ---
        # For now, using rule-based subject.
        meeting_subject = get_meeting_subject_rule_based(cleaned_minutes)
        self.log_message(f"Suggested Subject: '{meeting_subject}'")
        
        # For detailed description, for now just use the cleaned minutes
        detailed_description = cleaned_minutes 
        
        email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"

        self.log_message("Attempting to send emails...")
        all_sent_successfully = True
        for email in recipient_emails:
            # send_email function already handles printing success/failure messages
            if not send_email(email, meeting_subject, email_body):
                all_sent_successfully = False
        
        if all_sent_successfully:
            self.log_message("✅ All emails processed successfully.")
        else:
            self.log_message("❌ Some emails failed to send. Check the log above for details.")
        self.log_message("--- Dispatch Process Complete ---")


# --- Main Application Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = MeetingDispatcherApp(root)
    root.mainloop()