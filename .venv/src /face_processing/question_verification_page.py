
import streamlit as st
import speech_recognition as sr
import pyttsx3
from datetime import datetime
import re
import threading
import time
import json
import requests


## Function to fetch user data from database based on Aadhar number
def get_user_data(aadhar_number):
    try:
        # Make an API call to fetch user data
        response = requests.get(f"http://localhost:5000/api/get_aadhar_data/{aadhar_number}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching user data: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        return None


# Initialize speech engine
def text_to_speech(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Speed of speech
    engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
    engine.say(text)
    engine.runAndWait()


# Function to listen to user's speech input
def listen_to_speech(timeout=10):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.session_state.listening = True
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=timeout)
            st.session_state.listening = False
            try:
                text = recognizer.recognize_google(audio)
                return text.lower()
            except sr.UnknownValueError:
                return "SPEECH_NOT_RECOGNIZED"
            except sr.RequestError:
                return "SERVICE_UNAVAILABLE"
        except sr.WaitTimeoutError:
            st.session_state.listening = False
            return "TIMEOUT"


# Parse date of birth from speech - IMPROVED VERSION
def parse_dob(dob_speech):
    # For format: dd-month name-yyyy (e.g., "27 April 1995")
    month_names = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        # Add shortened month names
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'jun': '06', 'jul': '07', 'aug': '08', 'sept': '09', 'sep': '09',
        'oct': '10', 'nov': '11', 'dec': '12'
    }

    # Try different patterns
    patterns = [
        # dd month_name yyyy
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)\s+(\d{4})',
        # dd mm yyyy
        r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(\d{1,2})\s+(\d{4})',
        # Directly specifying "27-04-1995" or "27 04 1995" or "27/04/1995"
        r'(\d{1,2})[\s\-\/](\d{1,2})[\s\-\/](\d{4})'
    ]

    # Normalize input string
    dob_speech = dob_speech.lower().strip()

    for pattern in patterns:
        match = re.search(pattern, dob_speech)
        if match:
            day, month_or_num, year = match.groups()

            # Pad day with leading zero if needed
            day = day.zfill(2)

            # Convert month name to number if needed
            if month_or_num.lower() in month_names:
                month = month_names[month_or_num.lower()]
            else:
                month = month_or_num.zfill(2)

            # Return in format DD-MM-YYYY
            return f"{day}-{month}-{year}"

    # Handle special case for direct format matches
    # Format: DDMMYYYY or DD-MM-YYYY or DD/MM/YYYY
    direct_pattern = r'(\d{1,2})[-\/\s]*(\d{1,2})[-\/\s]*(\d{4})'
    match = re.search(direct_pattern, dob_speech)
    if match:
        day, month, year = match.groups()
        return f"{day.zfill(2)}-{month.zfill(2)}-{year}"

    return None


# Function to normalize database date
def normalize_date(date_str):
    """Convert date to DD-MM-YYYY format for consistent comparison"""
    # Handle slash format
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            return f"{parts[0].zfill(2)}-{parts[1].zfill(2)}-{parts[2]}"

    # Handle dash format
    if '-' in date_str:
        parts = date_str.split('-')
        if len(parts) == 3:
            return f"{parts[0].zfill(2)}-{parts[1].zfill(2)}-{parts[2]}"

    return date_str  # Return original if no transformation applies


# Parse Aadhar number (get last 4 digits)
def parse_aadhar_last_4(speech):
    # Extract any sequence of 4 digits
    pattern = r'\b\d{4}\b'
    match = re.search(pattern, speech)
    if match:
        return match.group(0)
    return None


# Function to verify the answer - IMPROVED VERSION
def verify_answer(question_type, user_answer, correct_data):
    if question_type == "dob":
        parsed_dob = parse_dob(user_answer)
        if parsed_dob:
            # Normalize the correct data format for comparison
            normalized_correct_dob = normalize_date(correct_data)

            # Compare the normalized formats
            correct_dob_parts = normalized_correct_dob.split('-')
            parsed_dob_parts = parsed_dob.split('-')

            if len(correct_dob_parts) == 3 and len(parsed_dob_parts) == 3:
                # Check if day, month, and year match
                return (correct_dob_parts[0] == parsed_dob_parts[0] and
                        correct_dob_parts[1] == parsed_dob_parts[1] and
                        correct_dob_parts[2] == parsed_dob_parts[2])
        return False

    elif question_type == "aadhar_last_4":
        last_4_digits = parse_aadhar_last_4(user_answer)
        correct_last_4 = correct_data[-4:]
        return last_4_digits == correct_last_4

    return False


