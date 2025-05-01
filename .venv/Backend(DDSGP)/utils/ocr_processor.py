import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import re
from datetime import datetime

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_photo_from_aadhar(image):
    """Extract photo from Aadhar card"""
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply face detection using Haar Cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) > 0:
            # Get the first detected face
            x, y, w, h = faces[0]

            # Extract face region with some padding
            padding = 20
            face_img = image[max(0, y-padding):min(y+h+padding, image.shape[0]),
                           max(0, x-padding):min(x+w+padding, image.shape[1])]

            # Convert to PIL Image
            face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(face_img_rgb)

            # Save to bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            return img_byte_arr

        return None
    except Exception as e:
        print(f"Error extracting photo: {str(e)}")
        return None

def extract_text_from_upload(uploaded_file):
    try:
        # Read image from uploaded file
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if image is None:
            return "Error: Unable to process image."

        # Extract photo first
        photo = extract_photo_from_aadhar(image.copy())

        # Convert to grayscale for text extraction
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply denoising
        gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)

        # Resize image
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Apply adaptive thresholding
        gray = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 2
        )

        # Apply morphological operations
        kernel = np.ones((1, 1), np.uint8)
        gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

        # Extract text using Tesseract
        custom_config = "--dpi 300"
        text = pytesseract.image_to_string(gray, lang='eng', config=custom_config)

        # Process extracted text
        extracted_info = process_extracted_text(text.strip())

        # Add photo to extracted info
        extracted_info['photo'] = photo

        extracted_info = process_extracted_text(text.strip())
        extracted_info['photo'] = photo

        return extracted_info
    except Exception as e:
        # Return a dictionary with error information
        return {
            'name': None,
            'id_number': None,
            'date_of_birth': None,
            'address': None,
            'raw_text': str(e),
            'photo': None,
            'error': str(e)
        }

def find_aadhar_number(text):
    # Pattern for 12-digit Aadhar number
    pattern = r'\b[2-9]{1}[0-9]{3}\s*[0-9]{4}\s*[0-9]{4}\b'
    matches = re.findall(pattern, text.replace('\n', ' '))
    if matches:
        # Remove spaces and return first match
        return ''.join(matches[0].split())
    return None

def find_dob(text):
    # Simple pattern to match XX/XX/XXXX format
    date_pattern = r'\d{2}/\d{2}/\d{4}'
    matches = re.findall(date_pattern, text)
    if matches:
        return matches[0]  # Return the first date found
    return None

def find_name(text):
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Look for DOB line with more patterns
        if any(dob_pattern in line.lower() for dob_pattern in ['dob:', 'date of birth:', 'rluvdob:', 'aduiidob', 'on aduii']):
            name_parts = []

            # Check one and two lines above DOB
            if i > 0:
                one_line_above = lines[i-1].strip()
                # Exclude lines with these words and check if line is not empty
                if (not any(word in one_line_above.lower() for word in ['cott', 'atdlvt', 'dob', 'birth'])
                    and len(one_line_above) > 0):
                    name_parts.append(one_line_above)

            if i > 1:
                two_lines_above = lines[i-2].strip()
                if len(two_lines_above) > 0:
                    name_parts.append(two_lines_above)

            if name_parts:
                # Join the name parts and clean up
                full_name = ' '.join(reversed(name_parts))  # Reverse to get correct order
                # Remove any text after special characters
                for char in ['/', '&', 'g']:
                    if char in full_name:
                        full_name = full_name.split(char)[0]
                # Clean up the name
                full_name = full_name.strip()
                # Remove common prefixes if they exist
                prefixes = ['Name:', 'NAME:']
                for prefix in prefixes:
                    if prefix in full_name:
                        full_name = full_name.split(prefix)[1]
                return full_name.strip()

        # Also check for explicit name labels as fallback
        if "Name:" in line:
            name = line.split("Name:")[-1].strip()
            if name.lower() != 'none':  # Skip if name is "None"
                return name.strip()

    # If no name found with above methods, look for all caps words that could be names
    for line in lines:
        line = line.strip()
        if (line.isupper() and
            len(line) > 5 and
            not any(char.isdigit() for char in line) and
            not any(word in line for word in ['GOVERNMENT', 'INDIA', 'UNIQUE', 'IDENTIFICATION', 'AUTHORITY'])):
            return line

    return None

def process_extracted_text(text):
    """Process the extracted text to identify key information"""
    info = {
        'name': None,
        'id_number': None,
        'date_of_birth': None,
        'address': None,
        'raw_text': text
    }

    # Find Aadhar number
    aadhar_number = find_aadhar_number(text)
    if aadhar_number:
        info['id_number'] = aadhar_number

    # Find name
    name = find_name(text)
    if name:
        info['name'] = name

    # Find date of birth
    dob = find_dob(text)
    if dob:
        info['date_of_birth'] = dob

    # Find address
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        # Look for address indicators
        if any(word in line.lower() for word in ['address:', 'add:', 'residence:']):
            # Take this line and the next line as address
            address_parts = []
            address_parts.append(line.split(':', 1)[1] if ':' in line else line)
            if i + 1 < len(lines):
                address_parts.append(lines[i + 1].strip())
            info['address'] = ' '.join(address_parts).strip()
            break
        # Long line with address-like words
        elif (len(line) > 30 and
              any(word in line.lower() for word in ['street', 'road', 'avenue', 'lane', 'district', 'village', 'city', 'state', 'pin'])):
            info['address'] = line
            break

    return info