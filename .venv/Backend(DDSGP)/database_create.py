import os
import sqlite3
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Create a temporary Flask app just for database initialization
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aadhar_information.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Define all database models
class AadharRecord(db.Model):
    """Main table for storing Aadhar card information"""
    __tablename__ = 'aadhar_record'
    id = db.Column(db.Integer, primary_key=True)
    aadhar_number = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.String(10), nullable=False)
    photo = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FaceEmbedding(db.Model):
    """Table for storing face embeddings"""
    __tablename__ = 'face_embeddings'
    id = db.Column(db.Integer, primary_key=True)
    aadhar_number = db.Column(db.String(12), db.ForeignKey('aadhar_record.aadhar_number'), unique=True, nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VerificationResult(db.Model):
    """Table for storing face verification results"""
    __tablename__ = 'verification_results'
    id = db.Column(db.Integer, primary_key=True)
    aadhar_number = db.Column(db.String(12), db.ForeignKey('aadhar_record.aadhar_number'), nullable=False)
    face_similarity = db.Column(db.Float, nullable=True)
    verification_passed = db.Column(db.Boolean, default=False)
    verification_time = db.Column(db.DateTime, default=datetime.utcnow)
    id_image_path = db.Column(db.Text, nullable=True)
    webcam_image_path = db.Column(db.Text, nullable=True)


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


def create_tables():
    """Create all tables in the database"""
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
    print("Database tables created successfully.")


def create_tables_manually():
    """Alternative method to create tables using raw SQL"""
    db_path = 'instance/aadhar_infromation.db'
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create aadhar_record table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aadhar_record (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aadhar_number VARCHAR(12) UNIQUE NOT NULL,
        name VARCHAR(100),
        date_of_birth VARCHAR(10) NOT NULL,
        photo BLOB,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create face_embeddings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS face_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aadhar_number VARCHAR(12) UNIQUE NOT NULL,
        embedding BLOB,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (aadhar_number) REFERENCES aadhar_record(aadhar_number)
    )
    ''')

    # Create verification_results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aadhar_number VARCHAR(12) NOT NULL,
        face_similarity FLOAT,
        verification_passed BOOLEAN,
        verification_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        id_image_path TEXT,
        webcam_image_path TEXT,
        FOREIGN KEY (aadhar_number) REFERENCES aadhar_record(aadhar_number)
    )
    ''')

    # Create question_verification_results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS question_verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aadhar_number VARCHAR(12) NOT NULL,
        verified_count INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        overall_verified BOOLEAN DEFAULT 0,
        results_json TEXT NOT NULL,
        verification_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (aadhar_number) REFERENCES aadhar_record(aadhar_number)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database tables created manually successfully.")


if __name__ == '__main__':
    # Choose which method to use
    method = input("Choose database creation method (1 for SQLAlchemy, 2 for Raw SQL): ")

    if method == '1':
        create_tables()
    else:
        create_tables_manually()

