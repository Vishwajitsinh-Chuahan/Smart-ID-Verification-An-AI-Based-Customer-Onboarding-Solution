import streamlit as st
import os
import time
from PIL import Image  # For image handling
from home_page import show_home_page
from document_upload_page import show_document_upload_page
from face_recognition_page import show_face_recognition_page
from face_processing.question_verification_page import show_question_verification_page

# Initialize session state variables
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# Set page configuration
st.set_page_config(
    page_title="Smart ID Verification",
    page_icon="🔐",
    layout="centered"
)


# Custom CSS for styling
def apply_custom_css():
    st.markdown("""
    <style>
    /* Main styles */
    .main-header {
        font-size: 2.2rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.4rem;
        color: #424242;
        margin-bottom: 1.5rem;
    }

    /* Top Navigation bar */
    .nav-container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        background-color: #1E88E5;
        padding: 10px 15px;
        color: white;
        align-items: center;
        margin-bottom: 20px;
    }
    .nav-title {
        font-size: 1.3rem;
        font-weight: bold;
    }
    .nav-links {
        display: flex;
        gap: 15px;
    }
    .nav-link {
        color: white;
        text-decoration: none;
    }

    /* Icon-based navigation for home page */
    .steps-container {
        display: flex;
        justify-content: space-around;
        margin: 30px 0;
        text-align: center;
    }
    .step-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 25%;
    }
    .step-icon {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 8px;
        color: #1E88E5;
        font-size: 20px;
    }
    .step-label {
        font-size: 14px;
        color: #424242;
        font-weight: 500;
    }

    /* Components */
    .upload-container {
        background-color: #f8f9fa;
        padding: 25px;
        border-radius: 10px;
        margin: 20px 0;
        text-align: center;
        border: none !important;
    }
    .guidelines {
        background-color: #E8F5E9;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
    }
    .success-message {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
    }
    .warning-message {
        background-color: #FFF8E1;
        color: #FF8F00;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
    }
    .error-message {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
    }

    /* Confirmation Page Styles */
    .confirmation-container {
        background-color: white;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        padding: 30px;
        margin: 20px 0;
    }

    .confirmation-header {
        display: flex;
        align-items: center;
        margin-bottom: 25px;
    }

    .check-icon {
        background-color: #E8F5E9;
        color: #2E7D32;
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-size: 30px;
        margin-right: 20px;
    }

    .verification-item {
        display: flex;
        align-items: center;
        padding: 15px 0;
        border-bottom: 1px solid #f0f0f0;
    }

    .verification-icon {
        margin-right: 15px;
        color: #1E88E5;
        font-size: 18px;
    }

    .verification-check {
        margin-left: auto;
        color: #2E7D32;
        font-size: 20px;
    }

    .document-preview {
        margin: 20px 0;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 10px;
        text-align: center;
    }

    .action-buttons {
        display: flex;
        gap: 15px;
        margin-top: 30px;
    }

    .primary-button {
        background-color: #1E88E5;
        color: white;
        border: none;
        padding: 12px 20px;
        border-radius: 5px;
        cursor: pointer;
        flex: 1;
        font-weight: 500;
    }

    .secondary-button {
        background-color: #f0f0f0;
        color: #424242;
        border: none;
        padding: 12px 20px;
        border-radius: 5px;
        cursor: pointer;
        flex: 1;
        font-weight: 500;
    }

    /* Footer */
    .footer {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #ddd;
        text-align: center;
        color: #757575;
    }

    /* Fix for the blue dotted line in file uploader */
    .stFileUploader > div > div {
        border: none !important;
    }
    .stFileUploader > div {
        border: none !important;
    }

    /* File upload drag area */
    .upload-area {
        border: 2px dashed #ddd;
        border-radius: 10px;
        padding: 40px 20px;
        text-align: center;
        background-color: #f9f9f9;
        margin: 20px 0;
        cursor: pointer;
    }
    .upload-icon {
        font-size: 40px;
        color: #1E88E5;
        margin-bottom: 10px;
    }
    .upload-text {
        color: #666;
    }
    </style>
    """, unsafe_allow_html=True)


