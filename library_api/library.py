import os
import re
import requests
from datetime import date
from flask import Blueprint, request, jsonify
from library_api.database import get_db
from library_api.common import error_message, convert_to_html_entities

bp = Blueprint('library_api', __name__)

# Returns a dictionary with basic book info by ID
def basic_book_info(book_id: int):
    db = get_db()
    book = db.execute(
        '''
        SELECT tbook.cTitle AS title, trim(tauthor.cName || ' ' || tauthor.cSurname) AS author,
            tpublishingcompany.cName AS publishing_company, tbook.nPublishingYear AS publishing_year
        FROM tbook
            INNER JOIN tauthor
                ON tbook.nAuthorID = tauthor.nAuthorID
            INNER JOIN tpublishingcompany
                ON tbook.nPublishingCompanyID = tpublishingcompany.nPublishingCompanyID
        WHERE tbook.nBookID = ?
        ''',
        (book_id,)
    ).fetchone()
    
    if book == None:
        return error_message('Book not found'), 404
    else:        

        # The book title is obtained from the book cover API
        book_cover_base_url = os.getenv('BOOK_COVER_BASE_URL')
        book_title = convert_to_html_entities(book['title'])
        author_name = convert_to_html_entities(book['author'])
        book_cover_url = f'{book_cover_base_url}?book_title={book_title}&author_name={author_name}'
        result = dict(requests.get(book_cover_url).json())
        if 'error' in result:
            cover = ''
        else:
            cover = result['url']

        # The sqlite row is converted to a dictionary
        book_info = {key: book[key] for key in book.keys()}
        book_info['cover'] = cover
        return book_info

# Return basic book info by ID 
@bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id: int):
    book_info = basic_book_info(book_id)
    if 'error' in book_info:
        return book_info, 404
    else:
        return jsonify(book_info), 200

# Return detailed book info by ID 
@bp.route('/admin/books/<int:book_id>', methods=['GET'])
def get_detailed_book(book_id: int):
    db = get_db()
    book_info = basic_book_info(book_id)
    if 'error' in book_info:
        return book_info, 404
    else:
        loans = db.execute(
            '''
            SELECT nMemberID AS user_id, dLoan AS loan_date
            FROM tloan
            WHERE nBookID = ?
            ORDER BY dLoan
            ''',
            (book_id,)
        ).fetchall()

        # The loan date is converted to a string, but the user ID is not
        loan_list = [{key: str(loan[key]) if key == 'loan_date' else loan[key] \
            for key in loan.keys()} for loan in loans]
        book_info['loans'] = loan_list
        return jsonify(book_info), 200
    
# Return information for a random number of books
@bp.route('/books', methods=['GET'])
def get_random_books():
    number = request.args.get('n')
    if number == None:
        return error_message()
    else:
        db = get_db()
        books = db.execute(
            '''
            SELECT tbook.nBookID AS book_id, tbook.cTitle AS title, tbook.nPublishingYear AS publishing_year,
                trim(tauthor.cName || ' ' || tauthor.cSurname) AS author, tpublishingcompany.cName AS publishing_company
            FROM tbook INNER JOIN tauthor
                    ON tbook.nAuthorID = tauthor.nAuthorID
                INNER JOIN tpublishingcompany
                    ON tbook.nPublishingCompanyID = tpublishingcompany.nPublishingCompanyID
            ORDER BY RANDOM()
            LIMIT ?
            ''',
            (number,)
        ).fetchall()

        book_list = [{key: book[key] for key in book.keys()} for book in books]
        return jsonify(book_list), 200
    
# Return information for a specific user
@bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id: int):
    db = get_db()
    user = db.execute(
        '''
        SELECT cEmail AS email, cName AS first_name, cSurname AS last_name, 
            cAddress AS address, cPhoneNo AS phone_number, 
            dBirth AS birth_date, dNewMember AS membership_date
        FROM tmember
        WHERE nMemberID = ?
        ''',
        (user_id,)
    ).fetchone()

    if user == None:
        return error_message('User not found'), 404
    else:        
        user_info = {key: user[key] for key in user.keys()}
        user_info['birth_date'] = str(user_info['birth_date'])
        user_info['membership_date'] = str(user_info['membership_date'])
        return jsonify(user_info), 200

# Add new user
@bp.route('/users', methods=['POST'])
def post_user():
    email = request.form.get('email')
    password = request.form.get('password')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    address = request.form.get('address')
    phone_number = request.form.get('phone_number')
    birth_date = request.form.get('birth_date')

    # All values are mandatory
    if not (email and password and first_name and last_name and address and phone_number and birth_date):
        return error_message(), 400
    else:
        # The password must be at least 8 characters long and include at least 
        # one uppercase and lowercase letter, one number and one special character.
        # RegEx pattern from https://uibakery.io/regex-library/password-regex-python
        if re.match('^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{8,}$', password) == None:
            return error_message('Incorrect password format'), 400
        else:
            # The email address must not exist in the database
            db = get_db()
            user = db.execute(
                '''
                SELECT COUNT(*) AS total
                FROM tmember
                WHERE cEmail = ?
                ''',
                (email,)
            ).fetchone()
            if user['total'] > 0:
                return error_message('The user already exists'), 400
            else:
                cursor = db.cursor()
                cursor.execute(
                    '''
                    INSERT INTO tmember
                        (cEmail, cPassword, cName, cSurname, cAddress, cPhoneNo, dBirth, dNewMember)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (email, password, first_name, last_name, address, phone_number, birth_date, str(date.today()))
                )
                user_id = cursor.lastrowid
                cursor.close()
                db.commit()

                return jsonify({'user_id': user_id}), 201

# Validate login information
@bp.route('/users/login', methods=['POST'])
def validate_user():
    email = request.form.get('email')
    password = request.form.get('password')

    if not (email and password):
        return error_message(), 400
    else:
        db = get_db()
        user = db.execute(
            '''
            SELECT nMemberID AS user_id
            FROM tmember
            WHERE cEmail = ?
            AND cPassword = ?
            ''',
            (email, password)
        ).fetchone()
        if user == None:
            return error_message('Wrong credentials'), 401
        else:
            return jsonify({'user_id': user['user_id']})