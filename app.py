from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager, create_access_token
from datetime import timedelta
import os
from dotenv import load_dotenv
from database import db, User, Rating, Movie

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'movies/'
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

# Registration endpoint for user sign-up (Admins and Users)
@app.route('/register', methods=['POST'])
def register_user():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    email = request.json.get("email", None)
    is_admin = request.json.get("isAdmin", False)

    if not username:
        return "Username is absent", 400
    if not password:
        return "Password is absent", 400
    if not email:
        return "Email is absent", 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password, email=email, isAdmin=is_admin)

    try:
        db.session.add(new_user)
        db.session.commit()
        return "The user has been registered", 201
    except Exception as e:
        db.session.rollback()
        return str(e), 500

# Login endpoint to authenticate users
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

# Admin-only endpoint to add a new movie
@app.route('/add-movies', methods=['POST'])
@jwt_required()
def add_movies():
    current_user_id = get_jwt_identity()
    current_user = User.query.filter_by(user_id=current_user_id).first()

    if current_user is None or not current_user.isAdmin:
        return jsonify({"msg": "Access denied"}), 403

    title = request.json.get("title")
    release_year = request.json.get("release_year")

    if not title or not release_year:
        return jsonify({"msg": "Title and release year are required."}), 400

    new_movie = Movie(title=title, release_year=release_year)

    try:
        db.session.add(new_movie)
        db.session.commit()
        return jsonify({"msg": f"Movie '{title}' added successfully!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500

# Endpoint for users to submit ratings for movies (only if movie exists)
# [To-Do]

# Endpoint to retrieve a list of existing user ratings for all movies
# [To-Do]

# Endpoint to fetch details for a specific movie, including its user ratings
@app.route('/movies/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    try:
        movie = Movie.query.filter_by(movie_id=movie_id).first()

        if movie is None:
            return jsonify({"msg": "Movie not found."}), 404

        ratings = Rating.query.filter_by(movie_id=movie_id).all()
        ratings_list = [{"user_id": rating.user_id, "rating": rating.rating} for rating in ratings]

        return jsonify({
            "movie_id": movie.movie_id,
            "title": movie.title,
            "release_year": movie.release_year,
            "ratings": ratings_list
        }), 200
    except Exception as e:
        return jsonify({"msg": "An error occurred while fetching the movie details."}), 500

# Endpoint to update user's own movie ratings
@app.route('/ratings/<int:rating_id>', methods=['PUT'])
@jwt_required()
def update_rating(rating_id):
    current_user_id = get_jwt_identity()
    new_rating = request.json.get('rating', None)

    if new_rating is None or not (1 <= new_rating <= 10):
        return jsonify({"msg": "A valid rating between 1 and 10 is required."}), 400

    rating = Rating.query.filter_by(rating_id=rating_id, user_id=current_user_id).first()

    if rating is None:
        return jsonify({"msg": "Rating not found or you are NOT allowed to update this rating."}), 404

    rating.rating = new_rating
    try:
        db.session.commit()
        return jsonify({"msg": "Updated rating successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "An error occurred while updating the rating."}), 500

# Admin-only endpoint to delete any user's movie rating
# [To-Do]

# Endpoint for users to delete their own ratings
@app.route('/ratings/<int:rating_id>', methods=['DELETE'])
@jwt_required()
def delete_rating(rating_id):
    current_user_id = get_jwt_identity()
    rating = Rating.query.filter_by(rating_id=rating_id, user_id=current_user_id).first()

    if rating is None:
        return jsonify({"msg": "Could NOT find rating, or you ARE NOT allowed to delete it."}), 404

    try:
        db.session.delete(rating)
        db.session.commit()
        return jsonify({"msg": "Deleted rating successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": "An error occurred while deleting the rating."}), 500

if __name__ == '__main__':
    app.run(debug=True)
