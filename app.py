import os
import json
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions as google_exceptions

# --- 1. CONFIGURATION & SETUP ---
load_dotenv()

st.set_page_config(
    page_title="ProGlot AI | Ultimate Tutor",
    page_icon="🧠",
    layout="centered"
)

# --- CONSTANTS ---
# Token Optimization: Only keep the last 20 messages in the context window.
# Older messages remain on disk but are removed from the active memory.
MAX_HISTORY_LENGTH = 20 

# --- API SECURITY CHECK ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("🚨 CRITICAL ERROR: GEMINI_API_KEY not found in .env file.")
    st.stop()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error(f"API Connection Error: {e}")
    st.stop()

# --- 2. ROBUST FILE HANDLING ---

def get_history_filename(lang_code: str) -> str:
    """Generates a safe filename for the language history."""
    safe_name = "".join(c for c in lang_code if c.isalnum())
    return f"history_{safe_name}.json"

def save_history_safe(history, lang_code: str):
    """Saves the chat history to a JSON file (Atomic write simulation)."""
    filename = get_history_filename(lang_code)
    history_data = []
    try:
        for message in history:
            role = message.role
            parts_content = []
            for part in message.parts:
                if hasattr(part, "text"):
                    parts_content.append({"text": part.text})
                else:
                    parts_content.append({"text": str(part)})
            history_data.append({"role": role, "parts": parts_content})

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error: Could not save history - {e}")

def load_history_safe(lang_code: str):
    """Loads history from JSON with error handling for corrupted files."""
    filename = get_history_filename(lang_code)
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []
    except Exception as e:
        st.error(f"File read error: {e}")
        return []

def clear_current_history(lang_code: str):
    """Deletes the specific history file for the selected language."""
    filename = get_history_filename(lang_code)
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError:
            pass
    st.session_state.chat_session = None
    st.rerun()

# --- 3. DYNAMIC PROMPT CONFIGURATION ---

# Language Options mapping (Display Name -> File Code)
LANG_OPTIONS = {
    "Italian (İtalyanca) 🇮🇹": "It",
    "Spanish (İspanyolca) 🇪🇸": "Es",
    "German (Almanca) 🇩🇪": "De",
    "French (Fransızca) 🇫🇷": "Fr",
    "Japanese (Japonca) 🇯🇵": "Jp",
    "English (İngilizce) 🇬🇧": "En"
}

# Initialize default selection to prevent state errors
if "selected_label_key" not in st.session_state:
    st.session_state.selected_label_key = list(LANG_OPTIONS.keys())[0]

# --- 4. UI & STATE MANAGEMENT ---
with st.sidebar:
    st.header("⚙️ Control Panel")
    
    selected_label = st.selectbox(
        "Target Language", 
        list(LANG_OPTIONS.keys()),
        index=list(LANG_OPTIONS.keys()).index(st.session_state.selected_label_key)
    )
    # Persist selection
    st.session_state.selected_label_key = selected_label
    lang_code = LANG_OPTIONS[selected_label] 
    
    st.divider()
    st.caption(f"Model: `{MODEL_NAME}`")
    st.caption(f"Memory: Last {MAX_HISTORY_LENGTH} messages")
    
    # --- SAFETY SWITCH: CLEAR HISTORY ---
    with st.expander("🗑️ Clear History"):
        st.warning("This action cannot be undone!")
        confirm_text = st.text_input("Type 'delete' to confirm:", key="delete_confirm")
        if st.button("Confirm Delete", type="primary"):
            if confirm_text.strip().lower() == "delete":
                clear_current_history(lang_code)
            else:
                st.error("Please type 'delete'.")

    # --- FEATURE: EXPORT TO WEB ---
    st.divider()
    with st.expander("🚀 Export to Gemini Web"):
        st.info("If API quota is exceeded, copy this text to https://gemini.google.com to continue.")
        
        # Define the system prompt string for export
        export_system_instruction = f"""
You are 'ProGlot', an expert {selected_label} tutor for Turkish speakers.
IMPORTANT: This is an ongoing lesson. Remember previous mistakes and progress.

RULES:
1. Explain concepts in Turkish, but provide examples strictly in {selected_label}.
2. Correct mistakes gently and explain the 'Why' behind the rule.
3. End every response with an interactive question or exercise.
4. NEVER just provide the answer; keep the dialogue active.

TONE: Professional, Patient, Encouraging.
"""
        # Load FULL history from disk (not just the windowed memory)
        full_disk_history = load_history_safe(lang_code)
        
        export_text = f"SYSTEM INSTRUCTION:\n{export_system_instruction}\n\nCHAT HISTORY:\n"
        for msg in full_disk_history:
            r = "Model" if msg.get("role") == "model" else "Student"
            txt = msg.get("parts", [{}])[0].get("text", "")
            export_text += f"{r}: {txt}\n"
        
        export_text += "\n\n(Please continue from here)"
        st.code(export_text, language="text")

    st.markdown("---")
    if st.button("🔄 Refresh UI"):
        st.rerun()

