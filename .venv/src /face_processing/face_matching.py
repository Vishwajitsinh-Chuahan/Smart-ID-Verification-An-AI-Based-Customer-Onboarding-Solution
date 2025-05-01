import cv2
import numpy as np
import os
import time
from datetime import datetime
import tensorflow as tf
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
import mediapipe as mp
import matplotlib

matplotlib.use('TkAgg')  # Use TkAgg backend for matplotlib

# Suppress TensorFlow logging
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Hides all TF info logs



# Ensure we're using GPU if available
physical_devices = tf.config.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
    print("Using GPU for inference")
else:
    print("Using CPU for inference")


class LivenessDetector:
    """MediaPipe-based liveness detection with eye blinks and head movement"""

    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # States
        self.state = "WAITING"
        self.blink_count = 0
        self.blink_threshold = 2  # User must blink twice
        self.head_movement_detected = False
        self.nose_start_x = None  # To track relative head movement

        # Blink Detection
        self.ear_threshold = 0.22  # Adaptive threshold
        self.blink_flag = False  # Ensures counting only complete blinks
        self.last_blink_time = 0  # To prevent counting multiple blinks too quickly

        # Instructions
        self.instructions = {
            "WAITING": "Position your face in the frame",
            "BLINK": "Please blink twice",
            "HEAD_MOVEMENT": "Turn head left and right slowly",
            "COMPLETE": "Verification Complete!"
        }

    def _draw_face_mesh(self, frame, landmarks):
        """Draw the face mesh landmarks on the frame"""
        self.mp_drawing.draw_landmarks(
            image=frame,
            landmark_list=landmarks,
            connections=self.mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=self.mp_drawing_styles
            .get_default_face_mesh_tesselation_style()
        )

    def _calculate_ear(self, landmarks, eye_indices):
        """Calculate Eye Aspect Ratio (EAR) to detect blinks"""
        p1 = landmarks.landmark[eye_indices[0]]  # Top
        p2 = landmarks.landmark[eye_indices[1]]  # Bottom
        p3 = landmarks.landmark[eye_indices[2]]  # Left corner
        p4 = landmarks.landmark[eye_indices[3]]  # Right corner

        # Euclidean distances
        vertical_dist = abs(p1.y - p2.y)
        horizontal_dist = abs(p3.x - p4.x)

        # Prevent division by zero
        if horizontal_dist < 0.001:
            return 1.0

        return vertical_dist / horizontal_dist  # EAR Formula

    def _detect_eye_blink(self, landmarks):
        """Detect if a valid blink has occurred"""
        left_eye_indices = [159, 145, 33, 133]  # Top, Bottom, Left, Right
        right_eye_indices = [386, 374, 362, 263]

        left_ear = self._calculate_ear(landmarks, left_eye_indices)
        right_ear = self._calculate_ear(landmarks, right_eye_indices)
        avg_ear = (left_ear + right_ear) / 2  # Average EAR

        current_time = time.time()

        # Require at least 0.3 seconds between blinks
        if avg_ear < self.ear_threshold:
            if not self.blink_flag and (current_time - self.last_blink_time) > 0.3:
                self.blink_flag = True
                self.last_blink_time = current_time
                return True  # Blink detected
        else:
            self.blink_flag = False  # Reset flag when eyes reopen

        return False

    def _detect_head_movement(self, landmarks):
        """Detect significant head movement by tracking nose position"""
        nose_x = landmarks.landmark[1].x  # Nose center

        if self.nose_start_x is None:
            self.nose_start_x = nose_x  # Set initial position
            return False

        movement = abs(nose_x - self.nose_start_x)

        # If we detect significant movement, return true
        if movement > 0.05:  # Adjust threshold for sensitivity
            return True

        return False

    def _extract_face_from_landmarks(self, frame, landmarks):
        """Extract face region based on landmarks"""
        h, w = frame.shape[:2]

        # Get face bounding box from landmarks
        x_coordinates = [landmark.x for landmark in landmarks.landmark]
        y_coordinates = [landmark.y for landmark in landmarks.landmark]

        x_min = max(0, int(min(x_coordinates) * w) - 10)
        y_min = max(0, int(min(y_coordinates) * h) - 10)
        x_max = min(w, int(max(x_coordinates) * w) + 10)
        y_max = min(h, int(max(y_coordinates) * h) + 10)

        # Extract face region
        face_image = frame[y_min:y_max, x_min:x_max]

        return face_image, [x_min, y_min, x_max, y_max]

    def _handle_state(self, landmarks):
        """Manage state transitions based on detected actions"""
        if self.state == "WAITING":
            self.state = "BLINK"
            return self.state, self.instructions[self.state]

        elif self.state == "BLINK":
            if self._detect_eye_blink(landmarks):
                self.blink_count += 1
                print(f"Blink Detected: {self.blink_count}")

            if self.blink_count >= self.blink_threshold:
                self.state = "HEAD_MOVEMENT"
                return self.state, self.instructions[self.state]

        elif self.state == "HEAD_MOVEMENT":
            if self._detect_head_movement(landmarks):
                self.head_movement_detected = True

            if self.head_movement_detected:
                self.state = "COMPLETE"
                return self.state, self.instructions[self.state]

        return self.state, self.instructions[self.state]

    def process_frame(self, frame):
        """Process a video frame for liveness detection"""
        if frame is None:
            return False, "ERROR", "Invalid frame received", None

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                self._draw_face_mesh(frame, face_landmarks)

                # Extract face for quality assessment
                face_image, bbox = self._extract_face_from_landmarks(frame, face_landmarks)

                state, message = self._handle_state(face_landmarks)
                return True, state, message, bbox

        return False, "DETECTING", "No face detected", None


