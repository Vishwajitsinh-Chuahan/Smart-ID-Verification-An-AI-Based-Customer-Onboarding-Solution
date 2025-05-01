from flask import Flask, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import base64
import io
import os
import json

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aadhar_information.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Define the AadharRecord model
class Aadhar_Record(db.Model):
    __tablename__ = 'aadhar_record'
    id = db.Column(db.Integer, primary_key=True)
    aadhar_number = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.String(10), nullable=False)
    photo = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'aadhar_number': self.aadhar_number,
            'name': self.name,
            'date_of_birth': self.date_of_birth,
            'created_at': self.created_at.isoformat()
        }


# Define the VerificationResult model
class VerificationResult(db.Model):
    __tablename__ = 'verification_results'
    id = db.Column(db.Integer, primary_key=True)
    aadhar_number = db.Column(db.String(12), db.ForeignKey('aadhar_record.aadhar_number'), nullable=False)
    face_similarity = db.Column(db.Float, nullable=True)
    verification_passed = db.Column(db.Boolean, default=False)
    verification_time = db.Column(db.DateTime, default=datetime.utcnow)
    id_image_path = db.Column(db.Text, nullable=True)
    webcam_image_path = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'aadhar_number': self.aadhar_number,
            'face_similarity': self.face_similarity,
            'verification_passed': self.verification_passed,
            'verification_time': self.verification_time.isoformat(),
            'id_image_path': self.id_image_path,
            'webcam_image_path': self.webcam_image_path
        }


# Define the QuestionVerificationResult model
class QuestionVerificationResult(db.Model):
    """Table for storing question verification results"""
    __tablename__ = 'question_verification_results'
    id = db.Column(db.Integer, primary_key=True)
    aadhar_number = db.Column(db.String(12), db.ForeignKey('aadhar_record.aadhar_number'), nullable=False)
    verified_count = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    overall_verified = db.Column(db.Boolean, default=False)
    results_json = db.Column(db.Text, nullable=False)  # Store JSON with question details
    verification_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'aadhar_number': self.aadhar_number,
            'verified_count': self.verified_count,
            'total_questions': self.total_questions,
            'overall_verified': self.overall_verified,
            'verification_time': self.verification_time.isoformat()
        }


