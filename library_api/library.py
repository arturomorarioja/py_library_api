import os
import re
import requests
from datetime import date, timedelta
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
    
# Add new book
@bp.route('/books', methods=['POST'])
def post_book():
    title = request.form.get('title')
    author_id = request.form.get('author_id')
    publisher_id = request.form.get('publisher_id')
    publishing_year = int(request.form.get('publishing_year'))

    if not (title and author_id and publisher_id and publishing_year):
        return error_message(), 400
    else:
        db = get_db()
        author = db.execute(
            '''
            SELECT COUNT(*) AS Total
            FROM tauthor
            WHERE nAuthorID = ?
            ''',
            (author_id,)
        ).fetchone()

        if author['Total'] == 0:
            return error_message('The author does not exist'), 404
        else:
            if publishing_year >= date.today().year:
                return error_message('Invalid year of publication'), 400
            else:
                publisher = db.execute(
                    '''
                    SELECT COUNT(*) AS Total
                    FROM tpublishingcompany
                    WHERE nPublishingCompanyID = ?
                    ''',
                    (publisher_id,)
                ).fetchone()

                if publisher['Total'] == 0:
                    return error_message('The publishing company does not exist'), 404
                else:
                    cursor = db.cursor()
                    cursor.execute(
                        '''
                        INSERT INTO tbook
                            (cTitle, nAuthorID, nPublishingYear, nPublishingCompanyID)
                        VALUES
                            (?, ?, ?, ?)
                        ''',
                        (title, author_id, publishing_year, publisher_id)
                    )
                    book_id = cursor.lastrowid
                    inserted_rows = cursor.rowcount
                    db.commit()
                    cursor.close()

                    if inserted_rows == 0:
                        return error_message('There was an error when trying to insert the book'), 500
                    else:
                        return jsonify({'book_id': book_id}), 201

# Return all authors

# Add new author

# Return all publishing companies

# Add new publishing company
    
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
        
# Delete a specific user
@bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        '''
        DELETE FROM tloan
        WHERE nMemberID = ?
        ''',
        (user_id,)
    )

    cursor.execute(
        '''
        DELETE FROM tmember
        WHERE nMemberID = ?
        ''',
        (user_id,)
    )
    deleted_rows = cursor.rowcount
    db.commit()
    cursor.close()
    if deleted_rows == 0:
        return error_message('The user could not be deleted'), 500
    else:
        return jsonify({'status': 'ok'}), 200

# Update a specific user
@bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id: int):
    fields = {
        'cEmail': request.form.get('email'),
        'cName': request.form.get('first_name'),
        'cSurname': request.form.get('last_name'),
        'cAddress': request.form.get('address'),
        'cPhoneNo': request.form.get('phone_number'),
        'dBirth': request.form.get('birth_date')
    }
    fields = { key: value for key, value in fields.items() if value is not None }

    if not fields:
        return error_message(), 400
    else:
        sql = 'UPDATE tmember SET ' + ', '.join([f'{key} = ?' for key in fields.keys()]) + ' WHERE nMemberID = ?'

        print(sql)
        print(list(fields.values()) + [user_id])

        db = get_db()
        cursor = db.cursor()
        cursor.execute(sql, list(fields.values()) + [user_id])
        updated_rows = cursor.rowcount
        db.commit()
        cursor.close()
        if updated_rows == 0:
            return error_message('The user could not be updated'), 500
        else:
            return jsonify({'status': 'ok'}), 200
        
# Loan a book
@bp.route('/users/<int:user_id>/books/<int:book_id>', methods=['POST'])
def loan_book(user_id: int, book_id: int):  
    
    # Check that the book is not already on loan by this user
    db = get_db()
    loan = db.execute(
        '''
        SELECT MAX(dLoan) AS last_loan_date
        FROM tloan
        WHERE nBookID = ?
        AND nMemberID = ?
        ''',
        (book_id, user_id)
    ).fetchone()

    today = date.today()
    if loan is not None:
        last_loan_date = loan['last_loan_date']
        if last_loan_date is not None:
            if loan['last_loan_date'] >= str(today - timedelta(days = 30)):
                return error_message('This user has still this book on loan'), 400
    
    # Loan the book
    cursor = db.cursor()
    cursor.execute(
        '''
        INSERT INTO tloan
            (nBookID, nMemberID, dLoan)
        VALUES
            (?, ?, ?)
        ''',
        (book_id, user_id, today)
    )
    inserted_rows = cursor.rowcount
    db.commit()
    cursor.close()
    if inserted_rows == 0:
        return error_message('It was not possible to loan the book'), 500
    else:
        return jsonify({'status': 'ok'})