class FaceVerificationSystem:
    def __init__(self):
        print("Initializing Face Verification System...")

        # Load face detector
        print("Loading MTCNN face detector...")
        from mtcnn import MTCNN
        self.detector = MTCNN()

        # Load face recognition model
        print("Loading InsightFace model...")
        import insightface
        from insightface.app import FaceAnalysis
        self.face_analyzer = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))

        # Initialize liveness detector
        self.liveness_detector = LivenessDetector()

        # Set threshold for face matching
        self.threshold = 0.45
        print("Face Verification System initialized successfully!")

    def load_image_from_file(self, image_path):
        """Load image from file path"""
        if not os.path.exists(image_path):
            print(f"Error: Image file not found at {image_path}")
            return None

        print(f"Loading ID card image from: {image_path}")
        image = cv2.imread(image_path)
        if image is None:
            print("Error: Could not read the image file")
            return None

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image_rgb

    def perform_liveness_detection(self):
        """Perform liveness detection with matplotlib feedback"""
        print("Initializing webcam for liveness detection...")
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Error: Could not open webcam")
            return None

        # Set webcam resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print("Liveness detection started")
        print("Please look at the camera and follow the on-screen instructions")

        # Initialize matplotlib for display
        plt.ion()  # Turn on interactive mode
        fig, ax = plt.subplots(figsize=(10, 6))
        img_display = ax.imshow(np.zeros((720, 1280, 3), dtype=np.uint8))
        title_obj = plt.title("Liveness Detection")
        status_text = ax.text(0.02, 0.95, "", transform=ax.transAxes, color='green', fontsize=12)
        message_text = ax.text(0.02, 0.90, "", transform=ax.transAxes, color='green', fontsize=12)
        blink_text = ax.text(0.02, 0.85, "", transform=ax.transAxes, color='red', fontsize=12)
        head_text = ax.text(0.02, 0.80, "", transform=ax.transAxes, color='blue', fontsize=12)
        time_text = ax.text(0.02, 0.75, "", transform=ax.transAxes, color='blue', fontsize=12)
        plt.tight_layout()

        start_time = time.time()
        timeout = 30  # 30 second timeout
        final_frame = None
        best_frame = None  # We'll still track this for debugging purposes

        # Frame counter for processing every few frames (reduces CPU load)
        frame_counter = 0
        process_every_n_frames = 2

        try:
            while True:
                # Check for timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    print("Timeout: Liveness detection failed")
                    # FIXED: Do not use best_frame on timeout - always fail
                    cap.release()
                    plt.close(fig)
                    return None

                # Read frame
                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to capture image from webcam")
                    break

                # Only process every n frames to reduce CPU load
                frame_counter += 1
                if frame_counter % process_every_n_frames != 0 and self.liveness_detector.state != "COMPLETE":
                    # Still update the display
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_display.set_array(frame_rgb)
                    time_left = int(timeout - elapsed_time)
                    time_text.set_text(f"Time left: {time_left}s")
                    fig.canvas.draw_idle()
                    fig.canvas.flush_events()
                    time.sleep(0.01)
                    continue

                # Process frame for liveness detection
                success, state, message, bbox = self.liveness_detector.process_frame(frame)

                # If we detect a face, store this as a potential return frame (still tracking for debug)
                if success and bbox is not None:
                    best_frame = frame.copy()

                # Convert frame to RGB for matplotlib
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Draw face bounding box if detected
                if bbox is not None:
                    cv2.rectangle(frame_rgb, (bbox[0], bbox[1]), (bbox[2], bbox[3]),
                                  (0, 255, 0), 2)

                # Update matplotlib display
                img_display.set_array(frame_rgb)
                status_text.set_text(f"Status: {state}")
                message_text.set_text(f"Message: {message}")
                blink_text.set_text(
                    f"Blinks: {self.liveness_detector.blink_count}/{self.liveness_detector.blink_threshold}")

                # Update head movement status
                head_status = "Head Movement: "
                if self.liveness_detector.head_movement_detected:
                    head_status += "Detected"
                    head_text.set_color('green')
                else:
                    head_status += "Not Detected"
                    head_text.set_color('red')
                head_text.set_text(head_status)

                # Update time left
                time_left = int(timeout - elapsed_time)
                time_text.set_text(f"Time left: {time_left}s")

                # Draw the plot
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

                # Check if liveness checks passed
                if state == "COMPLETE":
                    print("Liveness detection successful!")
                    final_frame = frame.copy()
                    time.sleep(1)  # Brief pause to show completion
                    break

                # Brief sleep to reduce CPU usage
                time.sleep(0.01)

        except Exception as e:
            print(f"Error during liveness detection: {e}")
            cap.release()
            plt.close(fig)
            return None

        finally:
            # Cleanup
            cap.release()
            plt.close(fig)

        if final_frame is not None:
            return cv2.cvtColor(final_frame, cv2.COLOR_BGR2RGB)
        return None

    def extract_face_embedding(self, image):
        """Extract face embedding from image with enhanced face detection"""
        if image is None:
            return None

        # Try InsightFace first for detection and feature extraction
        faces = self.face_analyzer.get(image)

        if not faces:
            print("InsightFace didn't detect any faces, trying MTCNN as fallback...")
            # Fallback to MTCNN if InsightFace fails
            mtcnn_faces = self.detector.detect_faces(image)

            if not mtcnn_faces:
                print("No face detected in the image with either method")
                return None

            # Get the largest face by confidence
            largest_face = max(mtcnn_faces, key=lambda x: x['confidence'])

            # Extract face using bounding box
            x, y, w, h = largest_face['box']
            # Ensure coordinates are valid
            x, y = max(0, x), max(0, y)
            face_image = image[y:y + h, x:x + w]

            # Try again with the cropped face
            face_image_rgb = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB) if len(face_image.shape) == 3 else face_image
            faces = self.face_analyzer.get(face_image_rgb)

            if not faces:
                print("Failed to extract embedding even with cropped face")
                return None

        # Get the largest face if multiple faces are detected
        if len(faces) > 1:
            print(f"Multiple faces ({len(faces)}) detected, using the largest one")
            # Sort faces by bbox area (width * height)
            faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)

        # Extract the embedding
        face_embedding = faces[0].embedding

        # Get the face bounding box for visualization
        bbox = faces[0].bbox.astype(int)

        # Ensure bbox is within image boundaries
        h, w = image.shape[:2]
        bbox[0] = max(0, bbox[0])
        bbox[1] = max(0, bbox[1])
        bbox[2] = min(w, bbox[2])
        bbox[3] = min(h, bbox[3])

        # Extract face image
        face_image = image[bbox[1]:bbox[3], bbox[0]:bbox[2]]

        return {
            'embedding': face_embedding,
            'bbox': bbox,
            'face_image': face_image
        }

    def verify_faces(self, id_embedding, webcam_embedding):
        """Compare face embeddings and determine if they match"""
        if id_embedding is None or webcam_embedding is None:
            return False, 0.0

        # Calculate cosine similarity
        similarity = cosine_similarity([id_embedding], [webcam_embedding])[0][0]
        match = similarity > self.threshold

        return match, similarity

    def save_results(self, id_image, webcam_image, id_face_data, webcam_face_data, match, similarity):
        """Save verification results with visualizations"""
        if id_image is None or webcam_image is None:
            print("Cannot save results due to missing images")
            return

        try:
            plt.figure(figsize=(12, 8))

            # ID Card Image
            plt.subplot(2, 2, 1)
            plt.title("ID Card Image")
            plt.imshow(id_image)
            plt.axis('off')

            if id_face_data is not None:
                bbox = id_face_data['bbox']
                # Draw bounding box on the original image
                id_display = id_image.copy()
                cv2.rectangle(id_display, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                plt.imshow(id_display)

            # Webcam Image
            plt.subplot(2, 2, 2)
            plt.title("Webcam Image")
            plt.imshow(webcam_image)
            plt.axis('off')

            if webcam_face_data is not None:
                bbox = webcam_face_data['bbox']
                # Draw bounding box on the original image
                webcam_display = webcam_image.copy()
                cv2.rectangle(webcam_display, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                plt.imshow(webcam_display)

            # Extracted Face from ID
            plt.subplot(2, 2, 3)
            plt.title("ID Card Face")
            if id_face_data is not None:
                plt.imshow(id_face_data['face_image'])
            plt.axis('off')

            # Extracted Face from Webcam
            plt.subplot(2, 2, 4)
            plt.title("Webcam Face")
            if webcam_face_data is not None:
                plt.imshow(webcam_face_data['face_image'])
            plt.axis('off')

            # Display match result and similarity score
            result_text = f"MATCH: {match} (Similarity: {similarity:.4f}, Threshold: {self.threshold})"
            plt.figtext(0.5, 0.02, result_text, ha="center", fontsize=14,
                        bbox={"facecolor": "green" if match else "red", "alpha": 0.5, "pad": 5})

            plt.tight_layout()

            # Create results directory if it doesn't exist
            os.makedirs("verification_results", exist_ok=True)

            # Save the figure
            result_filename = f"verification_results/result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(result_filename)
            plt.close()

            print(f"Results saved to {result_filename}")

            # Also save individual face images
            if id_face_data is not None:
                id_face_filename = f"verification_results/id_face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.imsave(id_face_filename, id_face_data['face_image'])

            if webcam_face_data is not None:
                webcam_face_filename = f"verification_results/webcam_face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.imsave(webcam_face_filename, webcam_face_data['face_image'])

        except Exception as e:
            print(f"Error saving results: {e}")


    def display_verification_result(self, id_image, webcam_image, id_face_data, webcam_face_data, match, similarity):
        """Display verification results in a matplotlib window"""
        if id_image is None or webcam_image is None:
            print("Cannot display results due to missing images")
            return

        try:
            plt.figure(figsize=(12, 8))

            # ID Card Image
            plt.subplot(2, 2, 1)
            plt.title("ID Card Image")
            if id_face_data is not None:
                bbox = id_face_data['bbox']
                # Draw bounding box on the original image
                id_display = id_image.copy()
                cv2.rectangle(id_display, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                plt.imshow(id_display)
            else:
                plt.imshow(id_image)
            plt.axis('off')

            # Webcam Image
            plt.subplot(2, 2, 2)
            plt.title("Webcam Image")
            if webcam_face_data is not None:
                bbox = webcam_face_data['bbox']
                # Draw bounding box on the original image
                webcam_display = webcam_image.copy()
                cv2.rectangle(webcam_display, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                plt.imshow(webcam_display)
            else:
                plt.imshow(webcam_image)
            plt.axis('off')

            # Extracted Face from ID
            plt.subplot(2, 2, 3)
            plt.title("ID Card Face")
            if id_face_data is not None:
                plt.imshow(id_face_data['face_image'])
            plt.axis('off')

            # Extracted Face from Webcam
            plt.subplot(2, 2, 4)
            plt.title("Webcam Face")
            if webcam_face_data is not None:
                plt.imshow(webcam_face_data['face_image'])
            plt.axis('off')

            # Display match result and similarity score
            result_text = f"MATCH: {match} (Similarity: {similarity:.4f}, Threshold: {self.threshold})"
            plt.figtext(0.5, 0.02, result_text, ha="center", fontsize=14,
                        bbox={"facecolor": "green" if match else "red", "alpha": 0.5, "pad": 5})

            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"Error displaying results: {e}")
# ----without numpy
    # def run_verification(self, id_image_path):
    #     """Run the complete verification process"""
    #     print("\n===== Starting Face Verification Process =====\n")
    #
    #     # Step 1: Load ID card image
    #     id_image = self.load_image_from_file(id_image_path)
    #     if id_image is None:
    #         print("Verification failed: Could not load ID card image")
    #         return
    #
    #     # Step 2: Run liveness detection and capture webcam image
    #     print("\n===== Starting Liveness Detection =====")
    #     webcam_image = self.perform_liveness_detection()
    #     if webcam_image is None:
    #         print("Verification failed: Liveness detection timed out or was unsuccessful")
    #         return
    #
    #     # Step 3: Extract face embeddings
    #     print("Extracting face from ID card...")
    #     id_face_data = self.extract_face_embedding(id_image)
    #     if id_face_data is None:
    #         print("Verification failed: No face detected in ID card image")
    #         return
    #
    #     print("Extracting face from webcam image...")
    #     webcam_face_data = self.extract_face_embedding(webcam_image)
    #     if webcam_face_data is None:
    #         print("Verification failed: No face detected in webcam image")
    #         return
    #
    #     # Step 4: Compare faces
    #     print("Comparing faces...")
    #     match, similarity = self.verify_faces(id_face_data['embedding'], webcam_face_data['embedding'])
    #
    #     # Step 5: Display results
    #     print("\n===== Verification Results =====")
    #     print(f"Similarity Score: {similarity:.4f}")
    #     print(f"Threshold: {self.threshold}")
    #     if match:
    #         print("RESULT: MATCH - The face in the webcam matches the face on the ID card")
    #     else:
    #         print("RESULT: NO MATCH - The face in the webcam does not match the face on the ID card")
    #
    #     # Display the results
    #     self.display_verification_result(id_image, webcam_image, id_face_data, webcam_face_data, match, similarity)
    #
    #     # Save the results
    #     self.save_results(id_image, webcam_image, id_face_data, webcam_face_data, match, similarity)
    #     return match, similarity

    # Add this to the run_verification method in the FaceVerificationSystem class
    # This modification ensures the method returns the match and similarity values


# ------this is first commment out
    def run_verification(self, id_image_path):
        """Run the complete verification process"""
        print("\n===== Starting Face Verification Process =====\n")

        # Step 1: Load ID card image
        id_image = self.load_image_from_file(id_image_path)
        if id_image is None:
            print("Verification failed: Could not load ID card image")
            return False, 0.0

        # Step 2: Run liveness detection and capture webcam image
        print("\n===== Starting Liveness Detection =====")
        webcam_image = self.perform_liveness_detection()
        if webcam_image is None:
            print("Verification failed: Liveness detection timed out or was unsuccessful")
            return False, 0.0

        # Step 3: Extract face embeddings
        print("Extracting face from ID card...")
        id_face_data = self.extract_face_embedding(id_image)
        if id_face_data is None:
            print("Verification failed: No face detected in ID card image")
            return False, 0.0

        print("Extracting face from webcam image...")
        webcam_face_data = self.extract_face_embedding(webcam_image)
        if webcam_face_data is None:
            print("Verification failed: No face detected in webcam image")
            return False, 0.0

        # Step 4: Compare faces
        print("Comparing faces...")
        match, similarity = self.verify_faces(id_face_data['embedding'], webcam_face_data['embedding'])

        # Convert numpy types to Python native types
        if isinstance(similarity, np.floating):
            similarity = float(similarity)

        if isinstance(match, np.bool_):
            match = bool(match)

        # Step 5: Display results
        print("\n===== Verification Results =====")
        print(f"Similarity Score: {similarity:.4f}")
        print(f"Threshold: {self.threshold}")
        if match:
            print("RESULT: MATCH - The face in the webcam matches the face on the ID card")
        else:
            print("RESULT: NO MATCH - The face in the webcam does not match the face on the ID card")

        # Display the results
        self.display_verification_result(id_image, webcam_image, id_face_data, webcam_face_data, match, similarity)

        # Save the results but don't return the file paths
        self.save_results(id_image, webcam_image, id_face_data, webcam_face_data, match, similarity)

        return match, similarity
