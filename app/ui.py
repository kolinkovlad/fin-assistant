from uuid import uuid4

import httpx
import streamlit as st

from settings import get_settings

st.title("🧠 Portfolio Assistant")

BASE_URL = get_settings().API_URL

DEFAULT_TIMEOUT = 30 # seconds

if 'chat' not in st.session_state:
    st.session_state.chat = []

session_id = st.text_input("Session ID:", key="session_id", placeholder="Enter session ID to continue previous chat")

generate_session = st.button("Generate New Session ID")
if generate_session:
    session_id = str(uuid4())
    st.text(f"New session ID generated. {session_id} You can use this to continue the chat later.")



user_input = st.text_input("You:", key="user_input")

if st.button("Send") and user_input:
    st.session_state.chat.append(("user", user_input))

    with st.spinner("Thinking..."):
        try:
            res = httpx.post(
                url=f'{BASE_URL}/chat',
                json={"text": user_input},
                headers={"session-id": session_id} if session_id else {},
                timeout=30.0  # seconds
            )
            res.raise_for_status()
            data = res.json()
            reply = data.get("response", "")
            tool_result = data.get("tool_result", {})
            if tool_result.get("summary"):
                reply += f"\n\n📊 Tool Summary:\n{tool_result['summary']}"
            st.session_state.chat.append(("assistant", reply))
        except httpx.RequestError as e:
            st.error(f"Error contacting backend: {e}")
        except httpx.HTTPStatusError as e:
            st.error(f"Backend returned error: {e.response.status_code}")

for role, msg in st.session_state.chat:
    st.markdown(f"**{role.capitalize()}**: {msg}")
