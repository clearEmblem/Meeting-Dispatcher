import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox # Import messagebox for future confirmation popups
from agent_core import clean_text, send_email_collective, extract_emails, read_file_content
import os
import sys
from dotenv import load_dotenv
from agent_core import *

load_dotenv()


# --- LLM Configuration (Placeholder for now) ---
# You'll need to uncomment and fill this out when we get to LLM integration
# import google.generativeai as genai
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE") # Get from .env or use placeholder
# if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
#     print("WARNING: Gemini API key is not set. LLM features will not work.")
# else:
#     genai.configure(api_key=GEMINI_API_KEY)


# --- Text Redirector Class (for GUI logging) ---
class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str_to_write):
        self.widget.config(state='normal')
        self.widget.insert(tk.END, str_to_write, (self.tag,))
        self.widget.see(tk.END)
        self.widget.config(state='disabled')

    def flush(self):
        pass

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
        self.log_text_widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20, state='disabled') # <-- HEIGHT CHANGED HERE
        self.log_text_widget.pack(pady=5, padx=10)
        
        # Redirect print statements to the log widget
        self.old_stdout = sys.stdout
        sys.stdout = TextRedirector(self.log_text_widget, "stdout")

    def log_message(self, message):
        """Helper to print messages to the GUI log with extra spacing."""
        # Add a newline before the message to create space, but not on the very first message or if it's already empty
        if self.log_text_widget.get(1.0, tk.END).strip(): # Check if log is not empty
            print("\n" + message) # Print with leading newline
        else:
            print(message) # Print normally if log is empty


    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Meeting Minutes File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, filepath)
            self.log_message(f"Selected file: {os.path.basename(filepath)}")

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
            
    def dispatch_minutes(self):
        self.log_message("\n--- Starting Meeting Minutes Dispatch ---")
        
        raw_minutes = self.minutes_text_widget.get(1.0, tk.END).strip()

        if not raw_minutes:
            self.log_message("Error: No meeting minutes provided in the text area.")
            return

        cleaned_minutes = clean_text(raw_minutes)
        self.log_message("Minutes cleaned and normalized.")

        recipient_emails_extracted = extract_emails(cleaned_minutes) 

        if not recipient_emails_extracted:
            self.log_message("⚠️ No email addresses found in the provided minutes. Cannot send emails.")
            return

        # Determine the primary recipient (yourself) and CC recipients
        primary_to_email = SENDER_EMAIL
        
        # Remove your own email from the CC list to avoid sending to yourself twice
        cc_recipients = [email for email in recipient_emails_extracted if email.lower() != primary_to_email.lower()]

        if not cc_recipients:
            self.log_message("Found email addresses, but they all belong to the sender. No one to CC.")
            # Option: If no CCs, you could still send it to yourself (To: SENDER_EMAIL, Cc: empty)
            if messagebox.askyesno("Confirm Dispatch",
                                   f"No other recipients found besides sender ({primary_to_email}). Send to self?\n"
                                   f"Subject: AI Agent Email - Meeting Minutes"):
                if send_email_collective(primary_to_email, [], "AI Agent Email - Meeting Minutes", email_body): # Pass empty list for CC
                    self.log_message("✅ Email sent successfully to sender only.")
                else:
                    self.log_message("❌ Failed to send email to sender.")
            else:
                self.log_message("🚫 Email sending cancelled by user.")
            return

        self.log_message(f"Found {len(recipient_emails_extracted)} unique email(s) in total.")
        self.log_message(f"Primary Recipient (To): {primary_to_email}")
        self.log_message(f"CC Recipients ({len(cc_recipients)}): {', '.join(cc_recipients[:5])}{'...' if len(cc_recipients) > 5 else ''}") # Show first 5

        # ... (subject and body generation remains the same) ...
        meeting_subject = "AI Agent Email - Meeting Minutes" 
        detailed_description = cleaned_minutes
        email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"


        # Ask for confirmation before sending
        if messagebox.askyesno("Confirm Dispatch", 
                               f"Do you want to send meeting minutes to {primary_to_email} (To) and {len(cc_recipients)} (Cc) recipient(s)?\n" # <--- UPDATED MESSAGE
                               f"Subject: {meeting_subject}"):

            self.log_message("Initiating collective email send...\n")
            # Call the collective sending function, passing the CC list
            if send_email_collective(primary_to_email, cc_recipients, meeting_subject, email_body): # <--- PASSING CC LIST
                self.log_message("✅ Collective email sent successfully to all recipients.")
            else:
                self.log_message("❌ Failed to send collective email.")
        else:
            self.log_message("🚫 Email sending cancelled by user.")
            
        self.log_message("--- Dispatch Process Complete ---")

if __name__ == "__main__":
    root = tk.Tk()
    app = MeetingDispatcherApp(root)
    root.mainloop()