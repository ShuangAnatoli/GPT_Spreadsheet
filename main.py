import streamlit as st
import re
from googleapiclient.discovery import build
from google.oauth2 import service_account
import openai
import os
from dotenv import load_dotenv
from difflib import get_close_matches

# Set up OpenAI API key
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# Google Sheets setup
SERVICE_ACCOUNT_FILE = "readspreadsheets.json"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = "1TyQbFR3d2HEqqxf05UojTO7zMN_MR0EdlMv32SGs-Uo"
RANGE_NAME = "Sheet1!A:B"  # Adjust range if needed

# Function to authenticate and load data from Google Sheets
def load_sheet_data():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])
    
    if not values:
        return {}
    else:
        # Storing facts as a dictionary (fact -> answer)
        learned_data = {}
        for row in values:
            if len(row) >= 2:
                learned_data[row[0].strip().lower()] = row[1].strip()
        return learned_data

# Function to process user queries and apply learned knowledge
def answer_from_learned_data(query, data):
    query = query.strip().lower()
    
    # Check for close matches in the learned data
    close_matches = get_close_matches(query, data.keys(), n=1, cutoff=0.7)  # Adjust cutoff as needed
    if close_matches:
        return data[close_matches[0]]
    
    # If no close matches, fallback to OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ]
    )
    return response['choices'][0]['message']['content']

# Function to normalize and extract numbers and operations
def normalize_query(query):
    # Regex to extract basic math expressions (e.g., 1+1, 3 - 2, etc.)
    pattern = r"(\d+[\+\-\*/]\d+)"
    matches = re.findall(pattern, query)
    if matches:
        return matches[0].replace(" ", "")  # Return normalized math operation like '1+1'
    return None

# Streamlit App
def main():
    st.title("Google Sheets Powered Q&A System")
    st.write("This app learns from data in a Google Sheet and answers questions accordingly.")

    # Load data from Google Sheets
    st.info("Loading data from Google Sheets...")
    try:
        learned_data = load_sheet_data()
        st.success("Data loaded successfully!")
        st.json(learned_data)  # Optionally display loaded data for transparency
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets: {e}")
        return

    # Input for user query
    user_query = st.text_input("Enter your question:")

    # Button to get the answer
    if st.button("Get Answer"):
        if not user_query.strip():
            st.error("Please enter a valid question.")
        else:
            with st.spinner("Processing your question..."):
                try:
                    # Attempt to normalize the query (e.g., math expressions like 1+1, 2*3, etc.)
                    normalized_query = normalize_query(user_query)
                    if normalized_query:
                        # Check if the normalized query exists in learned data
                        answer = answer_from_learned_data(normalized_query, learned_data)
                    else:
                        # Otherwise, check the full query against learned data
                        answer = answer_from_learned_data(user_query, learned_data)
                    st.success("Here's the answer:")
                    st.write(answer)
                except Exception as e:
                    st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()