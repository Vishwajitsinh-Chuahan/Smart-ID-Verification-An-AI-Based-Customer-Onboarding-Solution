import streamlit as st
import os
import sys
import requests
import json
from datetime import datetime
import numpy as np
from PIL import Image
import io
import cv2
import time

# Fix the import path for face_matching
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from face_processing.face_matching import FaceVerificationSystem


# JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def save_verification_result(aadhar_number, face_similarity, verification_passed):
    """Save face verification result to database via API"""
    try:
        # Convert numpy types to Python types
        if hasattr(face_similarity, 'item'):
            face_similarity = face_similarity.item()
        elif isinstance(face_similarity, np.floating):
            face_similarity = float(face_similarity)

        if hasattr(verification_passed, 'item'):
            verification_passed = verification_passed.item()
        elif isinstance(verification_passed, np.bool_):
            verification_passed = bool(verification_passed)

        api_data = {
            "aadhar_number": aadhar_number,
            "face_similarity": face_similarity,
            "verification_passed": verification_passed
        }

        response = requests.post(
            "http://localhost:5000/save_face_verification",
            json=api_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            st.success("Verification result saved to database")
            return True
        else:
            data = response.json()
            st.error(f"Error saving verification result: {data.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        st.error(f"Error saving verification result: {str(e)}")
        return False


def show_face_recognition_page():
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .top-bar {
        background-color: #1E88E5;
        color: white;
        padding: 10px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .main-header {
        font-size: 1.5rem;
        color: white;
        margin: 0;
    }
    .top-bar-buttons {
        display: flex;
    }
    .top-bar-button {
        color: white;
        margin-left: 15px;
        cursor: pointer;
    }
    .info-card {
        background-color: #E3F2FD;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 5px solid #1976D2;
    }
    .instruction-card {
        background-color: #FFF8E1;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
        border-left: 5px solid #FFB300;
    }
    .status-card {
        background-color: #E8F5E9;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #43A047;
    }
    .error-card {
        background-color: #FFEBEE;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #E53935;
    }
    .camera-placeholder {
        background-color: #f0f0f0;
        height: 240px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        text-align: center;
        flex-direction: column;
    }
    .badge {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 3px 8px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
        margin-left: 5px;
    }
    .badge-blue {
        background-color: #E3F2FD;
        color: #1976D2;
    }
    </style>
    """, unsafe_allow_html=True)

    # Page header
    st.markdown('<h2>Face Verification</h2>', unsafe_allow_html=True)
    # st.markdown('<p>Please position your face in the frame</p>', unsafe_allow_html=True)

    # Initialize face verification system if not already in session state
    if 'face_verification_system' not in st.session_state:
        try:
            with st.spinner("Loading face verification system..."):
                st.session_state.face_verification_system = FaceVerificationSystem()
        except Exception as e:
            st.error(f"Error initializing face verification system: {str(e)}")
            st.session_state.face_verification_system = None

    # Get FaceVerificationSystem instance
    face_system = st.session_state.face_verification_system

    # Display information about the uploaded document
    if 'uploaded_file_path' in st.session_state and st.session_state.uploaded_file_path:
        # Get document information
        document_name = os.path.basename(st.session_state.uploaded_file_path)
        document_type = st.session_state.get('selected_document_type', "Aadhar Card")

        # Get Aadhar number if available
        aadhar_number = st.session_state.get('aadhar_number', "")

        # Display document info in a styled card
        st.markdown(f"""
        <div class="info-card">
            <p><strong>Uploaded Document:</strong> {document_name}</p>
            <p><strong>Document Type:</strong> <span class="badge badge-blue">{document_type}</span></p>
            <p><strong>Aadhar Number:</strong> <span class="badge">{aadhar_number}</span></p>
        </div>
        """, unsafe_allow_html=True)

        # Display ID Photo and Webcam Image side by side
        col1, col2 = st.columns(2)

        # with col1:
        #     st.markdown("<h3>ID Photo</h3>", unsafe_allow_html=True)
        #     # Try to display the extracted photo
        #     extracted_photo = None
        #
        #     try:
        #         if aadhar_number:
        #             # Try to get photo from API
        #             response = requests.get(f"http://localhost:5000/get_photo/{aadhar_number}")
        #             if response.status_code == 200:
        #                 photo_bytes = response.content
        #                 extracted_photo = photo_bytes
        #                 image = Image.open(io.BytesIO(photo_bytes))
        #                 st.image(image, caption="Extracted Photo")
        #             else:
        #                 # Fallback to uploaded document
        #                 image = Image.open(st.session_state.uploaded_file_path)
        #                 st.image(image, caption="Uploaded Document")
        #         else:
        #             # Display the uploaded document
        #             image = Image.open(st.session_state.uploaded_file_path)
        #             st.image(image, caption="Uploaded Document")
        #     except Exception as e:
        #         st.error(f"Error displaying image: {str(e)}")
        with col1:
            st.markdown("<h3>ID Photo</h3>", unsafe_allow_html=True)
            try:
                if aadhar_number:
                    response = requests.get(f"http://localhost:5000/get_photo/{aadhar_number}")
                    if response.status_code == 200:
                        photo_bytes = response.content
                        image = Image.open(io.BytesIO(photo_bytes))
                        st.image(image, width=300)  # Removed caption
                    else:
                        image = Image.open(st.session_state.uploaded_file_path)
                        st.image(image, width=300)  # Removed caption
                else:
                    image = Image.open(st.session_state.uploaded_file_path)
                    st.image(image, width=300)  # Removed caption
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")

        with col2:
            st.markdown("<h3>Captured Image</h3>", unsafe_allow_html=True)

            # Initialize webcam states
            if 'webcam_started' not in st.session_state:
                st.session_state.webcam_started = False

            if 'verification_result' not in st.session_state:
                st.session_state.verification_result = None

            if 'verification_in_progress' not in st.session_state:
                st.session_state.verification_in_progress = False

            if 'instructions_read' not in st.session_state:
                st.session_state.instructions_read = False

            # Check for saved webcam image
            webcam_image_path = ""
            if 'verification_complete' in st.session_state and st.session_state.verification_complete:
                # Look for saved webcam image in the verification_results directory
                webcam_image_dir = "verification_results"
                if os.path.exists(webcam_image_dir):
                    # Get most recent webcam image
                    webcam_files = [f for f in os.listdir(webcam_image_dir) if f.startswith("webcam_face_")]
                    if webcam_files:
                        # Sort by creation time (newest first)
                        webcam_files.sort(key=lambda x: os.path.getmtime(os.path.join(webcam_image_dir, x)),
                                          reverse=True)
                        webcam_image_path = os.path.join(webcam_image_dir, webcam_files[0])

            # Display webcam image or placeholder
            # if webcam_image_path and os.path.exists(webcam_image_path):
            #     try:
            #         # Display the saved webcam image
            #         image = Image.open(webcam_image_path)
            #         st.image(image, caption=f"Captured: {os.path.basename(webcam_image_path)}")
            #     except Exception as e:
            #         st.error(f"Error displaying webcam image: {str(e)}")
            #         # Show a placeholder with error message
            #         st.markdown("""
            #         <div class="camera-placeholder" style="background-color: #FFEBEE;">
            #             <p style="color: #C62828;">Failed to load captured image</p>
            #         </div>
            #         """, unsafe_allow_html=True)
            if webcam_image_path and os.path.exists(webcam_image_path):
                try:
                    image = Image.open(webcam_image_path)
                    st.image(image, width=300)  # Removed dynamic caption
                except Exception as e:
                    st.error(f"Error displaying webcam image: {str(e)}")
                    st.markdown("""
                        <div class="camera-placeholder" style="background-color: #FFEBEE;">
                            <p style="color: #C62828;">Failed to load captured image</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                if st.session_state.verification_in_progress:
                    st.markdown("""
                    <div class="camera-placeholder">
                        <p style="color: #1976D2; font-weight: bold;">Verification in progress...</p>
                        <div style="margin-top: 10px;">
                            <p style="color: #666; font-size: 0.9rem;">✓ Detecting face</p>
                            <p style="color: #666; font-size: 0.9rem;">⟳ Waiting for eye blink</p>
                            <p style="color: #666; font-size: 0.9rem;">⟳ Waiting for head movement</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif 'verification_result' in st.session_state and st.session_state.verification_result:
                    result = st.session_state.verification_result
                    if result['match']:
                        st.markdown("""
                        <div class="camera-placeholder" style="background-color: #E8F5E9;">
                            <p style="color: #2E7D32; font-weight: bold; font-size: 1.2rem;">✅ VERIFIED!</p>
                            <p style="color: #2E7D32; font-size: 0.9rem;">Face verification successful</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="camera-placeholder" style="background-color: #FFEBEE;">
                            <p style="color: #C62828; font-weight: bold; font-size: 1.2rem;">❌ VERIFICATION FAILED</p>
                            <p style="color: #C62828; font-size: 0.9rem;">Face does not match</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="camera-placeholder">
                        <p style="color: #666;">No image captured yet</p>
                        <p style="color: #666; font-size: 0.9rem;">Follow the instructions below and click START FACE VERIFICATION</p>
                    </div>
                    """, unsafe_allow_html=True)

        # Detailed verification instructions
        st.markdown("""
        <div class="instruction-card">
            <h3 style="margin-top: 0; color: #F57C00;">Verification Instructions</h3>
            <p><b>Please follow these steps for successful verification:</b></p>
            <ol>
                <li><b>Proper Positioning:</b> Ensure your face is clearly visible in the camera frame</li>
                <li><b>Eye Blinking:</b> Blink your eyes twice when prompted</li>
                <li><b>Head Movement:</b> Move your head slowly from left to right when prompted</li>
                <li><b>Lighting Conditions:</b> Make sure your face is well-lit with no harsh shadows</li>
            </ol>
            <p><b>Note:</b> Failure to follow these instructions may result in verification failure.</p>
        </div>
        """, unsafe_allow_html=True)

        # Checkbox to confirm reading instructions
        instructions_read = st.checkbox("I have read and understood the instructions above",
                                        value=st.session_state.instructions_read)

        if instructions_read:
            st.session_state.instructions_read = True

        # Verification button
        start_button = st.button(
            "Start Face Verification",
            key="start_face_verification",
            type="primary",
            disabled=(not st.session_state.instructions_read) or
                     st.session_state.verification_in_progress or
                     (hasattr(st.session_state, 'verification_complete') and st.session_state.verification_complete)
        )

        if start_button and face_system and aadhar_number:
            st.session_state.webcam_started = True
            st.session_state.verification_in_progress = True

            # Start the face verification process
            try:
                with st.spinner("Performing face verification..."):
                    # Run the verification process
                    id_image_path = st.session_state.uploaded_file_path
                    match, similarity = face_system.run_verification(id_image_path)

                    # Save verification result to database
                    save_verification_result(
                        aadhar_number=aadhar_number,
                        face_similarity=similarity,
                        verification_passed=match
                    )

                    # Store the result in session state
                    st.session_state.verification_result = {
                        'match': match,
                        'similarity': similarity
                    }

                    # Set verification as complete
                    st.session_state.verification_in_progress = False
                    st.session_state.verification_complete = True

                    st.rerun()
            except Exception as e:
                st.error(f"Error during face verification: {str(e)}")
                st.session_state.verification_in_progress = False
        elif start_button and not aadhar_number:
            st.error("Aadhar number not found. Please upload a valid document first.")

        # Display verification result if available
        if 'verification_result' in st.session_state and st.session_state.verification_result:
            result = st.session_state.verification_result
            if result['match']:
                st.markdown(f"""
                <div class="status-card">
                    <h3 style="margin-top: 0; color: #2E7D32;">✅ Verification Successful</h3>
                    <p>Face verified with similarity score of {result['similarity']:.2f}</p>
                    <!-- <p style="margin-bottom: 0;">Verification result saved to database</p> -->
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="error-card">
                    <h3 style="margin-top: 0; color: #C62828;">❌ Verification Failed</h3>
                    <p>Face verification failed. Similarity: {result['similarity']:.2f}</p>
                    <!-- <p style="margin-bottom: 0;">Verification result saved to database</p> -->
                </div>
                """, unsafe_allow_html=True)

        # Navigation buttons at the bottom
        nav_col1, nav_col2 = st.columns([1, 1])

        with nav_col1:
            back_button = st.button(
                "Back to Document Upload",
                key="back_button",
                use_container_width=True
            )

            if back_button:
                # Modified to use st.session_state.page instead of current_page to match main app
                st.session_state.page = "document_upload"
                # Reset verification states
                if 'webcam_started' in st.session_state:
                    st.session_state.webcam_started = False
                if 'verification_result' in st.session_state:
                    st.session_state.verification_result = None
                if 'verification_in_progress' in st.session_state:
                    st.session_state.verification_in_progress = False
                if 'verification_complete' in st.session_state:
                    st.session_state.verification_complete = False
                if 'instructions_read' in st.session_state:
                    st.session_state.instructions_read = False
                st.rerun()

        with nav_col2:
            continue_button = st.button(
                "Continue to Question Verification",
                key="continue_button",
                type="primary",
                use_container_width=True,
                disabled=not (
                        'verification_result' in st.session_state and
                        st.session_state.verification_result and
                        st.session_state.verification_result['match']
                )
            )
            if continue_button:
                # Redirect to question verification page instead of confirmation page
                st.session_state.page = "question_verification"
                st.rerun()
    else:
        st.warning("Please upload an ID document first.")
        if st.button("Go to Document Upload"):
            st.session_state.page = "document_upload"
            st.rerun()
