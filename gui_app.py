import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import sys
import os
import re

from agent_core import (
    clean_text,
    send_email_collective,
    extract_emails,
    read_file_content,
    SENDER_EMAIL,
    get_llm_generated_subject,
    get_llm_reformatted_minutes
)

print("meeting-agent.py: agent_core imported. GUI initializing...")


# --- Text Redirector Class (for GUI logging) ---
class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str_to_write):
        # --- FIX: No longer need to change state ---
        self.widget.insert(tk.END, str_to_write, (self.tag,))
        self.widget.see(tk.END)

    def flush(self):
        pass


# --- GUI Application Class ---
class MeetingDispatcherApp:
    def __init__(self, master):
        self.master = master
        master.title("Meeting Dispatcher AI Agent")

        self.preview_confirmed = False

        # --- Widgets ---
        file_frame = tk.Frame(master)
        file_frame.pack(pady=10)

        tk.Label(file_frame, text="File Path:").pack(side=tk.LEFT, padx=5)
        self.file_path_entry = tk.Entry(file_frame, width=50, relief="solid", borderwidth=1)
        self.file_path_entry.pack(side=tk.LEFT, padx=5, ipadx=4, ipady=2)

        self.browse_button = tk.Button(file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        self.load_button = tk.Button(file_frame, text="Load from File", command=self.load_minutes_from_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        tk.Label(master, text="Meeting Minutes:").pack(pady=5)
        self.minutes_text_widget = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=90, height=20, relief="solid", borderwidth=1)
        self.minutes_text_widget.pack(pady=5, padx=10, ipadx=5, ipady=5)

        self.dispatch_button = tk.Button(master, text="Dispatch Meeting Minutes", command=self.dispatch_minutes, height=2, width=30)
        self.dispatch_button.pack(pady=15)

        tk.Label(master, text="Agent Log:").pack(pady=5)

        self.log_text_widget = scrolledtext.ScrolledText(
            master,
            wrap=tk.WORD,
            width=90,
            height=20,
            relief="solid",
            borderwidth=1,
            bg="#F0F0F0",
            fg="black"
        )
        self.log_text_widget.pack(pady=5, padx=10, ipadx=5, ipady=5)
        
        # --- FIX: Make widget read-only with a binding instead of disabling it ---
        # This keeps the widget scrollable by the user.
        self.log_text_widget.bind("<Key>", lambda e: "break")
        
        self.old_stdout = sys.stdout
        # The TextRedirector no longer needs to toggle the widget's state
        sys.stdout = TextRedirector(self.log_text_widget, "stdout")
        print("meeting-agent.py: MeetingDispatcherApp initialized. Logging redirected.")


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

    def show_email_preview(self, subject, body_content):
        """Creates the popup window to preview the email and its options."""
        print("meeting-agent.py: show_email_preview called. Creating Toplevel window...")
        sys.stdout.flush()

        preview_window = tk.Toplevel(self.master)
        preview_window.title("Email Preview - Confirm Dispatch")
        preview_window.transient(self.master)
        preview_window.grab_set()

        print("meeting-agent.py: Toplevel window created. Adding widgets...")
        sys.stdout.flush()

        tk.Label(preview_window, text=f"Subject: {subject}", font=('Arial', 12, 'bold'), wraplength=550).pack(pady=10, padx=10)

        tk.Label(preview_window, text="Meeting Minutes Body:").pack(pady=5, padx=10, anchor='w')
        preview_text_widget = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD, width=80, height=20, relief="solid", borderwidth=1)
        preview_text_widget.pack(pady=5, padx=10, ipadx=5, ipady=5)
        preview_text_widget.insert(tk.END, body_content)
        preview_text_widget.bind("<Key>", lambda e: "break")

        print("meeting-agent.py: Preview widgets packed. Adding buttons...")
        sys.stdout.flush()

        # This frame holds all the buttons
        button_frame = tk.Frame(preview_window)
        button_frame.pack(pady=15)

        # Send "Button" as a Label
        send_label = tk.Label(
            button_frame, text="Send Email", fg="white", bg="#4CAF50",
            relief="raised", borderwidth=2
        )
        send_label.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        send_label.bind("<Enter>", lambda e: e.widget.config(bg="#45a049"))
        send_label.bind("<Leave>", lambda e: e.widget.config(bg="#4CAF50"))
        send_label.bind("<Button-1>", lambda e: self._on_preview_action(preview_window, True))

        # Save "Button" as a Label
        save_label = tk.Label(
            button_frame, text="Save Minutes", fg="white", bg="#2196F3",
            relief="raised", borderwidth=2
        )
        save_label.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        save_label.bind("<Enter>", lambda e: e.widget.config(bg="#1976D2"))
        save_label.bind("<Leave>", lambda e: e.widget.config(bg="#2196F3"))
        save_label.bind("<Button-1>", lambda e: self._save_minutes_to_file(subject, body_content))

        # Cancel "Button" as a Label
        cancel_label = tk.Label(
            button_frame, text="Cancel", fg="white", bg="#F44336",
            relief="raised", borderwidth=2
        )
        cancel_label.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        cancel_label.bind("<Enter>", lambda e: e.widget.config(bg="#da190b"))
        cancel_label.bind("<Leave>", lambda e: e.widget.config(bg="#F44336"))
        cancel_label.bind("<Button-1>", lambda e: self._on_preview_action(preview_window, False))

        preview_window.protocol("WM_DELETE_WINDOW", lambda: self._on_preview_action(preview_window, False))

        print("meeting-agent.py: Preview window ready. Waiting for user action...")
        sys.stdout.flush()

        self.master.wait_window(preview_window)

    def _on_preview_action(self, window, confirmed):
        self.preview_confirmed = confirmed
        window.destroy()
    
    def _save_minutes_to_file(self, subject, minutes_content):
        """Saves the provided meeting minutes content to a user-selected file."""
        try:
            # Sanitize the subject to create a valid default filename
            default_filename = re.sub(r'[\\/*?:"<>|]', "", subject)
            default_filename = f"{default_filename.replace(' ', '_')}.txt"

            filepath = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                title="Save AI-Generated Minutes"
            )

            # If the user cancels the dialog, filepath will be empty
            if not filepath:
                self.log_message("File save cancelled by user.")
                return

            with open(filepath, 'w', encoding='utf-8') as f:
                # Add a header to the file for context
                file_header = f"Subject: {subject}\n"
                file_header += "=" * (len(subject) + 9) + "\n\n"
                f.write(file_header)
                f.write(minutes_content)

            self.log_message(f"✅ Minutes successfully saved to: {os.path.basename(filepath)}")

        except Exception as e:
            self.log_message(f"❌ Error saving file: {e}")
            messagebox.showerror("Save Error", f"An error occurred while saving the file:\n{e}")
            
            
    def dispatch_minutes(self):
        self.log_message("\n--- Starting Meeting Minutes Dispatch ---")

        raw_minutes = self.minutes_text_widget.get(1.0, tk.END).strip()

        if not raw_minutes:
            self.log_message("Error: No meeting minutes provided in the text area. Please load a file or paste content.")
            return

        cleaned_minutes = clean_text(raw_minutes)

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
                self.log_message("Requesting AI to generate subject and reformat minutes (sender only)...")

                meeting_subject = get_llm_generated_subject(cleaned_minutes)
                detailed_description = get_llm_reformatted_minutes(cleaned_minutes)
                self.log_message("AI generation complete.")

                email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"

                self.show_email_preview(meeting_subject, detailed_description)
                if not self.preview_confirmed:
                    self.log_message("🚫 Email sending cancelled by user from preview.")
                    self.log_message("--- Dispatch Process Complete ---")
                    return

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

        self.log_message("Requesting AI to generate subject and reformat minutes...")

        meeting_subject = get_llm_generated_subject(cleaned_minutes)
        detailed_description = get_llm_reformatted_minutes(cleaned_minutes)
        self.log_message("AI generation complete.")

        email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"

        self.show_email_preview(meeting_subject, detailed_description)

        if not self.preview_confirmed:
            self.log_message("🚫 Email sending cancelled by user from preview.")
            self.log_message("--- Dispatch Process Complete ---")
            return

        self.log_message("Initiating collective email send...")
        if send_email_collective(primary_to_email, cc_recipients, meeting_subject, email_body):
            self.log_message("✅ Collective email sent successfully to all recipients.")
        else:
            self.log_message("❌ Failed to send collective email.")

        self.log_message("--- Dispatch Process Complete ---")


# --- Main Application Execution ---
if __name__ == "__main__":
    print("Script starting.")
    root = tk.Tk()
    app = MeetingDispatcherApp(root)
    root.mainloop()