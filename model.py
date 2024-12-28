from flask import Flask, request, jsonify
import chromadb
import os
import requests
import PyPDF2
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize ChromaDB
DB_NAME = "QnA"
client = chromadb.Client()
db = client.get_or_create_collection(name=DB_NAME)

class PDFReader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def read(self):
        try:
            with open(self.pdf_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return [page.extract_text() for page in pdf_reader.pages]
        except Exception as e:
            logger.error(f"Error reading PDF: {str(e)}")
            return []

# Initialize FAQ documents if the database is empty
if db.count() == 0:
    pdf_path = "Company_FAQ.pdf"
    if os.path.exists(pdf_path):
        pdf_reader = PDFReader(pdf_path)
        pdf_text = pdf_reader.read()
        for idx, page in enumerate(pdf_text):
            db.add(documents=[page], ids=[f"page-{idx}"])
        logger.info("FAQ documents added to the database.")
    else:
        logger.warning(f"FAQ PDF file not found: {pdf_path}")

@app.route("/query", methods=["POST"])
def ask_llama():
    try:
        data = request.json
        username = data.get("username")
        query = data.get("query")

        if not username or not query:
            return jsonify({"error": "Username and query are required."}), 400

        logger.info(f"Received query from {username}: {query}")

        user_file = f"logs/{username}.txt"
        os.makedirs("logs", exist_ok=True)

        business_prompt = """
        You are a smart business chatbot named Zola for 'Acme Corporation', here to assist customers with general business inquiries.
        Your responses should be clear, concise, professional, and based on the FAQ provided below.
        Please respond intelligently, just like a human customer support representative.
        """

        full_prompt = business_prompt + f"\nUser's Query: {query}\nResponse:"

        # Query the database
        result = db.query(query_texts=[query], n_results=1)
        
        if not result["documents"] or not result["documents"][0]:
            logger.warning(f"No relevant documents found for query: {query}")
            response_text = "I apologize, but I couldn't find specific information about that. Could you please rephrase your question or ask something else?"
        else:
            try:
                url = "http://localhost:11434/api/chat"
                model = "llama3.2:latest"
                data = {
                    "model": model,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "stream": False
                }
                headers = {"Content-Type": "application/json"}
                
                response = requests.post(url, json=data, headers=headers, timeout=30)
                response.raise_for_status()  # Raise exception for bad status codes
                
                response_data = response.json()
                response_text = response_data.get("message", {}).get("content", 
                    "I apologize, but I'm having trouble generating a response right now. Please try again later.")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling LLM API: {str(e)}")
                response_text = "I apologize, but I'm having trouble processing your request right now. Please try again later."

        # Log the interaction
        try:
            with open(user_file, "a") as file:
                file.write(f"Query: {query}\nResponse: {response_text}\n\n")
        except IOError as e:
            logger.error(f"Error writing to log file: {str(e)}")

        return jsonify({"response": response_text})

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
