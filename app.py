from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    isAdmin = db.Column(db.Boolean, nullable=False, default=False)
    ratings = db.relationship('Rating', back_populates='user')

    def __repr__(self):
        return f"<User {self.username}"

class Movie(db.Model):
    __tablename__ = 'movies'
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    release_year = db.Column(db.Integer)
    ratings = db.relationship('Rating', back_populates='movie')

    def __repr__(self):
        return f"<Movie {self.title}"

class Rating(db.Model):
    __tablename__ = 'ratings'
    rating_id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.movie_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    rating = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', back_populates='ratings')
    movie = db.relationship('Movie', back_populates='ratings')

    def __repr__(self):
        return f"<Rating {self.rating_id}"
    

@app.route('/check_db')
def check_db_connection():
    try:
        # Establish a connection and execute a simple query using the connection
        with db.engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return "MySQL connection is working."
    except OperationalError:
        return "Failed to connect to MySQL."

@app.route('/')
def home():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)
