import streamlit as st
from openai import OpenAI
import time
import os

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

model = "gpt-3.5-turbo"

# ===========================
# ASSISTANT CONFIGURATION
# ===========================
# Pre-configured assistant and vector store IDs
# You'll set these after running the setup script
ASSISTANT_ID = os.getenv("ASSISTANT_ID") or st.secrets.get("ASSISTANT_ID", None)
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID") or st.secrets.get("VECTOR_STORE_ID", None)

# Function to get assistant response with citations
def get_assistant_response(assistant_id, input_text, thread_id):
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=input_text
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    # Wait for the run to complete
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status == 'completed':
            break
        elif run_status.status in ['failed', 'cancelled', 'expired']:
            st.error(f"Request failed with status: {run_status.status}")
            return None, []
        time.sleep(1)

    # Get most recent message
    messages = client.beta.threads.messages.list(
        thread_id=thread_id,
        order="desc",
        limit=1
    )

    latest_message = messages.data[0]
    if latest_message.role != "assistant" or latest_message.run_id != run.id:
        return None, []

    message_content = latest_message.content[0].text
    annotations = message_content.annotations

    # Reset citations for this single response
    citations = {}
    citation_counter = 0

    # Process annotations
    for annotation in annotations:
        if file_citation := getattr(annotation, "file_citation", None):
            if file_citation.file_id not in citations:
                cited_file = client.files.retrieve(file_citation.file_id)
                citations[file_citation.file_id] = (citation_counter, cited_file.filename)
                message_content.value = message_content.value.replace(annotation.text, f"[{citation_counter}]")
                citation_counter += 1
            else:
                existing_index = citations[file_citation.file_id][0]
                message_content.value = message_content.value.replace(annotation.text, f"[{existing_index}]")

    # Format citations for return
    formatted_citations = []
    if citations:
        for _, (index, filename) in sorted(citations.items(), key=lambda x: x[1][0]):
            formatted_citations.append(f"[{index}] {filename}")

        message_content.value += "\n\nReferences:\n"
        for citation in formatted_citations:
            message_content.value += f"• {citation}\n"

    return message_content.value, formatted_citations

# Initialize session state
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# ===========================
# APP UI
# ===========================
st.title("🤖 AI Document Assistant")
st.subheader("Ask questions about pre-loaded documents!")

# Check if assistant is configured
if not ASSISTANT_ID or not VECTOR_STORE_ID:
    st.error("⚠️ Assistant not configured yet. Please run the setup script first.")
    st.info("""
    **Setup Instructions:**
    1. Run `setup_assistant.py` to create your assistant and upload files
    2. Add the ASSISTANT_ID and VECTOR_STORE_ID to Railway environment variables
    3. Redeploy your app
    """)
    st.stop()

# Create thread if it doesn't exist
if st.session_state.thread_id is None:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input - always available
if user_input := st.chat_input("Ask me anything about the documents..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply, citations = get_assistant_response(
                ASSISTANT_ID,
                user_input,
                st.session_state.thread_id
            )

        if reply:
            st.markdown(reply)
            st.session_state.messages.append({
                "role": "assistant",
                "content": reply,
                "citations": citations
            })
        else:
            st.error("Sorry, I couldn't process your request. Please try again.")

# Clear conversation button
if st.session_state.messages:
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = client.beta.threads.create().id
        st.rerun()

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.write("This assistant has been pre-loaded with documents and is ready to answer your questions!")
    st.write("Just type your question in the chat box below.")
    
    if st.button("New Conversation"):
        st.session_state.messages = []
        st.session_state.thread_id = client.beta.threads.create().id
        st.rerun()
