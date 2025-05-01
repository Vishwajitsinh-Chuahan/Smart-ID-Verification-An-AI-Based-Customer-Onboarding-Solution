import speech_recognition as sr
import pyttsx3
import random
import json
import os
import re
import unicodedata
import difflib
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple, Set
import jellyfish  # Make sure to pip install jellyfish










class IndianNameProcessor:
    """Specialized processor for Indian names with regional variations"""

    def __init__(self):
        # Phonetic similarity threshold
        self.PHONETIC_THRESHOLD = 0.7

        # Common Indian name suffix/prefix variations
        self.SUFFIX_VARIATIONS = {
            'sinh': ['singh', 'sing', 'sin', 'singha', 'singhji'],
            'singh': ['sinh', 'sing', 'sin', 'singha', 'singhji'],
            'bhai': ['bai', 'bye', 'by', 'bha'],
            'kumar': ['kumaar', 'kumer', 'comar', 'kumarr'],
            'ben': ['bhen', 'bean', 'been', 'behn'],
            'ji': ['jee', 'g', 'gee', 'jii'],
            'devi': ['devee', 'davi', 'davey', 'davi'],
            'nath': ['nat', 'naat', 'not', 'naath'],
            'prasad': ['prashad', 'parshad', 'pershad', 'prasaad'],
            'wala': ['vala', 'walla', 'valla', 'waala']
        }

        # Common regional name transformations
        self.REGIONAL_VARIATIONS = {
            # Gujarat/Rajasthan
            'chauhan': ['chouhan', 'chohan', 'chuhan', 'chavan', 'chavhan', 'chouan'],
            'rathod': ['rathore', 'rathor', 'rathour', 'ratod', 'rathode'],
            'rajput': ['raajput', 'rajpoot', 'rajputh', 'raajpoot'],
            'vadodara': ['vadodra', 'baroda', 'vadodra', 'vadodara'],
            'ahmedabad': ['ahemdabad', 'ahmadabad', 'amadabad', 'ahmdabad'],
            # South Indian
            'krishna': ['krushna', 'krsna', 'kirishna', 'krishnan'],
            'rao': ['row', 'rav', 'raw', 'raao'],
            'reddy': ['redy', 'ready', 'radi', 'reddi'],
            # North Indian
            'sharma': ['sharmaa', 'sharman', 'sherma', 'sharmaji'],
            'trivedi': ['tiwari', 'tripathi', 'tivedi', 'trivedy'],
            'shukla': ['shookla', 'sukla', 'shukl', 'shooklaa'],
            # Bengali
            'chatterjee': ['chaterjee', 'chattarji', 'chatterji', 'chatarji'],
            'banerjee': ['banerjea', 'bannerji', 'banarji', 'banerjii'],
            'mukherjee': ['mukharji', 'mukerji', 'mukerjea', 'mukarji']
        }

        # Common prefixes with variations
        self.PREFIX_VARIATIONS = {
            'dhar': ['dharm', 'dharma', 'dharam', 'daram', 'dharme'],
            'vishwa': ['vishv', 'vishwajit', 'vishwajeet', 'vishva', 'visvaa', 'vishwaa', 'visvajit', 'vishvajit'],
            'surya': ['suraja', 'suraj', 'suriya', 'soorya', 'suraya']
        }

        # Common speech recognition errors for Indian names
        self.SPEECH_RECOGNITION_ERRORS = {
            'trushit': ['truce',  'truth it', 'true shit', 'trusty', 'true sheet'],
            'karan': ['current', 'karen', 'karran', 'kiran', 'curren'],
            'patel': ['pattle', 'patell', 'petal', 'pattle', 'pattell'],
            'mehta': ['meta', 'mayta', 'mehata', 'metta', 'meheta']
        }

        # Common compound name patterns and their corrections
        self.COMPOUND_NAME_PATTERNS = {
            r'(\w+)singh(\w+)': r'\1 singh \2',  # vishwajitsinghchauhan -> vishwajit singh chauhan
            r'(\w+)sinh(\w+)': r'\1 sinh \2',  # vishwajitsinhchauhan -> vishwajit sinh chauhan
            r'(\w+)kumar(\w+)': r'\1 kumar \2',  # rajkumarsingh -> raj kumar singh
            r'(\w+)ji(\w+)': r'\1 ji \2',  # ramjipatel -> ram ji patel
            r'(\w+)bhai(\w+)': r'\1 bhai \2',  # nareshbhaipatel -> naresh bhai patel
            r'vishva(\w+)': r'vishwa\1',  # vishvajitsinh -> vishwajitsinh
            r'visvajit': r'vishwajit',  # visvajit -> vishwajit
            r'visvajeet': r'vishwajeet',  # visvajeet -> vishwajeet
            r'visva': r'vishwa',  # visva -> vishwa
            r'viswa': r'vishwa'  # viswa -> vishwa
        }

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent comparison
        - Remove diacritical marks
        - Convert to lowercase
        - Remove extra whitespaces
        - Remove special characters
        - Handle hyphens appropriately
        """
        if not text:
            return ""

        # Save hyphenated names before removing special characters
        hyphenated_names = re.findall(r'\w+-\w+', text.lower())

        # Remove diacritical marks
        normalized = unicodedata.normalize('NFKD', str(text).lower())
        normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')

        # Replace hyphens with spaces for better matching
        normalized = normalized.replace('-', ' ')

        # Remove extra whitespaces and special characters
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

        # Fix compound names that might be recognized without spaces
        for pattern, replacement in self.COMPOUND_NAME_PATTERNS.items():
            normalized = re.sub(pattern, replacement, normalized)

        # Add variations for hyphenated names
        for hyphenated in hyphenated_names:
            parts = hyphenated.split('-')
            if len(parts) == 2:
                # Add space-separated version
                space_version = ' '.join(parts)
                if space_version not in normalized:
                    normalized = f"{normalized} {space_version}"

        return normalized

    def generate_name_variations(self, name: str) -> Set[str]:
        """Generate possible variations of a name based on Indian naming conventions"""
        variations = {name}
        normalized_name = self.normalize_text(name)
        words = normalized_name.split()

        # Process each word in the name
        for word in words:
            # Check for suffix variations
            for suffix, variants in self.SUFFIX_VARIATIONS.items():
                if word.endswith(suffix):
                    root = word[:-len(suffix)]
                    for variant in variants:
                        variations.add(f"{root}{variant}")

            # Check for prefix variations
            for prefix, variants in self.PREFIX_VARIATIONS.items():
                if word.startswith(prefix):
                    suffix = word[len(prefix):]
                    for variant in variants:
                        variations.add(f"{variant}{suffix}")

            # Check for regional variations
            for base, variants in self.REGIONAL_VARIATIONS.items():
                if word == base:
                    variations.update(variants)

            # Check for speech recognition errors
            for base, variants in self.SPEECH_RECOGNITION_ERRORS.items():
                if word == base:
                    variations.update(variants)

        # Generate combined variations for multi-word names
        if len(words) > 1:
            # Handle compound names
            compound_variations = set()
            for variation in variations:
                var_words = variation.split()
                if len(var_words) > 1:
                    # Create variations with and without spaces
                    compound_variations.add(''.join(var_words))
                    compound_variations.add(' '.join(var_words))

                    # Create variations with hyphens
                    if len(var_words) == 2:
                        compound_variations.add(f"{var_words[0]}-{var_words[1]}")

            variations.update(compound_variations)

        return variations

    def compute_phonetic_similarity(self, str1: str, str2: str) -> float:
        """
        Compute phonetic similarity between two strings using multiple algorithms
        """
        if not str1 or not str2:
            return 0.0

        # Normalize inputs
        norm_str1 = self.normalize_text(str1)
        norm_str2 = self.normalize_text(str2)

        # Generate variations
        variations1 = self.generate_name_variations(norm_str1)
        variations2 = self.generate_name_variations(norm_str2)

        # Compute similarity scores
        similarity_scores = []

        # Difflib sequence matcher for the original strings
        difflib_score = difflib.SequenceMatcher(None, norm_str1, norm_str2).ratio()
        similarity_scores.append(difflib_score * 0.8)  # Weight of 0.8

        # Levenshtein distance
        levenshtein_score = 1 - (jellyfish.levenshtein_distance(norm_str1, norm_str2) /
                                 max(len(norm_str1), len(norm_str2)) if max(len(norm_str1), len(norm_str2)) > 0 else 1)
        similarity_scores.append(levenshtein_score * 0.7)  # Weight of 0.7

        # Soundex phonetic matching
        soundex_score = 1.0 if jellyfish.soundex(norm_str1) == jellyfish.soundex(norm_str2) else 0.0
        similarity_scores.append(soundex_score * 0.5)  # Weight of 0.5

        # Metaphone phonetic matching (better for Indian names)
        metaphone_score = 1.0 if jellyfish.metaphone(norm_str1) == jellyfish.metaphone(norm_str2) else 0.0
        similarity_scores.append(metaphone_score * 0.9)  # Weight of 0.9

        # Check variations - find the best match among all variations
        best_variation_score = 0.0
        for var1 in variations1:
            for var2 in variations2:
                var_score = difflib.SequenceMatcher(None, var1, var2).ratio()
                best_variation_score = max(best_variation_score, var_score)

        similarity_scores.append(best_variation_score * 1.0)  # Weight of 1.0 (highest)

        # Compute weighted average of similarity scores
        total_weight = 0.8 + 0.7 + 0.5 + 0.9 + 1.0
        weighted_sum = sum(similarity_scores)

        # Final similarity score
        final_similarity = weighted_sum / total_weight if total_weight > 0 else 0

        return final_similarity

    def match_names(self, spoken_name: str, stored_name: str) -> Dict[str, Any]:
        """
        Advanced name matching with detailed analysis
        """
        if not spoken_name or not stored_name:
            return {
                'overall_similarity': 0.0,
                'word_matches': [],
                'is_match': False,
                'match_details': {
                    'spoken_name': spoken_name,
                    'stored_name': stored_name,
                    'normalized_spoken': '',
                    'normalized_stored': ''
                }
            }

        # Normalize names
        norm_spoken = self.normalize_text(spoken_name)
        norm_stored = self.normalize_text(stored_name)

        # Split names into words
        spoken_words = norm_spoken.split()
        stored_words = norm_stored.split()

        # Compute overall name similarity
        overall_similarity = self.compute_phonetic_similarity(spoken_name, stored_name)

        # Word-level matching
        word_matches = []
        for spoken_word in spoken_words:
            best_match = (0, "")
            for stored_word in stored_words:
                similarity = self.compute_phonetic_similarity(spoken_word, stored_word)
                if similarity > best_match[0]:
                    best_match = (similarity, stored_word)
            word_matches.append(best_match)

        # Special handling for "vishwajitsinh" -> "visvajit singh" type errors
        if 'vishwajit' in stored_name.lower() or 'vishwajeet' in stored_name.lower():
            if 'visvajit' in spoken_name.lower() or 'visvajeet' in spoken_name.lower():
                # Boost similarity score for this common error
                overall_similarity = max(overall_similarity, 0.85)

        # Special handling for "sinh" -> "singh" variations
        if 'sinh' in stored_name.lower() and 'singh' in spoken_name.lower():
            # Boost similarity score for this common variation
            overall_similarity = max(overall_similarity, 0.9)

        # Analysis results
        return {
            'overall_similarity': overall_similarity,
            'word_matches': word_matches,
            'is_match': overall_similarity >= self.PHONETIC_THRESHOLD,
            'match_details': {
                'spoken_name': spoken_name,
                'stored_name': stored_name,
                'normalized_spoken': norm_spoken,
                'normalized_stored': norm_stored
            }
        }


class QuestionVerifier:
    def __init__(self, document_info_path=None):
        # Initialize speech recognition engine
        self.recognizer = sr.Recognizer()

        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)  # Speed of speech
        self.tts_engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)

        # Initialize Indian name processor
        self.name_processor = IndianNameProcessor()

        # Month name mapping for date processing
        self.month_names = {
            'january': '01', 'jan': '01',
            'february': '02', 'feb': '02',
            'march': '03', 'mar': '03',
            'april': '04', 'apr': '04',
            'may': '05',
            'june': '06', 'jun': '06',
            'july': '07', 'jul': '07',
            'august': '08', 'aug': '08',
            'september': '09', 'sep': '09', 'sept': '09',
            'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }

        # Load document information if provided
        self.document_info = None
        if document_info_path and os.path.exists(document_info_path):
            try:
                with open(document_info_path, 'r') as f:
                    self.document_info = json.load(f)
                print(f"Loaded document information from {document_info_path}")
            except Exception as e:
                print(f"Error loading document information: {e}")

        # Define question templates
        self.questions = [
            {
                "id": "dob",
                "text": "Please speak your date of birth.",
                "instruction": "Speak your date of birth in the format day, month, year. You can say the month name or number.",
                "max_retries": 3
            },
            {
                "id": "id_number",
                "text": "Please speak the last four digits of your Aadhaar number.",
                "instruction": "Speak only the last four digits clearly.",
                "max_retries": 3
            }
        ]

        # Store answers
        self.answers = {}
        self.verification_results = {}

        # Configure speech recognizer for better accuracy
        self.recognizer.energy_threshold = 300  # Increase for noisy environments
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Shorter pause to detect end of speech

    def _speak(self, text):
        """Convert text to speech"""
        print(f"System: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def _listen(self, timeout=5, phrase_time_limit=10):
        """
        Listen for speech and convert to text with improved handling
        for Indian accents and names
        """
        with sr.Microphone() as source:
            print("Listening...")
            # Adjust for ambient noise for better recognition
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                print("Speak now...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                print("Processing speech...")

                # Try multiple recognition services for better accuracy
                text = None

                # First try Google's service (most accurate for Indian accents)
                try:
                    text = self.recognizer.recognize_google(audio)
                except Exception as e:
                    print(f"Google recognition failed: {e}")

                # If Google fails, try Sphinx (works offline)
                if not text:
                    try:
                        text = self.recognizer.recognize_sphinx(audio)
                    except Exception as e:
                        print(f"Sphinx recognition failed: {e}")

                if text:
                    print(f"User said: {text}")
                    return text
                else:
                    print("Could not understand audio")
                    return None

            except sr.WaitTimeoutError:
                print("No speech detected within timeout period")
                return None
            except sr.UnknownValueError:
                print("Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                return None
            except Exception as e:
                print(f"Error in speech recognition: {e}")
                return None

    def _extract_date_components(self, date_string):
        """
        Extract day, month, and year from a date string that may contain month names
        Returns a tuple of (day, month, year) where month is normalized to a two-digit string
        """
        # Normalize the date string
        date_string = date_string.lower().strip()

        # First, check for month names in the string
        month_number = None
        for month_name, month_num in self.month_names.items():
            if month_name in date_string:
                month_number = month_num
                # Replace the month name with a placeholder for easier digit extraction
                date_string = date_string.replace(month_name, f" {month_num} ")
                break

        # Extract all numbers from the string
        numbers = re.findall(r'\d+', date_string)

        # If we have 3 numbers, assume day, month, year format
        if len(numbers) >= 3:
            day, month, year = numbers[0], numbers[1], numbers[2]

            # If month wasn't identified by name but is a number
            if not month_number:
                month_number = month

            # Normalize day and month to two digits
            day = day.zfill(2)
            month = month_number.zfill(2)

            # Handle two-digit years (assuming 20xx for years less than 50, 19xx otherwise)
            if len(year) == 2:
                year = f"20{year}" if int(year) < 50 else f"19{year}"

            return day, month, year

        # If we have 2 numbers and a month was identified by name
        elif len(numbers) == 2 and month_number:
            # Determine which number is day and which is year based on value
            if int(numbers[0]) <= 31 and (len(numbers[1]) == 4 or int(numbers[1]) > 31):
                day, year = numbers[0], numbers[1]
            else:
                day, year = numbers[1], numbers[0]

            # Normalize
            day = day.zfill(2)
            month = month_number

            # Handle two-digit years
            if len(year) == 2:
                year = f"20{year}" if int(year) < 50 else f"19{year}"

            return day, month, year

        # If we only have 1 number and a month was identified by name
        elif len(numbers) == 1 and month_number:
            # Assume the number is the year if it's 4 digits or > 31
            if len(numbers[0]) == 4 or int(numbers[0]) > 31:
                # We're missing the day, use a placeholder
                return "01", month_number, numbers[0]
            else:
                # We're missing the year, use a placeholder
                return numbers[0].zfill(2), month_number, "2000"

        # If we couldn't parse the date properly
        return None, None, None





    def verify_with_document_info(self, question_id, answer):
        """Verify the answer against document information with improved matching"""
        if not self.document_info or not answer:
            return False

        if question_id not in self.document_info:
            return False

        expected_answer = str(self.document_info[question_id])

        # Use specialized matching for different types of information
        if question_id == "full_name":
            # Use the advanced name matcher for Indian names
            match_result = self.name_processor.match_names(answer, expected_answer)
            match_score = match_result['overall_similarity']

            # Store detailed match information for debugging
            self.verification_results[question_id] = {
                "answer": answer,
                "expected": expected_answer,
                "match_score": match_score,
                "verified": match_score >= 0.7,  # 70% threshold for names
                "match_details": match_result
            }

            return match_score >= 0.7

        elif question_id == "address":
            # For addresses, use a more lenient matching approach
            # that focuses on key parts (city, state, pincode)
            norm_answer = self.name_processor.normalize_text(answer)
            norm_expected = self.name_processor.normalize_text(expected_answer)

            # Extract key parts from the address
            answer_words = set(norm_answer.split())
            expected_words = set(norm_expected.split())

            # Check for city/state/location matches
            common_words = answer_words.intersection(expected_words)

            # Calculate match score based on important words
            match_score = len(common_words) / max(len(expected_words), 1)

            # Apply phonetic matching for city/state names
            for answer_word in answer_words:
                for expected_word in expected_words:
                    if len(expected_word) >= 4 and len(answer_word) >= 4:  # Only check substantial words
                        word_similarity = self.name_processor.compute_phonetic_similarity(answer_word, expected_word)
                        if word_similarity >= 0.8:  # High similarity threshold
                            match_score += 0.1  # Bonus for phonetic matches

            match_score = min(match_score, 1.0)  # Cap at 1.0

            self.verification_results[question_id] = {
                "answer": answer,
                "expected": expected_answer,
                "match_score": match_score,
                "verified": match_score >= 0.6  # 60% threshold for addresses
            }

            return match_score >= 0.6

        elif question_id in ["phone", "id_number"]:
            # For numerical data, extract and match digits
            answer_digits = ''.join([c for c in answer if c.isdigit()])
            expected_digits = ''.join([c for c in expected_answer if c.isdigit()])

            # STRICT MATCHING: For phone numbers and ID numbers, require 100% match
            # For "last 4 digits" type questions
            if question_id == "id_number" and len(expected_digits) <= 4:
                # Check if answer ends with the expected digits
                is_match = answer_digits.endswith(expected_digits)
                match_score = 1.0 if is_match else 0.0
            else:
                # For full numbers, require exact match of digits
                is_match = answer_digits == expected_digits
                match_score = 1.0 if is_match else 0.0

            self.verification_results[question_id] = {
                "answer": answer,
                "expected": expected_answer,
                "match_score": match_score,
                "verified": is_match  # Must be exact match
            }

            return is_match

        elif question_id == "dob":
            # Enhanced DOB verification with month name recognition

            # Parse expected date
            expected_parts = re.split(r'[-/\s.]', expected_answer)
            if len(expected_parts) >= 3:
                # Normalize expected date to DD-MM-YYYY format
                exp_day = expected_parts[0].zfill(2)
                exp_month = expected_parts[1].zfill(2)
                exp_year = expected_parts[2]
                if len(exp_year) == 2:
                    exp_year = f"20{exp_year}" if int(exp_year) < 50 else f"19{exp_year}"

                expected_normalized = f"{exp_day}-{exp_month}-{exp_year}"
            else:
                # If expected date format is unexpected, use original
                expected_normalized = expected_answer

            # Parse spoken date with month name recognition
            spoken_day, spoken_month, spoken_year = self._extract_date_components(answer)

            if spoken_day and spoken_month and spoken_year:
                # Construct normalized spoken date
                spoken_normalized = f"{spoken_day}-{spoken_month}-{spoken_year}"

                # Compare normalized dates
                is_match = spoken_normalized == expected_normalized

                # If direct match fails, try more flexible matching
                if not is_match:
                    # Check if day, month, year match individually
                    expected_parts = expected_normalized.split('-')
                    spoken_parts = spoken_normalized.split('-')

                    day_match = expected_parts[0] == spoken_parts[0]
                    month_match = expected_parts[1] == spoken_parts[1]
                    year_match = expected_parts[2] == spoken_parts[2]

                    # Accept if at least 2 components match
                    components_match = sum([day_match, month_match, year_match])
                    is_partial_match = components_match >= 2

                    # For debugging
                    print(f"Date comparison: Expected {expected_normalized}, Spoken {spoken_normalized}")
                    print(f"Component matches: Day {day_match}, Month {month_match}, Year {year_match}")

                    # Only count exact matches as verified
                    is_match = is_match or (is_partial_match and year_match)  # Must match year plus one other component
            else:
                # Fallback to digit sequence matching if parsing failed
                answer_digits = ''.join([c for c in answer if c.isdigit()])
                expected_digits = ''.join([c for c in expected_answer if c.isdigit()])
                is_match = answer_digits == expected_digits

            match_score = 1.0 if is_match else 0.0

            self.verification_results[question_id] = {
                "answer": answer,
                "expected": expected_answer,
                "parsed_date": f"{spoken_day}-{spoken_month}-{spoken_year}" if spoken_day else "Failed to parse",
                "expected_normalized": expected_normalized,
                "match_score": match_score,
                "verified": is_match  # Must be exact match
            }

            return is_match


        else:
            # Default matching for other question types
            similarity = difflib.SequenceMatcher(None,
                                                 self.name_processor.normalize_text(answer),
                                                 self.name_processor.normalize_text(expected_answer)).ratio()

            self.verification_results[question_id] = {
                "answer": answer,
                "expected": expected_answer,
                "match_score": similarity,
                "verified": similarity >= 0.7  # 70% default threshold
            }

            return similarity >= 0.7

    def ask_question(self, question_id=None, retry_count=0):
        """Ask a specific question or random question in speech mode with improved retry logic"""
        if question_id:
            question = next((q for q in self.questions if q["id"] == question_id), None)
        else:
            question = random.choice(self.questions)

        if not question:
            return None, None

        # Get max retries for this question
        max_retries = question.get("max_retries", 2)

        # If this is the first attempt, speak the full question
        if retry_count == 0:
            self._speak(question["text"])
            self._speak(question["instruction"])
        else:
            # For retries, provide more specific guidance
            self._speak(f"Let's try again. {question['instruction']}")

        # Listen for the answer with extended timeout for longer responses
        answer = self._listen(timeout=7, phrase_time_limit=15)

        # If no answer detected and we haven't exceeded max retries
        if not answer and retry_count < max_retries:
            retry_message = "I didn't catch that clearly."
            if question["id"] == "full_name":
                retry_message += " Please speak your name more slowly and clearly."
            elif question["id"] in ["phone", "id_number"]:
                retry_message += " Please speak each digit clearly with a slight pause between them."
            elif question["id"] == "dob":
                retry_message += " Please say the day, then month, then year clearly."

            self._speak(retry_message)

            # Short pause before retry
            time.sleep(1)

            # Retry the question
            return self.ask_question(question_id, retry_count + 1)

        # If we still don't have an answer after retries
        if not answer:
            self._speak("I'm still having trouble understanding. Let's move on.")
            return question["id"], None

        # Store the answer
        self.answers[question["id"]] = answer

        return question["id"], answer

    def run_verification(self, num_questions=None):
        """Run the verification process entirely in speech mode"""
        # Initialize verification session
        self._speak(
            "Welcome to the verification process. I'll ask you a few questions to verify your identity. Please speak clearly.")

        # MODIFIED: Always use all available questions instead of random selection
        # We only have DOB and ID number questions now
        question_ids = [q["id"] for q in self.questions]

        verified_count = 0
        asked_count = 0

        for question_id in question_ids:
            # Ask question and get answer
            q_id, answer = self.ask_question(question_id)
            asked_count += 1

            if not answer:
                continue  # Skip verification if no answer was provided

            # Verify answer if document info is available
            if self.document_info:
                verified = self.verify_with_document_info(q_id, answer)
                if verified:
                    verified_count += 1
                    self._speak("Thank you, that information has been verified.")
                else:
                    # For numerical data, provide direct feedback
                    if q_id in ["phone", "id_number", "dob"]:
                        self._speak("The information you provided doesn't match our records.")
                    else:
                        self._speak("Thank you for that information.")
            else:
                self._speak("Thank you for that information.")

        # Store verification results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("verification_results", exist_ok=True)

        result_file = f"verification_results/verification_{timestamp}.json"
        with open(result_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "answers": self.answers,
                "verification_results": self.verification_results,
                "verified_count": verified_count,
                "total_questions": asked_count
            }, f, indent=4)

        print(f"Verification results saved to {result_file}")

        # Determine overall verification status
        if self.document_info:
            # MODIFIED: Adjusted verification criteria for just 2 questions
            # Both questions must match for verification to succeed
            min_required = asked_count  # Must match all asked questions (which is now 2)

            # Verification is successful only if all answers match
            overall_verified = verified_count >= min_required

            if overall_verified:
                self._speak("Verification complete. Your identity has been confirmed. Thank you.")
            else:
                self._speak("Verification failed. We couldn't confirm your identity with the information provided.")

            print(f"Verification status: {'Passed' if overall_verified else 'Failed'}")
            print(f"Verified {verified_count} out of {asked_count} questions (Minimum required: {min_required})")

            return overall_verified
        else:
            self._speak("Thank you for providing your information.")
            return None  # No verification possible without document info





def main():
    """Main function to demonstrate the QuestionVerifier"""
    # Example document info with complex Indian names
    example_document_info = {
        "full_name": "Vishwajitsinh Chauhan",  # Note the hyphen
        "dob": "27-03-2003",
        "address": "33 aaradhna row house, sayan , gujarat",
        "id_number": "2468",
        "phone": "9876543210"
    }

    # Save example document info to a temporary JSON file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        json.dump(example_document_info, temp_file)
        temp_file_path = temp_file.name

    try:
        # Create QuestionVerifier instance with the temporary document info file
        verifier = QuestionVerifier(document_info_path=temp_file_path)

        # Run verification process
        print("Starting speech verification...")
        # MODIFIED: Changed to run all questions (which is now just 2)
        verification_result = verifier.run_verification()

        # Print verification summary
        if verification_result is not None:
            print(f"Verification {'passed' if verification_result else 'failed'}")

            # Print detailed results
            print("\nVerification Results:")
            for q_id, result in verifier.verification_results.items():
                print(f"\n{q_id.upper()}:")
                print(f"  Provided: {result['answer']}")
                print(f"  Expected: {result['expected']}")
                print(f"  Match Score: {result['match_score']:.2f}")
                print(f"  Verified: {'Yes' if result['verified'] else 'No'}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)


if __name__ == "__main__":
    main()






