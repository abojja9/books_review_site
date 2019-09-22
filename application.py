import os

from flask import Flask, session, request, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import render_template, redirect
from helpers import login_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import requests

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))



@app.route("/")
@login_required
def index():
    """ Show search box """

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """ Log user in """

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        print ("Login POST")
        user_dict = {
            "username" : request.form.get("username"),
            "password" : request.form.get("password")
        }
        # Step-1: See whether the username is valid
        if user_dict["username"] is None:
            return render_template("error.html",  message="please provide valid username")
        # Step-2: Check if the password is valid
        elif user_dict["password"] is None:
            return render_template("error.html",  message="please provide valid password")
        # Step-4: Confirm the password:
        else:
            res = db.execute("SELECT * from users WHERE username = :username",
                {"username" : user_dict["username"]}).fetchone()
            if res is None:
                return render_template("error.html",  message=" user doesn't exist, please create an account")
            elif not check_password_hash(res[2], user_dict["password"]):
                return render_template("error.html",  message=" password's did not match")

        # Create a session for the new user
        session["user_id"] = res[0]
        session["username"] = res[1]

        # Redirect user to the home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        print ("via GET")
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """ Log user in """
   
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        register_dict = {
            "username" : request.form.get("username"),
            "password" : request.form.get("password"),
            "confirmation": request.form.get("confirmation")
        }
        print ("register_dict:", register_dict)
        
        # Update the users table with the new username and password.
        # Step-1: See whether the username is valid
        if register_dict["username"] is None:
            return render_template("error.html",  message="please provide valid username")
        
        # Step-2: Check whether any duplicate username exists
        duplicateuserCheck = db.execute("SELECT * from users WHERE username = :username",
            {"username": register_dict["username"]}).fetchone()
        if duplicateuserCheck:
            return render_template("error.html",  message="username already exists, please use another")
        # Step-3: Check if the password is valid
        elif register_dict["password"] is None:
            return render_template("error.html",  message="please provide valid password")
        # Step-4: Confirm the password:
        elif not register_dict["confirmation"] and not register_dict["password"]==register_dict["confirmation"]:
            return render_template("error.html",  message=" password's did not match")
        
        # Insert new user to the "users" database
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                {
                    "username" : register_dict["username"],
                    "password" : generate_password_hash(register_dict["password"], method='pbkdf2:sha256', salt_length=8)
                }
        )

        # Commit info to the database
        db.commit()

        flash('Account created', 'info')

        # Redirect user to the login page
        return redirect("/login")
        
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        print ("Register: via GET")
        return render_template("register.html")

@app.route("/logout")
def logout():
    """ Log user out """

    # Forget any user ID
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/search", methods=["GET"])
def search():
    """ Search for a book """

    if not request.args.get("book"):
        return render_template("error.html", message="Please provide book details")
    
    # Take the input and add a wildcard
    query = ("%" + request.args.get("book") + "%").title()

    res = db.execute("SELECT isbn, title, author, year FROM books "
                    "WHERE isbn LIKE :query OR title LIKE :query OR "
                    "author LIKE :query OR year LIKE :query;",
                    {"query": query}
                    )

    if res is None:
        return render_template("error.html",  message=" book not found, search again with correct description")
    res_books = res.fetchall()
    print ("books:", res_books)

    return render_template("results.html", books=res_books)

@app.route("/book/<isbn>", methods=['GET','POST'])
@login_required
def book(isbn):
    """ Save user review and load same page with reviews updated."""

    if request.method == "POST":

        # Save current user info
        currentUser = session["user_id"]
        
        # Fetch form data
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        
        # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save id into variable
        bookId = row.fetchone() # (id,)
        bookId = bookId[0]

        # Check for user submission (ONLY 1 review/user allowed per book)
        row2 = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id",
                    {"user_id": currentUser,
                     "book_id": bookId})

        # A review already exists
        if row2.rowcount == 1:
            
            flash('You already submitted a review for this book', 'warning')
            return redirect("/book/" + isbn)

        # Convert to save into DB
        rating = int(rating)

        db.execute("INSERT INTO reviews (user_id, book_id, comment, rating) VALUES \
                    (:user_id, :book_id, :comment, :rating)",
                    {"user_id": currentUser, 
                    "book_id": bookId, 
                    "comment": comment, 
                    "rating": rating
                    })

        # Commit transactions to DB and close the connection
        db.commit()

        flash('Review submitted!', 'info')

        return redirect("/book/" + isbn)
    
    # Take the book ISBN and redirect to his page (GET)
    else:

        row = db.execute("SELECT isbn, title, author, year FROM books WHERE \
                        isbn = :isbn",
                        {"isbn": isbn})

        bookInfo = row.fetchall()

        """ GOODREADS reviews """

        # Read API key from env variable
        key = os.getenv("GOODREADS_KEY")
        
        # Query the api with key and ISBN as parameters
        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})

        # Convert the response to JSON
        response = query.json()

        # "Clean" the JSON before passing it to the bookInfo list
        response = response['books'][0]

        # Append it as the second element on the list. [1]
        bookInfo.append(response)

        """ Users reviews """

         # Search book_id by ISBN
        row = db.execute("SELECT id FROM books WHERE isbn = :isbn",
                        {"isbn": isbn})

        # Save id into variable
        book = row.fetchone() # (id,)
        book = book[0]

        # Fetch book reviews
        # Date formatting (https://www.postgresql.org/docs/9.1/functions-formatting.html)
        results = db.execute("SELECT users.username, comment, rating, \
                            time \
                            FROM users \
                            INNER JOIN reviews \
                            ON users.id = reviews.user_id \
                            WHERE book_id = :book \
                            ORDER BY time",
                            {"book": book})

        reviews = results.fetchall()

        return render_template("book.html", bookInfo=bookInfo, reviews=reviews)




@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):
    """ return json response with book details."""


    row = db.execute("SELECT title, author, year, isbn, \
                COUNT(reviews.id) as review_count, \
                AVG(reviews.rating) as average_score \
                FROM books \
                INNER JOIN reviews \
                ON books.id = reviews.book_id \
                WHERE isbn = :isbn \
                GROUP BY title, author, year, isbn",
                {"isbn": isbn})


    # Error checking
    if row.rowcount != 1:
        return jsonify({"Error": "Invalid book ISBN"}), 422

     # Fetch result from RowProxy    
    tmp = row.fetchone()

    # Convert to dict
    result = dict(tmp.items())

    # Round Avg Score to 2 decimal. This returns a string which does not meet the requirement.
    # https://floating-point-gui.de/languages/python/
    result['average_score'] = float('%.2f'%(result['average_score']))

    return jsonify(result)

    







    
