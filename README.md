# Library API
Python Flask API that serves e-book information in the context of a digital online library.

## Endpoints
POST parameters are sent as form-data.

<b>User endpoints</b>:
|Method|Endpoint|POST params|Description|
|------|--------|-----------|-----------|
|GET|/books?n=<number_of_books>||Retrieve a random number of books|
|GET|/books/<book_id>||Retrieve information about a book|
|GET|/authors||Retrieve all authors|
|GET|/publishers||Retrieve all publishers|
|GET|/users/<user_id>||Retrieve information about a user|
|POST|/users|email, password, first_name, last_name, address, phone_number, birth_date|Create a new user. All parameters are mandatory. Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number and one special character|
|PUT|/users/<user_id>|email (optional), first_name (optional), last_name (optional), address (optional), phone_number (optional), birth_date (optional)|Update information about a user. At least one parameter must have a value|
|DELETE|/users/<user_id>||Delete a user and their loans|
|POST|/users/login|email, password|Validate user login information|
|POST|/users/<user_id>/books/<book_id>||Loan a book if it has not been loaned by the same user in the previous 30 days|

<b>Admin endpoints</b>:
|Method|Endpoint|POST params|Description|
|------|--------|-----------|-----------|
|GET|/admin/books/<book_id>||Retrieve information about a book and its loan history|
|POST|/admin/books|title, author_id, publisher_id, publishing_year|Create a new book. All parameters are mandatory. Year must be higher than the present year|

<b>Return values</b>:

- GET /books?n=15
```json
[
    {
        "book_id": 1005,
        "title": "Harry Potter and the Goblet of Fire",
        "publishing_year": 1943,
        "author": "J. K. Rowling",
        "publishing_company": "Labadie-Zboncak"
    },
    {
        "book_id": 1506,
        "title": "The Complete Tales and Poems of Edgar Allan Poe",
        "publishing_year": 1982,
        "author": "Edgar Allan Poe",
        "publishing_company": "Fisher LLC"
    },
    ...
]
```
- GET /books/1251
```json
{
    "title": "Do Androids Dream of Electric Sheep?",
    "author": "Philip K. Dick",
    "publishing_company": "Frami, Feeney and Hermiston",
    "publishing_year": 2010,
    "cover": "https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1507838927i/36402034.jpg"
}
```
- GET /authors
```json
[
    {
        "author_id": 1,
        "author_name": "Aeschylus"
    },
    {
        "author_id": 3,
        "author_name": "Aristotle"
    },
    ...
]
```
- GET /publishers
```json
[
    {
        "publisher_id": 98,
        "publisher_name": "Adams Group"
    },
    {
        "publisher_id": 135,
        "publisher_name": "Armstrong Inc"
    },
    ...
]
```
- GET /users/13
```json
{
    "email": "laura.m.lind@mail.com",
    "first_name": "Laura M.",
    "last_name": "Lind",
    "address": "Ulriksholmvej 80, 2990 Nivå",
    "phone_number": "004550724315",
    "birth_date": "1979-02-01",
    "membership_date": "2013-09-05"
}
```
- POST /users
```json
{
    "user_id": 2683
}
```
```json
{
    "error": "Incorrect parameters"
}
```
```json
{
    "error": "The user already exists"
}
```
```json
{
    "error": "Incorrect password format"
}
```
- PUT /users/2683
```json
{
    "status": "ok"
}
```
```json
{
    "error": "Incorrect parameters"
}
```
- DELETE /users/2683
```json
{
    "status": "ok"
}
```
- POST /users/login
```json
{
    "user_id": 2683
}
```
```json
{
    "error": "Wrong credentials"
}
```
- POST /users/13/books/1251
```json
{
    "status": "ok"
}
```
```json
{
    "error": "This user has still this book on loan"
}
```
- GET /admin/books/1251
```json
{
    "title": "Do Androids Dream of Electric Sheep?",
    "author": "Philip K. Dick",
    "publishing_company": "Frami, Feeney and Hermiston",
    "publishing_year": 2010,
    "cover": "https://images-na.ssl-images-amazon.com/images/S/compressed.photo.goodreads.com/books/1507838927i/36402034.jpg",
    "loans": [
        {
            "user_id": 966,
            "loan_date": "2013-12-19"
        },
        {
            "user_id": 1586,
            "loan_date": "2015-04-19"
        },
        ...
    ]
}
```
- POST /admin/books
```json
{
    "book_id": 1999
}
```
```json
{
    "error": "Incorrect parameters"
}
```
```json
{
    "error": "The author does not exist"
}
```
```json
{
    "error": "The publishing company does not exist"
}
```

## Installation
Rename `librarylite_original.db` as `librarylite.db`.

## Tools
SQLite3 / Flask / Python

## Author
Arturo Mora-Rioja