# Save the verification results to the database
def save_verification_results(aadhar_number, verified_count, total_questions, overall_verified, results_json):
    try:
        # Create the data payload
        payload = {
            "aadhar_number": aadhar_number,
            "verified_count": verified_count,
            "total_questions": total_questions,
            "overall_verified": overall_verified,
            "results_json": results_json
        }

        # Make an API call to save verification results
        response = requests.post("http://localhost:5000/api/save_question_verification", json=payload)

        if response.status_code == 201:
            return True
        else:
            st.error(f"Error saving verification results: {response.text}")
            return False
    except Exception as e:
        st.error(f"Error connecting to server: {str(e)}")
        return False


# Main function to display question verification page
def show_question_verification_page():
    # Custom CSS for better UI
    st.markdown("""
    <style>
    .main {
        background-color: #f5f7ff;
    }
    .verification-container {
        background-color: white;
        border-radius: 10px;
        padding: 30px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 20px auto;
        max-width: 800px;
    }
    .header {
        text-align: center;
        margin-bottom: 20px;
    }
    .progress-bar-container {
        margin: 20px 0;
    }
    .question-container {
        margin: 40px 0;
        text-align: center;
    }
    .previous-question-container {
        margin: 20px 0;
        padding: 15px;
        background-color: #f9f9f9;
        border-radius: 8px;
        border-left: 4px solid #9e9e9e;
    }
    .instructions-container {
        margin: 20px 0;
        padding: 15px;
        background-color: #f1f8ff;
        border-radius: 8px;
        border-left: 4px solid #4285f4;
    }
    .instructions-title {
        font-weight: bold;
        color: #4285f4;
        margin-bottom: 10px;
    }
    .listening-indicator {
        color: #1e88e5;
        font-weight: bold;
        margin-top: 20px;
        text-align: center;
    }
    .result-success {
        color: #43a047;
        font-weight: bold;
    }
    .result-error {
        color: #e53935;
        font-weight: bold;
    }
    .button-container {
        display: flex;
        justify-content: space-around;
        margin-top: 30px;
    }
    .primary-button {
        background-color: #4285f4;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        font-size: 16px;
    }
    .secondary-button {
        background-color: #616161;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        font-size: 16px;
    }
    .footer {
        text-align: center;
        margin-top: 40px;
        color: #666;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="header">', unsafe_allow_html=True)
    st.markdown('<h1>Identity Verification</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Get current Aadhar number from session state
    aadhar_number = st.session_state.get('aadhar_number', None)

    if not aadhar_number:
        st.error("No Aadhar number found. Please complete the previous steps first.")
        if st.button("Go Back to Face Verification"):
            st.session_state.page = "face_recognition"
            st.rerun()
        return

    # Initialize session state variables if not already initialized
    if 'verification_started' not in st.session_state:
        st.session_state.verification_started = False
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
    if 'correct_answers' not in st.session_state:
        st.session_state.correct_answers = 0
    if 'total_questions' not in st.session_state:
        st.session_state.total_questions = 2  # DOB and Aadhar last 4 digits
    if 'listening' not in st.session_state:
        st.session_state.listening = False
    if 'speak_thread' not in st.session_state:
        st.session_state.speak_thread = None
    if 'attempts' not in st.session_state:
        st.session_state.attempts = 0
    # FIX: Explicitly set verification_complete to False when initializing
    if 'verification_complete' not in st.session_state:
        st.session_state.verification_complete = False
    if 'answered_questions' not in st.session_state:
        st.session_state.answered_questions = {}
    if 'user_responses' not in st.session_state:
        st.session_state.user_responses = {}
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'data_fetched' not in st.session_state:
        st.session_state.data_fetched = False
    if 'results_saved' not in st.session_state:
        st.session_state.results_saved = False
    if 'completion_announced' not in st.session_state:
        st.session_state.completion_announced = False

    # Fetch user data if not already fetched
    if st.session_state.user_data is None:
        with st.spinner("Fetching user data..."):
            user_data = get_user_data(aadhar_number)
            if user_data:
                st.session_state.user_data = user_data
                st.session_state.data_fetched = True
            else:
                st.error("Could not fetch user data for verification. Please try again later.")
                if st.button("Go Back to Face Verification"):
                    st.session_state.page = "face_recognition"
                    st.rerun()
                return

    # Define questions based on user data
    questions = [
        {
            "question": "Can you confirm your date of birth as shown on your document?",
            "type": "dob",
            "correct_answer": st.session_state.user_data.get("dob", ""),
            "speech": "Please confirm your date of birth as shown on your document.",
            "instruction": "You can say it like 'twenty seven april nineteen ninety five' or '27 04 1995'."
        },
        {
            "question": "Can you confirm the last 4 digits of your Aadhar number?",
            "type": "aadhar_last_4",
            "correct_answer": aadhar_number,
            "speech": "Please confirm the last 4 digits of your Aadhar number.",
            "instruction": "Simply say the four digits, for example 'two one seven nine'."
        }
    ]

    # FIX: Only check for verification_complete and current_question_index
    # to determine if verification is really complete
    verification_really_complete = (st.session_state.verification_complete and
                                    st.session_state.current_question_index >= st.session_state.total_questions)

    # Display initial instructions if verification hasn't started
    if not st.session_state.verification_started and not verification_really_complete:
        # st.markdown('<div class="instructions-container">', unsafe_allow_html=True)
        st.markdown('<div class="instructions-title">Important Instructions:</div>', unsafe_allow_html=True)
        st.markdown('''
        <ul>
            <li>You must answer all questions verbally (by speaking).</li>
            <li>Make sure your microphone is properly connected and working.</li>
            <li>Ensure you are in a quiet environment for better speech recognition.</li>
            <li>You will be asked 2 questions to verify your identity.</li>
            <li>Please answer clearly and follow the specific format instructions for each question.</li>
        </ul>
        ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Start verification button
        if st.button("Start Question Verification", key="start_verification"):
            st.session_state.verification_started = True
            # FIX: Ensure verification_complete is False when starting
            st.session_state.verification_complete = False
            st.session_state.current_question_index = 0

            # Speak the instructions
            def speak_initial_instructions():
                text_to_speech(
                    "Welcome to identity verification. Please answer all questions verbally. Make sure your microphone is working and you are in a quiet environment.")
                time.sleep(0.5)

            speak_thread = threading.Thread(target=speak_initial_instructions)
            speak_thread.start()
            st.session_state.speak_thread = speak_thread
            st.rerun()

    # Handle verification process
    elif st.session_state.verification_started and not verification_really_complete:
        # Display previous questions and answers
        for q_idx in range(st.session_state.current_question_index):
            if q_idx in st.session_state.answered_questions:
                prev_question = questions[q_idx]
                user_response = st.session_state.user_responses.get(q_idx, "No response recorded")
                verification_result = "Verification successful" if st.session_state.answered_questions[
                    q_idx] else "Verification failed"
                result_class = "result-success" if st.session_state.answered_questions[q_idx] else "result-error"

                st.markdown(f"<h3>Question {q_idx + 1} of {st.session_state.total_questions}</h3>",
                            unsafe_allow_html=True)
                st.markdown(f"<p><strong>{prev_question['question']}</strong></p>", unsafe_allow_html=True)
                st.markdown(f"<p>Your response: {user_response}</p>", unsafe_allow_html=True)
                st.markdown(f'<p class="{result_class}">{verification_result}</p>', unsafe_allow_html=True)

        # Check if we've reached the end of questions
        if st.session_state.current_question_index >= st.session_state.total_questions:
            st.session_state.verification_complete = True
            st.rerun()
            return

        current_question = questions[st.session_state.current_question_index]

        # Progress bar
        progress_percentage = (st.session_state.current_question_index / st.session_state.total_questions) * 100
        st.markdown(
            f'<div class="progress-bar-container">Question {st.session_state.current_question_index + 1} of {st.session_state.total_questions}</div>',
            unsafe_allow_html=True)
        st.progress(progress_percentage / 100)

        # Display question
        st.markdown(f'<div class="question-container"><h2>{current_question["question"]}</h2></div>',
                    unsafe_allow_html=True)

        # Display instructions for current question
        # st.markdown('<div class="instructions-container">', unsafe_allow_html=True)
        st.markdown(f'<div class="instructions-title">Instructions:</div>', unsafe_allow_html=True)
        st.markdown(f'<p>{current_question["instruction"]}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Handle question steps
        if st.session_state.current_step == 0:
            # Speak the question and instructions
            def speak_question():
                text_to_speech(current_question["speech"])
                time.sleep(0.5)
                text_to_speech(current_question["instruction"])

            st.session_state.speak_thread = threading.Thread(target=speak_question)
            st.session_state.speak_thread.start()
            st.session_state.current_step = 1
            st.rerun()

        elif st.session_state.current_step == 1:
            # Wait for the speech to finish
            if st.session_state.speak_thread and st.session_state.speak_thread.is_alive():
                st.info("The system is speaking. Please listen carefully...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.session_state.current_step = 2
                st.rerun()

        elif st.session_state.current_step == 2:
            # Show the button to give answer
            if st.button("Give Answer", key="give_answer", type="primary"):
                st.session_state.current_step = 3
                st.rerun()

        elif st.session_state.current_step == 3:
            # Listen for the user's response
            if st.session_state.listening:
                st.markdown('<div class="listening-indicator">Listening... Please speak now</div>',
                            unsafe_allow_html=True)
            else:
                with st.spinner("Listening to your response..."):
                    user_answer = listen_to_speech()

                    if user_answer == "SPEECH_NOT_RECOGNIZED":
                        st.warning("Sorry, I couldn't understand your response. Please try again.")
                        st.session_state.attempts += 1

                        if st.session_state.attempts >= 2:
                            text_to_speech(
                                "Sorry, I couldn't understand your response. Let's move to the next question.")
                            # Store the result for the current question (failed)
                            st.session_state.answered_questions[st.session_state.current_question_index] = False
                            st.session_state.user_responses[st.session_state.current_question_index] = "Not recognized"

                            # Reset for next question
                            st.session_state.current_step = 0
                            st.session_state.attempts = 0
                            st.session_state.current_question_index += 1

                        else:
                            # First attempt failed, give more specific instructions
                            text_to_speech(
                                "I couldn't understand you clearly. Please speak slowly and clearly, following the format instructions.")
                            st.session_state.current_step = 2  # Go back to Give Answer button

                    elif user_answer == "TIMEOUT" or user_answer == "SERVICE_UNAVAILABLE":
                        st.error(
                            "There was an issue with the speech recognition. Please check your microphone and try again.")
                        text_to_speech(
                            "There was an issue with the speech recognition. Please check your microphone and try again.")
                        st.session_state.current_step = 2  # Go back to Give Answer button

                    else:
                        # Save the user's response
                        st.session_state.user_responses[st.session_state.current_question_index] = user_answer
                        st.info(f"Your response: {user_answer}")

                        # Verify the answer
                        is_correct = verify_answer(
                            current_question["type"],
                            user_answer,
                            current_question["correct_answer"]
                        )

                        # Store the verification result
                        st.session_state.answered_questions[st.session_state.current_question_index] = is_correct

                        if is_correct:
                            st.success("Answer verified successfully!")
                            text_to_speech("Answer verified successfully.")
                            # Increment correct answers counter
                            st.session_state.correct_answers += 1

                            # Move to next question
                            st.session_state.current_step = 0
                            st.session_state.attempts = 0
                            st.session_state.current_question_index += 1

                        else:
                            st.error("Verification failed. The information doesn't match our records.")

                            # If first attempt, give another chance
                            st.session_state.attempts += 1
                            if st.session_state.attempts < 2:
                                text_to_speech(
                                    "Verification failed. Please make sure you're providing the correct information and try again.")
                                st.session_state.current_step = 2  # Go back to Give Answer button
                            else:
                                text_to_speech(
                                    "Verification failed. The information doesn't match our records. Moving to the next question.")
                                # Move to next question after two failed attempts
                                st.session_state.current_step = 0
                                st.session_state.attempts = 0
                                st.session_state.current_question_index += 1

                    # Check if all questions are done
                    if st.session_state.current_question_index >= st.session_state.total_questions:
                        st.session_state.verification_complete = True

                    st.rerun()

    # Verification complete
    elif verification_really_complete:
        # Display all questions and answers
        for q_idx in range(st.session_state.total_questions):
            if q_idx in st.session_state.answered_questions:
                prev_question = questions[q_idx]
                user_response = st.session_state.user_responses.get(q_idx, "No response recorded")
                verification_result = "Verification successful" if st.session_state.answered_questions[
                    q_idx] else "Verification failed"
                result_class = "result-success" if st.session_state.answered_questions[q_idx] else "result-error"

                st.markdown(f"<h3>Question {q_idx + 1} of {st.session_state.total_questions}</h3>",
                            unsafe_allow_html=True)
                st.markdown(f"<p><strong>{prev_question['question']}</strong></p>", unsafe_allow_html=True)
                st.markdown(f"<p>Your response: {user_response}</p>", unsafe_allow_html=True)
                st.markdown(f'<p class="{result_class}">{verification_result}</p>', unsafe_allow_html=True)

        st.markdown('<div class="question-container">', unsafe_allow_html=True)
        st.markdown('<h2>Verification Complete</h2>', unsafe_allow_html=True)

        # Calculate verification result - only pass if ALL answers are correct
        verification_result = "PASSED" if st.session_state.correct_answers == st.session_state.total_questions else "FAILED"
        overall_verified = verification_result == "PASSED"

        # Create results JSON for database storage
        results_json = {}
        for q_idx in range(st.session_state.total_questions):
            if q_idx in st.session_state.answered_questions:
                results_json[f"question_{q_idx + 1}"] = {
                    "question": questions[q_idx]["question"],
                    "user_response": st.session_state.user_responses.get(q_idx, "No response"),
                    "verified": st.session_state.answered_questions[q_idx]
                }

        # Save results to database if not already saved
        if not st.session_state.results_saved:
            with st.spinner("Saving verification results..."):
                save_success = save_verification_results(
                    aadhar_number=aadhar_number,
                    verified_count=st.session_state.correct_answers,
                    total_questions=st.session_state.total_questions,
                    overall_verified=overall_verified,
                    results_json=json.dumps(results_json)
                )
                if save_success:
                    st.session_state.results_saved = True

        if verification_result == "PASSED":
            st.markdown('<p class="result-success">Your identity has been successfully verified!</p>',
                        unsafe_allow_html=True)
            if not st.session_state.completion_announced:
                text_to_speech(
                    "Your identity has been successfully verified! Thank you for completing the verification process.")
                st.session_state.completion_announced = True
        else:
            st.markdown('<p class="result-error">Verification failed. Please contact support for assistance.</p>',
                        unsafe_allow_html=True)
            st.markdown(
                f'<p>Correct answers: {st.session_state.correct_answers}/{st.session_state.total_questions}</p>',
                unsafe_allow_html=True)
            if not st.session_state.completion_announced:
                text_to_speech("Verification failed. Please contact support for assistance.")
                st.session_state.completion_announced = True

        st.markdown('</div>', unsafe_allow_html=True)

        # Only show navigation buttons if they're relevant
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Start Over", key="start_over"):
                # Reset question verification state
                for key in ['verification_started', 'current_question_index', 'current_step',
                            'correct_answers', 'listening', 'attempts', 'verification_complete',
                            'answered_questions', 'user_responses', 'completion_announced',
                            'results_saved']:
                    if key in st.session_state:
                        st.session_state[key] = False if key in ['verification_started', 'verification_complete',
                                                                 'listening', 'completion_announced',
                                                                 'results_saved'] else 0

                st.session_state.answered_questions = {}
                st.session_state.user_responses = {}
                st.rerun()

        with col2:
            # Only enable the confirmation button if all answers are correct
            if verification_result == "PASSED":
                if st.button("Continue to Confirmation", key="continue", type="primary"):
                    st.session_state.page = "confirmation"
                    st.rerun()
            st.button("Go Back to Face Verification", key="go_back", on_click=lambda:
            setattr(st.session_state, 'page', 'face_recognition'))

    # FIX: Add else clause to handle edge cases where the state is unclear
    else:
        st.warning("There appears to be an issue with the verification flow. Let's reset and try again.")
        if st.button("Reset and Start Over", key="reset_verification"):
            # Reset all verification state variables
            for key in ['verification_started', 'current_question_index', 'current_step',
                        'correct_answers', 'listening', 'attempts', 'verification_complete',
                        'answered_questions', 'user_responses', 'completion_announced',
                        'results_saved']:
                if key in st.session_state:
                    st.session_state[key] = False if key in ['verification_started', 'verification_complete',
                                                             'listening', 'completion_announced',
                                                             'results_saved'] else 0

            st.session_state.answered_questions = {}
            st.session_state.user_responses = {}
            st.rerun()

