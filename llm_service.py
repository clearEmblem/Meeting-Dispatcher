import os
from dotenv import load_dotenv
from google import genai 
from google.genai import types 
import sys
import pprint # <--- NEW IMPORT for pretty printing
import traceback # <--- NEW IMPORT for full tracebacks

# --- Configuration (Loaded only once when this module is imported) ---
load_dotenv()
print("ai_service.py: .env loaded.") 
sys.stdout.flush() 

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    
_client = genai.Client()
print("ai_service.py: Gemini Client instantiated.")
sys.stdout.flush()


# --- LLM Helper Functions ---

def generate_subject_with_llm(minutes_text):
    sys.stdout.flush()
    try:
        subject_prompt = (
            "Provide an appropriate email subject title for the following meeting minutes. "
            "The response should be less than 5 words maximum: "
            f"\n\n{minutes_text}"
        )

        sys.stdout.flush()
        
        response = _client.models.generate_content(
            model="gemini-2.5-pro", 
            contents=subject_prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=500),
                temperature=0.2       
            ),
        )
        
        sys.stdout.flush()
        
        subject = response.text.strip().replace('**', '') 
        return subject
    except Exception as e:
        print(f"❌ ai_service.py: Error in subject generation: {type(e).__name__}: {e}")
        traceback.print_exc(file=sys.stdout) # <--- PRINT FULL TRACEBACK TO CONSOLE
        sys.stdout.flush()
        return "AI Agent Email - Meeting Minutes (LLM Error)"

def reformat_minutes_with_llm(minutes_text):
    sys.stdout.flush()
    try:
        minutes_reformat_prompt = (
            "You are an expert administrative assistant specializing in transforming raw, informal, or unpolished meeting notes into professional, structured, and highly readable meeting minutes. Your goal is to improve clarity, organization, and conciseness while accurately preserving all factual information, key discussions, decisions made, and assigned action items."
            "\n\nStrictly adhere to the following formatting and content guidelines:"
            "\n1. Input Quality: Assume the provided notes might be raw, conversational, or taken quickly, possibly lacking formal structure or consistent formatting."
            "\n2. Output Purpose: The final output must be a stand-alone, formal meeting minutes document."
            "\n3. Structure: Organize the minutes using clear, professional headings. Recommended headings include:"
            "\n4. NEVER start the response with 'Meeting Minutes'. Always start the response with Meeting Details"
            "\n'Meeting Details' (for Date, Time, Location, etc.)"
            "\n'Attendees'"
            "\n'Discussion Summary'"
            "\n'Decisions Made'"
            "\n'Action Items'"
            "\n'Next Meeting' (if applicable)"
            "\n4. Content Transformation:"
            "\n  - Condense conversational exchanges into concise discussion points."
            "\n  - Clearly delineate decisions and action items."
            "\n  - Ensure all responsibilities and due dates for action items are explicit."
            "\n  - CRITICAL: Identify and REMOVE all email addresses from the output. Ensure they are not present in the 'Attendees' list or any other section of the reformatted minutes."
            "\n5. Formatting:"
            "\n  - Use bullet points for lists (e.g., attendees, discussion points, action items)."
            "\n  - Ensure distinct paragraphs using double newlines for proper vertical spacing."
            "\n  - For all bulleted or sub-items, use exactly 4 spaces for indentation." 
            "\n6. Tone & Style:"
            "\n  - Maintain a neutral, objective, and formal tone throughout."
            "\n  - Avoid any conversational filler, slang, or subjective commentary."
            # "\n  - CRITICAL: Output MUST be plain text. Do NOT use any Markdown formatting (e.g., no asterisks for bolding, hash symbols for headings, backticks for code blocks). Use only natural line breaks and spaces for formatting."
            # "\n  - CRITICAL: Do NOT include any email-specific framing (e.g., 'Dear Team', 'Here are the minutes', 'Best regards', 'Subject:'). Provide only the reformatted meeting minutes content."
            f"\n\nHere are the raw meeting notes to be transformed into professional minutes:\n{minutes_text}"
        )

        sys.stdout.flush()
        
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=minutes_reformat_prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=500),
                temperature=0.3       
            ),
        )
        

        sys.stdout.flush()
        
        reformatted_minutes = response.text.strip().replace('**', '') 
        return reformatted_minutes
    except Exception as e:
        print(f"❌ ai_service.py: Error reformatting minutes: {type(e).__name__}: {e}")
        traceback.print_exc(file=sys.stdout) # <--- PRINT FULL TRACEBACK TO CONSOLE
        sys.stdout.flush()
        return minutes_text