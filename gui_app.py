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

        # --- NEW: Frame for adding recipients manually ---
        recipients_frame = tk.Frame(master)
        recipients_frame.pack(pady=(10, 0), padx=10, fill='x')

        tk.Label(recipients_frame, text="Additional CC Recipients (comma-separated):").pack(side=tk.LEFT, padx=(0, 5))
        self.additional_recipients_entry = tk.Entry(recipients_frame, relief="solid", borderwidth=1)
        self.additional_recipients_entry.pack(side=tk.LEFT, expand=True, fill='x')

        
        # --- FIX: Re-implementing the dispatch button as a styled Label ---
        dispatch_bg_color = "#28a745"  # The green color you wanted
        dispatch_active_color = "#218838" # A darker green for hover/click

        
        self.dispatch_button = tk.Label(
            master,
            text="Dispatch Meeting Minutes",
            fg="white",
            bg=dispatch_bg_color,
            relief="raised",
            borderwidth=2,
            height=2,
            width=30
        )
         
        self.dispatch_button.pack(pady=15)
        # Add all the responsive bindings
        self.dispatch_button.bind("<Enter>", lambda e: e.widget.config(bg=dispatch_active_color))
        self.dispatch_button.bind("<Leave>", lambda e: e.widget.config(bg=dispatch_bg_color))
        self.dispatch_button.bind("<Button-1>", lambda e: e.widget.config(relief="sunken"))
        self.dispatch_button.bind("<ButtonRelease-1>", lambda e: (
            e.widget.config(relief="raised"),
            self.dispatch_minutes()
        ))

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
        # ... (The first part of the function is the same) ...
        preview_window = tk.Toplevel(self.master)
        preview_window.title("Email Preview - Confirm Dispatch")
        preview_window.transient(self.master)
        preview_window.grab_set()

        tk.Label(preview_window, text=f"Subject: {subject}", font=('Arial', 12, 'bold'), wraplength=550).pack(pady=10, padx=10)
        tk.Label(preview_window, text="Meeting Minutes Body:").pack(pady=5, padx=10, anchor='w')
        preview_text_widget = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD, width=80, height=20, relief="solid", borderwidth=1)
        preview_text_widget.pack(pady=5, padx=10, ipadx=5, ipady=5)
        preview_text_widget.insert(tk.END, body_content)
        preview_text_widget.bind("<Key>", lambda e: "break")

        button_frame = tk.Frame(preview_window)
        button_frame.pack(pady=15)

        # --- UPDATED BUTTONS WITH BETTER FEEDBACK ---

        # Send "Button" as a Label
        send_label = tk.Label(
            button_frame, text="Send Email", fg="white", bg="#4CAF50",
            relief="raised", borderwidth=2, cursor="hand2"  # Add hand cursor
        )
        send_label.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        send_label.bind("<Enter>", lambda e: e.widget.config(bg="#45a049"))
        send_label.bind("<Leave>", lambda e: e.widget.config(bg="#4CAF50"))
        send_label.bind("<Button-1>", lambda e: e.widget.config(relief="sunken"))
        send_label.bind("<ButtonRelease-1>", lambda e: (
            e.widget.config(relief="raised"),
            self._on_preview_action(preview_window, True)
        ))

        # Save "Button" as a Label
        save_label = tk.Label(
            button_frame, text="Save Minutes", fg="white", bg="#2196F3",
            relief="raised", borderwidth=2, cursor="hand2"  # Add hand cursor
        )
        save_label.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        save_label.bind("<Enter>", lambda e: e.widget.config(bg="#1976D2"))
        save_label.bind("<Leave>", lambda e: e.widget.config(bg="#2196F3"))
        save_label.bind("<Button-1>", lambda e: e.widget.config(relief="sunken"))
        save_label.bind("<ButtonRelease-1>", lambda e: (
            e.widget.config(relief="raised"),
            self._save_minutes_to_file(subject, body_content)
        ))

        # Cancel "Button" as a Label
        cancel_label = tk.Label(
            button_frame, text="Cancel", fg="white", bg="#F44336",
            relief="raised", borderwidth=2, cursor="hand2"  # Add hand cursor
        )
        cancel_label.pack(side=tk.LEFT, padx=10, ipady=5, ipadx=10)
        cancel_label.bind("<Enter>", lambda e: e.widget.config(bg="#da190b"))
        cancel_label.bind("<Leave>", lambda e: e.widget.config(bg="#F44336"))
        cancel_label.bind("<Button-1>", lambda e: e.widget.config(relief="sunken"))
        cancel_label.bind("<ButtonRelease-1>", lambda e: (
            e.widget.config(relief="raised"),
            self._on_preview_action(preview_window, False)
        ))

        preview_window.protocol("WM_DELETE_WINDOW", lambda: self._on_preview_action(preview_window, False))
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
            
    # --- ADD THIS NEW METHOD ---
    def _reset_ui(self):
        """Clears all input fields and the agent log for a fresh start."""
        # Clear text entry widgets
        self.file_path_entry.delete(0, tk.END)
        self.additional_recipients_entry.delete(0, tk.END)
        
        # Clear the main text areas
        self.minutes_text_widget.delete(1.0, tk.END)
        self.log_text_widget.delete(1.0, tk.END)
            
    def dispatch_minutes(self):
        self.log_message("\n--- Starting Meeting Minutes Dispatch ---")
        raw_minutes = self.minutes_text_widget.get(1.0, tk.END).strip()
        if not raw_minutes:
            self.log_message("Error: No meeting minutes provided in the text area.")
            return

        cleaned_minutes = clean_text(raw_minutes)

        # Get emails from both sources
        extracted_emails = set(extract_emails(cleaned_minutes))
        if extracted_emails:
            self.log_message(f"Found {len(extracted_emails)} recipient(s) in minutes text.")

        additional_emails_str = self.additional_recipients_entry.get().strip()
        manual_emails = set()
        if additional_emails_str:
            manual_emails = set(email.strip() for email in additional_emails_str.split(',') if email.strip())
            self.log_message(f"Found {len(manual_emails)} manually added recipient(s).")

        all_recipients_set = extracted_emails.union(manual_emails)
        self.log_message(f"Total unique recipients: {len(all_recipients_set)}")

        if not all_recipients_set:
            self.log_message("⚠️ No email addresses provided in the minutes or the recipients field.")
            return

        primary_to_email = SENDER_EMAIL
        cc_recipients = [email for email in all_recipients_set if email.lower() != primary_to_email.lower()]

        self.log_message("Requesting AI to generate subject and reformat minutes...")
        meeting_subject = get_llm_generated_subject(cleaned_minutes)
        detailed_description = get_llm_reformatted_minutes(cleaned_minutes)
        self.log_message("AI generation complete.")

        email_body = f"Dear Team,\n\nPlease find the meeting minutes below:\n\n{detailed_description}\n\nBest regards,\nYour Meeting Dispatcher Agent"
        self.show_email_preview(meeting_subject, detailed_description)

        if not self.preview_confirmed:
            self.log_message("🚫 Email sending cancelled by user from preview.")
            return

        # --- ADDED BACK: Log the final recipient list ---
        self.log_message(f"Primary Recipient (To): {primary_to_email}")
        if cc_recipients:
            # Display up to 5 CC recipients for readability, then add '...'
            cc_display_list = cc_recipients[:5]
            additional_cc_count = len(cc_recipients) - 5
            
            log_str = f"CC Recipients ({len(cc_recipients)}): {', '.join(cc_display_list)}"
            if additional_cc_count > 0:
                log_str += f", and {additional_cc_count} more..."
            self.log_message(log_str)
        else:
            self.log_message("No other recipients to CC.")
        # ---------------------------------------------------
        
        self.log_message("Initiating email send...")
        if send_email_collective(primary_to_email, cc_recipients, meeting_subject, email_body):
            self._reset_ui()
            self.log_message("✅ Collective email sent successfully.")
            self.log_message("--- Dispatch Process Complete ---")
        else:
            self.log_message("❌ Failed to send collective email.")


# --- Main Application Execution ---
if __name__ == "__main__":
    print("Script started.")
    root = tk.Tk()
    app = MeetingDispatcherApp(root)
    root.mainloop()