import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import sys
import os

# --- Update this import to include the new LLM wrapper functions from agent_core ---
from agent_core import (
    clean_text,
    send_email_collective,
    extract_emails,
    read_file_content,
    SENDER_EMAIL,
    get_llm_generated_subject,   # Calling wrapper in agent_core
    get_llm_reformatted_minutes  # Calling wrapper in agent_core
)
print("meeting-agent.py: agent_core imported. GUI initializing...") # DEBUG


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
        file_frame = tk.Frame(master)
        file_frame.pack(pady=10)

        tk.Label(file_frame, text="File Path:").pack(side=tk.LEFT, padx=5)
        self.file_path_entry = tk.Entry(file_frame, width=50)
        self.file_path_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_button = tk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.load_button = tk.Button(file_frame, text="Load from File", command=self.load_minutes_from_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        tk.Label(master, text="Meeting Minutes:").pack(pady=5)
        self.minutes_text_widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20)
        self.minutes_text_widget.pack(pady=5, padx=10)

        self.dispatch_button = tk.Button(master, text="Dispatch Meeting Minutes", command=self.dispatch_minutes, height=2, width=30)
        self.dispatch_button.pack(pady=15)

        tk.Label(master, text="Agent Log:").pack(pady=5)
        self.log_text_widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20, state='disabled')
        self.log_text_widget.pack(pady=5, padx=10)
        
        self.old_stdout = sys.stdout
        sys.stdout = TextRedirector(self.log_text_widget, "stdout")
        print("meeting-agent.py: MeetingDispatcherApp initialized. Logging redirected.") # DEBUG

    def log_message(self, message):
        """Helper to print messages to the GUI log with extra spacing."""
        if self.log_text_widget.get(1.0, tk.END).strip():
            print("\n" + message)
        else:
            print(message)

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Meeting Minutes File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, filepath)
            self.log_message(f"Selected file: {os.path.basename(filepath)}")
            self.load_minutes_from_file() 

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
        print("meeting-agent.py: Dispatch button clicked. Starting processing.") # DEBUG to console
        
        raw_minutes = self.minutes_text_widget.get(1.0, tk.END).strip()

        if not raw_minutes:
            self.log_message("Error: No meeting minutes provided in the text area. Please load a file or paste content.")
            return

        cleaned_minutes = clean_text(raw_minutes)
        self.log_message("Minutes cleaned and normalized.")

        recipient_emails_extracted = extract_emails(cleaned_minutes) 

        if not recipient_emails_extracted:
            self.log_message("⚠️ No email addresses found in the provided minutes. Cannot send emails.")
            return

        primary_to_email = SENDER_EMAIL
        cc_recipients = [email for email in recipient_emails_extracted if email.lower() != primary_to_email.lower()]

        if not cc_recipients:
            self.log_message("Found email addresses, but they all belong to the sender. No one to CC.")
            if messagebox.askyesno("Confirm Dispatch",
                                   f"No other recipients found besides sender ({primary_to_email}). Send to self?\n"
                                   f"Subject: AI Agent Email - Meeting Minutes"):
                # Call LLM-generated content even for sender-only
                self.log_message("Requesting AI to generate subject and reformat minutes (sender only)...") # GUI log
                print("meeting-agent.py: About to call LLM functions (sender only).") # DEBUG
                
                meeting_subject = get_llm_generated_subject(cleaned_minutes)
                detailed_description = get_llm_reformatted_minutes(cleaned_minutes)
                self.log_message("AI generation complete.") # GUI log
                print("meeting-agent.py: LLM functions returned (sender only).") # DEBUG

                email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"

                if send_email_collective(primary_to_email, [], meeting_subject, email_body):
                    self.log_message("✅ Email sent successfully to sender only.")
                else:
                    self.log_message("❌ Failed to send email to sender.")
            else:
                self.log_message("🚫 Email sending cancelled by user.")
            return

        self.log_message(f"Found {len(recipient_emails_extracted)} unique email(s) in total.")
        self.log_message(f"Primary Recipient (To): {primary_to_email}")
        self.log_message(f"CC Recipients ({len(cc_recipients)}): {', '.join(cc_recipients[:5])}{'...' if len(cc_recipients) > 5 else ''}")

        # --- LLM Integration: Get subject and reformatted minutes ---
        self.log_message("Requesting AI to generate subject and reformat minutes...") # GUI log
        print("meeting-agent.py: About to call LLM functions via agent_core.") # DEBUG to console

        meeting_subject = get_llm_generated_subject(cleaned_minutes)
        detailed_description = get_llm_reformatted_minutes(cleaned_minutes)
        self.log_message("AI generation complete.") # GUI log
        print("meeting-agent.py: LLM functions returned.") # DEBUG to console

        email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"


        if messagebox.askyesno("Confirm Dispatch", 
                               f"Do you want to send meeting minutes to {primary_to_email} (To) and {len(cc_recipients)} (Cc) recipient(s)?\n"
                               f"Subject: {meeting_subject}"):

            self.log_message("Initiating collective email send...")
            if send_email_collective(primary_to_email, cc_recipients, meeting_subject, email_body):
                self.log_message("✅ Collective email sent successfully to all recipients.")
            else:
                self.log_message("❌ Failed to send collective email.")
        else:
            self.log_message("🚫 Email sending cancelled by user.")
            
        self.log_message("--- Dispatch Process Complete ---")


# --- Main Application Execution ---
if __name__ == "__main__":
    print("meeting-agent.py: Script starting.") # DEBUG
    root = tk.Tk()
    app = MeetingDispatcherApp(root)
    root.mainloop()
    print("meeting-agent.py: GUI loop ended.") # DEBUG