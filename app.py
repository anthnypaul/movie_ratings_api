from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
import datetime
import os
from dotenv import load_dotenv
from database import db, User, Rating, Movie
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager, create_access_token # Importing necessary modules for JWT -Baraa
from werkzeug.utils import secure_filename
from datetime import timedelta

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'movies/'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SECRET_KEY'] = "temporary_key_for_testing"
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_TYPE'] = 'Bearer'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

jwt_manager = JWTManager(app)

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/check_db')
def check_db_connection():
    try:
        # Establish a connection and execute a simple query using the connection
        with db.engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return "MySQL connection is working."
    except OperationalError:
        return "Failed to connect to MySQL."

@app.route('/register', methods=['POST'])
def register_user():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    email = request.json.get("email", None)

    if username == None:
        return "Username is absent", 400
    if password == None:
        return "Password is absent", 400
    if email == None:
        return "Email is absent", 400

    hashed_password = generate_password_hash(password)
    newUser = User(username=username, password=hashed_password, email=email)

    try:    
        db.session.add(newUser)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return str(e), 500

    return "The user has been registered", 201

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get("username")
    password = request.json.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        token = create_access_token(identity=user.user_id, expires_delta=timedelta(hours=1))
        return jsonify({"token": token}), 200

    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/')
def home():
    return "Hello, Flask!"


# An endpoint for users to delete their own ratings.
@app.route('/ratings/<int:rating_id>', methods=['DELETE'])
@jwt_required()
def delete_rating(rating_id):
    try:
        # Get current user ID from JWT token
        current_user_id = get_jwt_identity()

        # Get rating from database
        rating = Rating.query.filter_by(rating_id=rating_id, user_id=current_user_id).first()

        # Check if rating exists & belongs to current user
        if rating is None:
            return jsonify({"msg": "Could NOT find rating, or you ARE NOT allowed to delete rating."}), 404

        # Delete rating
        db.session.delete(rating)
        db.session.commit()

        return jsonify({"msg": "Deleted rating successfully."}), 200

    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        return jsonify({"msg": "An error occurred while deleting rating."}), 500

# An endpoint that allows users to update their own movie ratings.
@app.route('/ratings/<int:rating_id>', methods=['PUT'])
@jwt_required() # Ensures only authenticated users can update ratings.
def update_rating(rating_id):
    try:
        # Get current user ID from JWT token
        current_user_id = get_jwt_identity()

        # Get new rating value from request body
        new_rating = request.json.get('rating', None)

        if new_rating is None or not (1 <= new_rating <= 10):
            return jsonify({"msg": "A valid rating between 1 and 10 is required."}), 400

        # Fetch the rating from the database
        rating = Rating.query.filter_by(rating_id=rating_id, user_id=current_user_id).first()

        # Check if rating exists & belongs to current user
        if rating is None:
            return jsonify({"msg": "Rating not found or you are NOT allowed to update this rating."}), 404

        # Update rating value
        rating.rating = new_rating
        db.session.commit()

        return jsonify({"msg": "Updated rating successfully."}), 200

    except Exception as e:
        # Rollback in case of an error
        db.session.rollback()
        return jsonify({"msg": "An error occurred while updating rating."}), 500

# An endpoint to fetch details for a specific movie, including its user ratings.
@app.route('/movies/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    try:
        # Fetch movie from database
        movie = Movie.query.filter_by(movie_id=movie_id).first()

        # Check if movie exists
        if movie is None:
            return jsonify({"msg": "Movie not found."}), 404

        # Fetch all ratings for the movie
        ratings = Rating.query.filter_by(movie_id=movie_id).all()

        # Create list of ratings to include in response
        ratings_list = []
        for rating in ratings:
            ratings_list.append({
                "user_id": rating.user_id,
                "rating": rating.rating
            })

        # Return movie details & ratings
        return jsonify({
            "movie_id": movie.movie_id,
            "title": movie.title,
            "release_year": movie.release_year,
            "ratings": ratings_list
        }), 200

    except Exception as e:
        return jsonify({"msg": "An error occurred while fetching the movie details."}), 500

@app.route('/add-movies', methods=['POST'])
@jwt_required()
def add_movies():
    current_user_id = get_jwt_identity()

    current_user = User.query.filter_by(user_id=current_user_id).first()

    # Check if user is Admin
    if current_user == None or not current_user.isAdmin:
        return jsonify({"msg": "Access denied"}), 403
    
    # If no file is selected
    if 'file' not in request.files:
        print("Files in request:", request.files)
        return jsonify({"msg": "No file part in the request"}), 400
    
    file = request.files['file']
    release_year = request.json.get("release_year", None)

    # Save the file to designated folder
    if file.filename == '':
        return jsonify({"msg": "No file selected for uploading"}), 400


    if file:

        file_name = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        return jsonify({"msg": f"File '{file.filename} uploaded successfully!"}), 200
    
    return jsonify({"msg": "File upload failed"}), 500

@app.route('/upload', methods=['POST'])
def upload():
    # Check if the request contains a file part
    if 'file' not in request.files:
        print("Files in request:", request.files)
        return jsonify({"msg": "No file part in the request"}), 400
    
    file = request.files['file']

    # If no file is selected
    if file.filename == '':
        return jsonify({"msg": "No file selected for uploading"}), 400

    sanitized_filename = secure_filename(file.filename)

    # Save the file to designated folder
    if file and allowed_file(sanitized_filename):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], sanitized_filename)
        file.save(filepath)

        return jsonify({"msg": f"File '{sanitized_filename}' uploaded successfully!"}), 200

    return jsonify({"msg": f"Invalid file type for '{sanitized_filename}'. Allowed file types are {ALLOWED_EXTENSIONS}"}), 415 

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True)