# Function to handle file upload
def save_uploaded_file(uploaded_file):
    try:
        if uploaded_file is not None:
            # Create a directory if it doesn't exist
            if not os.path.exists("uploaded_files"):
                os.makedirs("uploaded_files")

            file_path = os.path.join("uploaded_files", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None
    return None


# Top navigation bar
def render_navigation():
    st.markdown("""
    <div class="nav-container">
        <div class="nav-title">Smart ID Verification</div>
        <!--<div class="nav-links">
            <span class="nav-link">Help</span>
            <span class="nav-link">Admin</span>
        </div>-->
    </div>
    """, unsafe_allow_html=True)


# Main function to run the app
def main():
    apply_custom_css()

    # Initialize session state for navigation
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    if 'upload_success' not in st.session_state:
        st.session_state.upload_success = False
    if 'selected_document_type' not in st.session_state:
        st.session_state.selected_document_type = None
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None
    if 'new_upload' not in st.session_state:
        st.session_state.new_upload = False

    # Render navigation bar
    render_navigation()

    # Display uploaded document in sidebar if available
    if st.session_state.uploaded_file_path and st.session_state.page != 'confirmation':
        with st.sidebar:
            st.success("Document uploaded successfully!")
            try:
                # Try to open the image file
                image = Image.open(st.session_state.uploaded_file_path)
                # Display the image without the use_container_width parameter
                st.image(image, caption="Uploaded Document")
            except Exception as e:
                st.error(f"Error displaying image: {e}")

    # Navigation logic
    if st.session_state.page == 'home':
        show_home_page()
    elif st.session_state.page == 'document_upload':
        show_document_upload_page()
    elif st.session_state.page == 'face_recognition':
        show_face_recognition_page()
    elif st.session_state.page == 'question_verification':
        show_question_verification_page()  # New page for question verification
    elif st.session_state.page == 'confirmation':
        show_confirmation_page()


# New Confirmation page with centered design
def show_confirmation_page():
    # Add custom CSS for centering
    st.markdown("""
    <style>
    .centered-content {
        max-width: 800px;
        margin: 0 auto;
        text-align: center;
        padding: 20px;
    }
    .verification-item {
        display: flex;
        align-items: center;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
        border-radius: 8px;
        text-align: left;
    }
    .verification-icon {
        font-size: 24px;
        margin-right: 15px;
        width: 40px;
        text-align: center;
    }
    .verification-check {
        color: #4CAF50;
        font-size: 24px;
        margin-left: auto;
    }
    .main-header {
        color: #1E88E5;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="centered-content">', unsafe_allow_html=True)

    st.markdown("""
        <h2 class="main-header">Verification Successful</h2>
        <p>All verification steps have been completed</p>
    """, unsafe_allow_html=True)

    st.markdown("<h3>Detailed Validation Breakdown:</h3>", unsafe_allow_html=True)

    # Document Verification item
    st.markdown("""
        <div class="verification-item">
            <div class="verification-icon">📄</div>
            <div>
                <strong>Document Verification</strong>
                <div style="font-size:14px; color:#666;">ID document successfully validated</div>
            </div>
            <div class="verification-check">✓</div>
        </div>
    """, unsafe_allow_html=True)

    # Face Match item
    st.markdown("""
        <div class="verification-item">
            <div class="verification-icon">👤</div>
            <div>
                <strong>Face Match</strong>
                <div style="font-size:14px; color:#666;">Face verification successful</div>
            </div>
            <div class="verification-check">✓</div>
        </div>
    """, unsafe_allow_html=True)

    # Questionnaire item
    st.markdown("""
        <div class="verification-item">
            <div class="verification-icon">📋</div>
            <div>
                <strong>Questionnaire Responses</strong>
                <div style="font-size:14px; color:#666;">Security questions verified</div>
            </div>
            <div class="verification-check">✓</div>
        </div>
    """, unsafe_allow_html=True)

    # Action buttons
    if st.button("Return to Home Page", key="continue_button", type="primary", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)




if __name__ == "__main__":
    main()