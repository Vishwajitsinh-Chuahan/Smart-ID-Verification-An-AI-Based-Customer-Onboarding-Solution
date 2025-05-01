import streamlit as st
import time
import os
import sys

# Add the DDSGP directory to the path to import the document processor
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DDSGP"))
from utils.document_processor import process_document


def show_document_upload_page():
    st.markdown('<h1 class="main-header">Document Upload</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Please select and upload your document</p>', unsafe_allow_html=True)

    # Document type selection
    document_types = ["Aadhar Card", "Passport", "Driver's License", "Other"]

    # Check if we already have a selected document type in session state
    default_index = 0
    if st.session_state.selected_document_type in document_types:
        default_index = document_types.index(st.session_state.selected_document_type)

    selected_type = st.selectbox(
        "Select Document Type",
        options=document_types,
        index=default_index
    )

    # Update session state with selected document type
    if selected_type:
        st.session_state.selected_document_type = selected_type

    # # Clean file uploader UI
    # st.markdown("""
    # <div class="upload-area">
    #     <div class="upload-icon">📄</div>
    #     <p class="upload-text">Drag and drop your file here or click to browse</p>
    # </div>
    # """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload your document",
        type=["jpg", "jpeg", "png", "pdf"],
        label_visibility="collapsed"
    )

    # Display file information if uploaded
    if uploaded_file:
        st.markdown(f"""
        <div style="margin-top: 15px; padding: 10px; background-color: #E3F2FD; border-radius: 5px;">
            <p style="margin: 0;"><b>File:</b> {uploaded_file.name} ({round(uploaded_file.size / 1024, 2)} KB)</p>
        </div>
        """, unsafe_allow_html=True)

        # Mark that we have a new upload in this session
        st.session_state.new_upload = True

    st.caption("Maximum file size: 10MB • JPG, JPEG, PNG, PDF")

    # Document guidelines
    st.markdown("""
    <div class="guidelines">
        <h3 style="color: #2E7D32; margin-top: 0;">📋 Document Guidelines</h3>
        <ul style="list-style-type: none; padding-left: 0;">
            <li style="margin: 10px 0; display: flex; align-items: center;">
                <span style="color: #4CAF50; margin-right: 10px;">✓</span> Clear, high-resolution image
            </li>
            <li style="margin: 10px 0; display: flex; align-items: center;">
                <span style="color: #4CAF50; margin-right: 10px;">✓</span> Full document visible
            </li>
            <li style="margin: 10px 0; display: flex; align-items: center;">
                <span style="color: #4CAF50; margin-right: 10px;">✓</span> No glare or shadows
            </li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Buttons with conditional logic
    col1, col2 = st.columns([1, 1])

    # Always show Cancel button
    with col1:
        if st.button("Cancel", key="cancel_button", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()

    # Conditional button logic
    with col2:
        # If document already uploaded and no new upload in this session
        if st.session_state.uploaded_file_path and not st.session_state.new_upload:
            if st.button("Continue to Face Recognition", key="continue_button", type="primary",
                         use_container_width=True):
                st.session_state.page = 'face_recognition'
                st.rerun()
        # If we have a new upload in this session
        elif uploaded_file and selected_type:
            upload_button_text = "Process Document" if not st.session_state.uploaded_file_path else "Process New Document"
            if st.button(upload_button_text, key="upload_button", type="primary", use_container_width=True):
                # First save the file locally
                file_path = save_uploaded_file(uploaded_file)
                if file_path:
                    st.session_state.uploaded_file_path = file_path

                    # Process the document with OCR
                    # We need to reset the file pointer position before passing to OCR
                    uploaded_file.seek(0)
                    success, message = process_document(uploaded_file)

                    if success:
                        st.success(message)
                        st.session_state.upload_success = True
                        st.session_state.new_upload = False

                        # Add a small delay to show the success message
                        time.sleep(1)

                        # Go to next page
                        st.session_state.page = 'face_recognition'
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Failed to upload document. Please try again.")
        # Default upload button when no file is selected
        else:
            if st.button("Upload Document", key="upload_button", type="primary", use_container_width=True):
                if not selected_type:
                    st.warning("Please select a document type.")
                else:
                    st.warning("Please upload a document.")


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
