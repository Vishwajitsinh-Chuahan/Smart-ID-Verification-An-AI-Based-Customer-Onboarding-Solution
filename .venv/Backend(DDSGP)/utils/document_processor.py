import streamlit as st
import requests
import base64
import json
import os
import sys
import time

# Add the parent directory to the path to import ocr_processor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ocr_processor import extract_text_from_upload


def process_document(uploaded_file):
    """
    Process the uploaded document using OCR and save to database
    Returns: (success, message)
    """
    if uploaded_file is None:
        return False, "No file uploaded"

    try:
        # Show processing indicator
        with st.spinner("Processing document..."):
            # Extract information from the document
            extracted_info = extract_text_from_upload(uploaded_file)

            if 'error' in extracted_info and extracted_info['error']:
                return False, f"Error during OCR processing: {extracted_info['error']}"

            # Check if we have the minimum required information
            if not extracted_info.get('id_number'):
                return False, "Could not extract Aadhar number from the document. Please upload a clearer image."

            if not extracted_info.get('date_of_birth'):
                return False, "Could not extract date of birth from the document. Please upload a clearer image."

            # Prepare data for API
            api_data = {
                'aadhar_number': extracted_info.get('id_number'),
                'name': extracted_info.get('name'),
                'date_of_birth': extracted_info.get('date_of_birth')
            }

            # Add photo if available
            if extracted_info.get('photo'):
                api_data['photo'] = base64.b64encode(extracted_info['photo']).decode('utf-8')

            # Check if record already exists
            response = requests.get(f"http://localhost:5000/check_aadhar/{api_data['aadhar_number']}")
            if response.status_code == 200:
                data = response.json()
                if data.get('exists'):
                    # Store the aadhar number in session state for face recognition
                    st.session_state.aadhar_number = api_data['aadhar_number']
                    return True, "Aadhar record already exists in database."

            # Save to database via API
            response = requests.post(
                "http://localhost:5000/save_record",
                json=api_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 201:
                # Store the aadhar number in session state for face recognition
                st.session_state.aadhar_number = api_data['aadhar_number']
                return True, "Document processed and saved successfully."
            else:
                data = response.json()
                return False, f"Error saving to database: {data.get('error', 'Unknown error')}"

    except Exception as e:
        return False, f"Error processing document: {str(e)}"
