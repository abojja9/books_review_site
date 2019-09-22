import os
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


# db.execute(
#     'CREATE TABLE "books"('
#         'id SERIAL PRIMARY KEY,'
#         'isbn VARCHAR NOT NULL,'
#         'title VARCHAR NOT NULL,'
#         'author VARCHAR NOT NULL,'
#         'year VARCHAR NOT NULL);'
# )

# db.execute(
#     'CREATE TABLE "users"('
#         'id SERIAL PRIMARY KEY,'
#         'username VARCHAR NOT NULL,'
#         'password VARCHAR NOT NULL);'
# )

# db.execute(
#     'CREATE TABLE "reviews"('
#         'id SERIAL PRIMARY KEY,'
#         'user_id INTEGER REFERENCES users,'
#         'book_id INTEGER REFERENCES books,'
#         'rating SMALLINT NOT NULL CONSTRAINT Invalid_Rating CHECK (rating <=5 AND rating>=1),'
#         'comment VARCHAR NOT NULL,'
#         'time TIME (0));'
# )


f = open("books.csv")
reader = csv.reader(f)

for isbn, title, author, year in reader: # loop gives each column a name
    # print(isbn, title, author, year)
    db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": title, "author": author, "year": year}) # substitute values from CSV line into SQL command, as per this dict
    print(f"Added book with isbn: {isbn} titled {title} by {author} in {year}.")
db.commit() # transactions are assumed, so close the transaction finished
