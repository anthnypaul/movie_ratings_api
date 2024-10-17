from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
import datetime
import os
from dotenv import load_dotenv
from database import db, User, Rating
from flask_jwt_extended import jwt_required, get_jwt_identity # Importing necessary modules for JWT -Baraa

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SECRET_KEY'] = "temporary_key_for_testing"
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
        token = jwt.encode(
            {
                'user_id': user.user_id,  
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            },
            app.config['SECRET_KEY'],
            algorithm="HS256"
        )
        return jsonify({"token": token}), 200

    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/')
def home():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)

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
@jwt_required()
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