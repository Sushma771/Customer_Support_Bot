import os
import time
import json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# --- Load environment variables ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")  # optional
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
system_prompt = os.getenv(
    "SYSTEM_PROMPT",
    "You are a friendly, concise customer support agent. "
    "If you do not know an answer, ask a clarifying question."
)

if not api_key:
    st.error("❌ Missing OPENAI_API_KEY in your .env file.")
    st.stop()

# --- Initialize client ---
client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

# --- Page config ---
st.set_page_config(page_title="AI Support Bot", page_icon="💬", layout="centered")

# --- Directory for chat storage ---
CHAT_DIR = "chats"
os.makedirs(CHAT_DIR, exist_ok=True)

def chat_file(customer_id):
    return os.path.join(CHAT_DIR, f"customer_{customer_id}.json")

def history_file(customer_id):
    return os.path.join(CHAT_DIR, f"customer_{customer_id}_history.json")

def load_chat(customer_id):
    """Load current chat"""
    path = chat_file(customer_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return [{"role": "system", "content": system_prompt}]

def save_chat(customer_id, chat):
    """Save current chat"""
    with open(chat_file(customer_id), "w", encoding="utf-8") as f:
        json.dump(chat, f, indent=2, ensure_ascii=False)

def save_to_history(customer_id, chat):
    """Append finished chat into one history file"""
    path = history_file(customer_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    for msg in chat:
        if msg["role"] != "system":
            history.append(msg)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

# --- Customer ID Input ---
st.sidebar.title("👤 Customer")
customer_id = st.sidebar.text_input("Enter Customer ID", key="customer_id_input")

# --- Load chat history ---
if customer_id:
    if "customer_chats" not in st.session_state:
        st.session_state.customer_chats = {}

    if customer_id not in st.session_state.customer_chats:
        st.session_state.customer_chats[customer_id] = load_chat(customer_id)

# --- Sidebar controls ---
with st.sidebar:
    st.write("Model:", model)
    st.caption("Tip: Change default model/system prompt in `.env`")
    st.markdown("---")

    if st.button("🔄 New Chat"):
        if customer_id:
            # Move current chat to history before clearing
            old_chat = st.session_state.customer_chats[customer_id]
            save_to_history(customer_id, old_chat)

            # Start fresh
            st.session_state.customer_chats[customer_id] = [
                {"role": "system", "content": system_prompt}
            ]
            save_chat(customer_id, st.session_state.customer_chats[customer_id])
            st.success("✅ Old chat moved to history. New chat started.")
            st.rerun()

    # Show combined old history
    if customer_id and os.path.exists(history_file(customer_id)):
        st.markdown("### 📜 Full Chat History")
        with open(history_file(customer_id), "r", encoding="utf-8") as f:
            history = json.load(f)
        for msg in history:
            st.write(f"**{msg['role'].capitalize()}**: {msg['content']}")

# --- App Title ---
st.title("💁‍♀️ AI-powered Customer Support Bot")
st.caption("Chats saved. Each customer has a full combined history.")

# --- Display active chat ---
if customer_id:
    messages = st.session_state.customer_chats[customer_id]
    for msg in messages:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- Input box ---
if customer_id:
    user_input = st.chat_input("Type your question...")
else:
    st.info("Please enter a Customer ID to start chatting.")
    user_input = None

# --- Handle new user message ---
if user_input and customer_id:
    st.session_state.customer_chats[customer_id].append(
        {"role": "user", "content": user_input}
    )
    save_chat(customer_id, st.session_state.customer_chats[customer_id])

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        streamed_text = ""

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": m["role"], "content": m["content"]}
                          for m in st.session_state.customer_chats[customer_id]],
                stream=True,
                temperature=0.2,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                streamed_text += delta
                placeholder.markdown(streamed_text)
                time.sleep(0.01)

        except Exception as e:
            streamed_text = f"⚠️ Error: {e}"
            placeholder.markdown(streamed_text)

        st.session_state.customer_chats[customer_id].append(
            {"role": "assistant", "content": streamed_text}
        )
        save_chat(customer_id, st.session_state.customer_chats[customer_id])