# --- 5. MODEL LOGIC & INITIALIZATION ---

# System Instruction (Injected into the Model)
SYSTEM_INSTRUCTION = f"""
You are 'ProGlot', an expert {selected_label} tutor for Turkish speakers.
IMPORTANT: This is an ongoing lesson. Remember previous mistakes and progress.

RULES:
1. Explain concepts in Turkish, but provide examples strictly in {selected_label}.
2. Correct mistakes gently and explain the 'Why' behind the rule.
3. End every response with an interactive question or exercise.
4. NEVER just provide the answer; keep the dialogue active.

TONE: Professional, Patient, Encouraging.
"""

def initialize_model():
    """Initializes the Gemini model with specific generation config."""
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "max_output_tokens": 2048,
    }
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )

# Main Logic: Check for language change or initialization
if "chat_session" not in st.session_state or st.session_state.get("current_lang_code") != lang_code:
    with st.spinner(f"Loading {selected_label} history..."):
        model = initialize_model()
        past_history = load_history_safe(lang_code)
        
        # --- SLIDING WINDOW LOGIC ---
        # Optimize tokens: Only load the last N messages into active memory
        if len(past_history) > MAX_HISTORY_LENGTH:
            recent_history = past_history[-MAX_HISTORY_LENGTH:]
        else:
            recent_history = past_history
        # ----------------------------

        try:
            st.session_state.chat_session = model.start_chat(history=recent_history)
        except Exception:
            # Fallback for API errors
            st.session_state.chat_session = model.start_chat(history=[])
        
        st.session_state.current_lang_code = lang_code
        # Mark as initialized if history exists
        st.session_state.is_initialized = len(past_history) > 0

# --- 6. RENDER CHAT INTERFACE ---
st.title(f"🌍 ProGlot AI")
st.subheader(f"{selected_label} Tutor")

# Display Chat History
if st.session_state.chat_session:
    for message in st.session_state.chat_session.history:
        role = "user" if message.role == "user" else "assistant"
        avatar = "👤" if role == "user" else "🎓"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message.parts[0].text)

# Cold Start / First Interaction Trigger
if not st.session_state.is_initialized:
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("Tutor is preparing the lesson plan..."):
            try:
                # Invisible prompt to start the conversation
                response = st.session_state.chat_session.send_message(
                    f"Start the lesson. Introduce yourself professionally in Turkish and ask for my {selected_label} proficiency level."
                )
                st.markdown(response.text)
                st.session_state.is_initialized = True
                save_history_safe(st.session_state.chat_session.history, lang_code)
            except Exception as e:
                st.error(f"Initialization Error: {e}")

# User Input Handling
user_input = st.chat_input(f"Type your response in {selected_label} or Turkish...")

if user_input:
    # 1. Render User Message
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
    
    # 2. Render Assistant Response
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("ProGlot is thinking..."):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                st.markdown(response.text)
                
                # Save the new state to disk (Simulate persistence)
                save_history_safe(st.session_state.chat_session.history, lang_code)
            
            except google_exceptions.ServiceUnavailable:
                st.error("⚠️ Service Unavailable: Google servers are temporarily down.")
            except google_exceptions.ResourceExhausted:
                st.error("⚠️ API Quota Exceeded. Please use the 'Export to Gemini Web' feature in the sidebar.")
            except Exception as e:
                st.error(f"An error occurred: {e}")