@app.route('/save_face_verification', methods=['POST'])
def save_face_verification():
    data = request.json
    aadhar_number = data.get("aadhar_number")
    face_similarity = data.get("face_similarity")
    verification_passed = data.get("verification_passed")

    # Validate required fields
    if not aadhar_number:
        return jsonify({'error': 'Aadhar number is required'}), 400

    try:
        result = VerificationResult(
            aadhar_number=aadhar_number,
            face_similarity=face_similarity,
            verification_passed=verification_passed
        )

        db.session.add(result)
        db.session.commit()
        return jsonify({'message': 'Face verification result saved successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Routes for Question Verification

@app.route('/api/get_aadhar_data/<aadhar_number>', methods=['GET'])
def get_aadhar_data(aadhar_number):
    """
    Retrieve user data based on Aadhar number
    This endpoint is called by the Streamlit app to fetch user details for verification
    """
    # Find the Aadhar record in the database
    aadhar_record = Aadhar_Record.query.filter_by(aadhar_number=aadhar_number).first()

    if not aadhar_record:
        return jsonify({'error': 'Aadhar record not found'}), 404

    # Return user data in the format expected by the Streamlit app
    user_data = {
        'aadhar_number': aadhar_record.aadhar_number,
        'name': aadhar_record.name,
        'dob': aadhar_record.date_of_birth,  # Note: adjusted field name to match your model
        # Add any other fields that might be needed for verification
    }

    return jsonify(user_data), 200


@app.route('/api/save_question_verification', methods=['POST'])
def save_question_verification():
    """
    Save the results of the question verification process
    This endpoint is called by the Streamlit app after completing the verification
    """
    # Get data from request
    data = request.json

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Extract required fields
    aadhar_number = data.get('aadhar_number')
    verified_count = data.get('verified_count')
    total_questions = data.get('total_questions')
    overall_verified = data.get('overall_verified')
    results_json = data.get('results_json')

    # Validate required fields
    if not all([aadhar_number, verified_count is not None, total_questions is not None,
                overall_verified is not None, results_json]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        # Check if the Aadhar number exists
        aadhar_record = Aadhar_Record.query.filter_by(aadhar_number=aadhar_number).first()
        if not aadhar_record:
            return jsonify({'error': 'Aadhar record not found'}), 404

        # Check if a verification result already exists for this Aadhar
        existing_record = QuestionVerificationResult.query.filter_by(aadhar_number=aadhar_number).first()

        if existing_record:
            # Update existing record
            existing_record.verified_count = verified_count
            existing_record.total_questions = total_questions
            existing_record.overall_verified = overall_verified
            existing_record.results_json = results_json
            existing_record.verification_time = datetime.utcnow()
        else:
            # Create new verification result
            new_verification = QuestionVerificationResult(
                aadhar_number=aadhar_number,
                verified_count=verified_count,
                total_questions=total_questions,
                overall_verified=overall_verified,
                results_json=results_json
            )
            db.session.add(new_verification)

        # Commit the changes
        db.session.commit()

        return jsonify({'message': 'Verification results saved successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@app.route('/verification_status/<aadhar_number>', methods=['GET'])
def get_verification_status(aadhar_number):
    """
    Get the current verification status for an Aadhar number
    Useful for checking if verification is complete or needs to be redone
    """
    try:
        # Find the verification record
        verification = QuestionVerificationResult.query.filter_by(aadhar_number=aadhar_number).first()

        if not verification:
            return jsonify({'status': 'not_verified', 'message': 'No verification record found'}), 200

        # Return the verification status and details
        status_data = {
            'status': 'verified' if verification.overall_verified else 'failed',
            'verified_count': verification.verified_count,
            'total_questions': verification.total_questions,
            'verification_time': verification.verification_time.isoformat(),
            'results': json.loads(verification.results_json) if verification.results_json else {}
        }

        return jsonify(status_data), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving verification status: {str(e)}'}), 500


# Create database tables
with app.app_context():
    db.create_all()


@app.route('/check_aadhar/<aadhar_number>', methods=['GET'])
def check_aadhar(aadhar_number):
    record = Aadhar_Record.query.filter_by(aadhar_number=aadhar_number).first()
    return jsonify({'exists': record is not None})


@app.route('/get_records', methods=['GET'])
def get_records():
    records = Aadhar_Record.query.all()
    return jsonify({
        'total_records': len(records),
        'records': [record.to_dict() for record in records]
    })


@app.route('/get_record/<aadhar_number>', methods=['GET'])
def get_record(aadhar_number):
    record = Aadhar_Record.query.filter_by(aadhar_number=aadhar_number).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    record_data = record.to_dict()
    if record.photo:
        record_data['photo'] = base64.b64encode(record.photo).decode('utf-8')

    return jsonify(record_data)


@app.route('/get_photo/<aadhar_number>', methods=['GET'])
def get_photo(aadhar_number):
    record = Aadhar_Record.query.filter_by(aadhar_number=aadhar_number).first()
    if not record or not record.photo:
        return jsonify({'error': 'Photo not found'}), 404

    return send_file(
        io.BytesIO(record.photo),
        mimetype='image/png',
        as_attachment=False,
        download_name=f'photo_{aadhar_number}.png'
    )


@app.route('/save_record', methods=['POST'])
def save_record():
    data = request.json

    # Check if Aadhar number already exists
    existing_record = Aadhar_Record.query.filter_by(aadhar_number=data['aadhar_number']).first()
    if existing_record:
        return jsonify({'error': 'Aadhar number already registered'}), 400

    # Convert base64 photo string to bytes
    photo_bytes = None
    if data.get('photo'):
        try:
            photo_bytes = base64.b64decode(data['photo'])
        except Exception as e:
            return jsonify({'error': f'Invalid photo data: {str(e)}'}), 400

    # Create new record
    new_record = Aadhar_Record(
        aadhar_number=data['aadhar_number'],
        name=data.get('name'),
        date_of_birth=data['date_of_birth'],
        photo=photo_bytes
    )

    try:
        db.session.add(new_record)
        db.session.commit()
        return jsonify({'message': 'Record saved successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/delete_record_post', methods=['POST'])
def delete_record_post():
    aadhar_number = request.form.get('aadhar_number') or request.json.get('aadhar_number')
    if not aadhar_number:
        return jsonify({'error': 'Aadhar number is required'}), 400

    record = Aadhar_Record.query.filter_by(aadhar_number=aadhar_number).first()
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    try:
        db.session.delete(record)
        db.session.commit()
        return jsonify({'message': 'Record deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500





@app.route('/view_records')
def view_records():
    records = Aadhar_Record.query.all()

    html = f"""
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Times New Roman', Times, serif;
        }}

        body {{
            background: #F1F0E8;  /* Off-white background */
            color: #4A5B61;  /* Darker shade of the blue-gray for text */
        }}

        .container {{
            padding: 40px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}

        h1 {{
            color: #4A5B61;  /* Darker blue-gray for better contrast */
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .subtitle {{
            color: #5C7178;  /* Medium dark blue-gray for subtitle */
            font-size: 1.2rem;
            margin-bottom: 30px;
            font-weight: 500;
        }}

        .table-container {{
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(137, 168, 178, 0.1);
            overflow: hidden;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #89A8B2;  /* Soft blue-gray for header */
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 500;
            font-size: 0.95rem;
            border-bottom: 2px solid #B3C8CF;
        }}

        td {{
            padding: 15px;
            border-bottom: 1px solid #E5E1DA;  /* Light warm gray for borders */
            font-size: 0.95rem;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover {{
            background-color: #F1F0E8;  /* Off-white for hover */
        }}

        .photo-cell img {{
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(137, 168, 178, 0.1);
            transition: transform 0.2s;
            border: 1px solid #E5E1DA;
        }}

        .photo-cell img:hover {{
            transform: scale(1.1);
        }}

        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #89A8B2;
        }}

        .empty-state h2 {{
            color: #89A8B2;
            margin-bottom: 10px;
        }}

        .empty-state p {{
            font-size: 1.1rem;
            color: #B3C8CF;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px 10px;
            }}

            h1 {{
                font-size: 2rem;
            }}

            .table-container {{
                overflow-x: auto;
            }}

            th, td {{
                padding: 10px;
                font-size: 0.9rem;
            }}
        }}
    </style>
    <div class="container">
        <div class="header">
            <h1>Stored Records</h1>
            <p class="subtitle">View aadhar details of all employees</p>
        </div>

        <div class="table-container">
            <table>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Aadhar Number</th>
                    <th>Date of Birth</th>
                    <th>Photo</th>
                </tr>
    <form method="post" action="http://127.0.0.1:5000/delete_record_post">
    <input type="text" name="aadhar_number" placeholder="Enter Aadhar Number" required>
    <button type="submit">Delete Record</button>
</form>
    """

    if records:
        for record in records:
            photo_html = ""
            if record.photo:
                photo_base64 = base64.b64encode(record.photo).decode('utf-8')
                photo_html = f'<img src="data:image/png;base64,{photo_base64}" style="max-width: 100px;">'

            html += f"""
                <tr>
                    <td>{record.id}</td>
                    <td>{record.name or 'Not Available'}</td>
                    <td>{record.aadhar_number}</td>
                    <td>{record.date_of_birth}</td>
                    <td class="photo-cell">{photo_html}</td>
                </tr>
            """

        html += """
            </table>
        </div>
        """
    else:
        html += """
            <div class="empty-state">
                <h2>No Records Found</h2>
                <p>Start by uploading an Aadhar card to see records here.</p>
            </div>
        </div>
        """

    return html


@app.route('/view_verification_results')
def view_verification_results():
    # Query all verification results from the database
    results = VerificationResult.query.all()

    html = f"""
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Times New Roman', Times, serif;
        }}

        body {{
            background: #F1F0E8;
            color: #4A5B61;
        }}

        .container {{
            padding: 40px 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}

        h1 {{
            color: #4A5B61;
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .subtitle {{
            color: #5C7178;
            font-size: 1.2rem;
            margin-bottom: 30px;
            font-weight: 500;
        }}

        .table-container {{
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(137, 168, 178, 0.1);
            overflow: hidden;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #89A8B2;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 500;
            font-size: 0.95rem;
            border-bottom: 2px solid #B3C8CF;
        }}

        td {{
            padding: 15px;
            border-bottom: 1px solid #E5E1DA;
            font-size: 0.95rem;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover {{
            background-color: #F1F0E8;
        }}

        .status-passed {{
            color: #4CAF50;
            font-weight: bold;
        }}

        .status-failed {{
            color: #F44336;
            font-weight: bold;
        }}

        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #89A8B2;
        }}

        .empty-state h2 {{
            color: #89A8B2;
            margin-bottom: 10px;
        }}

        .empty-state p {{
            font-size: 1.1rem;
            color: #B3C8CF;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px 10px;
            }}

            h1 {{
                font-size: 2rem;
            }}

            .table-container {{
                overflow-x: auto;
            }}

            th, td {{
                padding: 10px;
                font-size: 0.9rem;
            }}
        }}
    </style>
    <div class="container">
        <div class="header">
            <h1>Face Verification Results</h1>
            <p class="subtitle">View all face verification attempts and their results</p>
        </div>

        <div class="table-container">
            <table>
                <tr>
                    <th>ID</th>
                    <th>Aadhar Number</th>
                    <th>Similarity Score</th>
                    <th>Verification Status</th>
                    <th>Verification Time</th>
                </tr>
    """

    if results:
        for result in results:
            # Format the verification status with appropriate styling
            status_class = "status-passed" if result.verification_passed else "status-failed"
            status_text = "PASSED" if result.verification_passed else "FAILED"

            # Format the similarity score to 2 decimal places
            similarity = f"{result.face_similarity:.2f}" if result.face_similarity is not None else "N/A"

            # Format the verification time
            verification_time = result.verification_time.strftime("%Y-%m-%d %H:%M:%S")

            html += f"""
                <tr>
                    <td>{result.id}</td>
                    <td>{result.aadhar_number}</td>
                    <td>{similarity}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{verification_time}</td>
                </tr>
            """

        html += """
            </table>
        </div>
        """
    else:
        html += """
            <div class="empty-state">
                <h2>No Verification Results Found</h2>
                <p>No face verification attempts have been recorded yet.</p>
            </div>
        </div>
        """

    return html


@app.route('/verification_results/<path:filename>')
def serve_verification_image(filename):
    return send_file(f"verification_results/{filename}")


if __name__ == '__main__':
    app.run(debug=True, port=5000)

