"""
Setup Script - Run this ONCE to create your assistant with pre-loaded files
After running, add the printed IDs to Railway environment variables
"""

from openai import OpenAI
import os

# Initialize OpenAI client
api_key = input("Enter your OpenAI API key: ")
client = OpenAI(api_key=api_key)

model = "gpt-3.5-turbo"

print("\n🚀 Starting Assistant Setup...\n")

# Step 1: Create Vector Store
print("Step 1: Creating vector store...")
vector_store = client.vector_stores.create(name="Document Assistant Knowledge Base")
print(f"✅ Vector store created: {vector_store.id}\n")

# Step 2: Upload Files
print("Step 2: Upload your files")
print("Enter file paths one at a time (or type 'done' when finished):")
print("Example: /path/to/document.pdf\n")

file_paths = []
while True:
    file_path = input("File path (or 'done'): ").strip()
    if file_path.lower() == 'done':
        break
    if os.path.exists(file_path):
        file_paths.append(file_path)
        print(f"  ✅ Added: {os.path.basename(file_path)}")
    else:
        print(f"  ❌ File not found: {file_path}")

if not file_paths:
    print("\n❌ No files added. Exiting.")
    exit()

print(f"\n📤 Uploading {len(file_paths)} file(s) to vector store...")

# Upload files to vector store
file_streams = []
for path in file_paths:
    file_streams.append(open(path, "rb"))

file_batch = client.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vector_store.id,
    files=file_streams
)

# Close file streams
for stream in file_streams:
    stream.close()

print(f"✅ Successfully uploaded {len(file_paths)} file(s)\n")

# Step 3: Create Assistant
print("Step 3: Creating assistant...")

assistant_name = input("Enter assistant name (default: 'Document Assistant'): ").strip() or "Document Assistant"

assistant_instructions = input(
    "Enter custom instructions (or press Enter for default): "
).strip() or """You are a helpful assistant that answers questions based on the documents in your knowledge base.
Use your vector store files to provide accurate, well-supported responses with citations.
Be clear, concise, and helpful in your answers."""

assistant = client.beta.assistants.create(
    name=assistant_name,
    instructions=assistant_instructions,
    model=model,
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
)

print(f"✅ Assistant created: {assistant.id}\n")

# Step 4: Display Results
print("="*60)
print("✅ SETUP COMPLETE!")
print("="*60)
print("\n📋 Save these IDs - you'll need them for Railway:\n")
print(f"ASSISTANT_ID={assistant.id}")
print(f"VECTOR_STORE_ID={vector_store.id}")
print("\n" + "="*60)
print("\n📝 Next Steps:")
print("1. Go to Railway → Your Project → Variables")
print("2. Add these two environment variables:")
print(f"   - ASSISTANT_ID = {assistant.id}")
print(f"   - VECTOR_STORE_ID = {vector_store.id}")
print("3. Redeploy your app")
print("4. Your assistant will be live with pre-loaded documents!")
print("\n" + "="*60)

# Optional: Test the assistant
test = input("\n🧪 Would you like to test the assistant now? (yes/no): ").strip().lower()
if test == 'yes':
    thread = client.beta.threads.create()
    
    print("\n💬 Test your assistant (type 'exit' to quit):\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            break
            
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        
        # Wait for completion
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == 'completed':
                break
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"Error: {run_status.status}")
                break
        
        # Get response
        messages = client.beta.threads.messages.list(
            thread_id=thread.id,
            order="desc",
            limit=1
        )
        
        response = messages.data[0].content[0].text.value
        print(f"\nAssistant: {response}\n")

print("\n✨ All done! Your assistant is ready to deploy.")
