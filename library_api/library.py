import os
import requests
import html.entities
from flask import Blueprint, request, jsonify
from library_api.database import get_db

def error_message(message='Incorrect parameters'):
    return jsonify({'error': message})

"""
Substitutes a string's non-ASCII characters by their equivalent character entities.
It also replaces spaces by plus signs, as requested by the book cover API.
Proposed and generated by ChatGPT
"""
def convert_to_html_entities(text: str):
    result = []
    for char in text:
        # Check if the character is ASCII
        if ord(char) < 128:
            result.append(char)
        else:
            # Attempt to find a named HTML entity for the character
            entity_name = html.entities.codepoint2name.get(ord(char))
            if entity_name:
                # Use the named entity (e.g., &euml; for ë)
                result.append(f"&{entity_name};")
            else:
                # Use a numeric entity if no named entity exists
                result.append(f"&#{ord(char)};")
    return ''.join(result).replace(' ', '+')

bp = Blueprint('library_api', __name__)

# Returns a dictionary with basic book info by ID
def basic_book_info(book_id: int):
    db = get_db()
    book = db.execute(
        '''
        SELECT tbook.cTitle, tauthor.cName, tauthor.cSurname,
            tpublishingcompany.cName, tbook.nPublishingYear
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
        return error_message('Book not found')
    else:        

        # The book title is obtained from the book cover API
        book_cover_base_url = os.getenv('BOOK_COVER_BASE_URL')
        book_title = convert_to_html_entities(book[0])
        author_name = convert_to_html_entities(f'{book[1]} {book[2]}')
        book_cover_url = f'{book_cover_base_url}?book_title={book_title}&author_name={author_name}'
        result = dict(requests.get(book_cover_url).json())
        if 'error' in result:
            cover = ''
        else:
            cover = result['url']

        return {
            'title': book[0],
            'author': f'{book[1]} {book[2]}',
            'publishing_company': book[3],
            'publishing_year': book[4],
            'cover': cover
        }

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
            SELECT nMemberID, dLoan
            FROM tloan
            WHERE nBookID = ?
            ORDER BY dLoan
            ''',
            (book_id,)
        ).fetchall()

        loan_list = []
        for loan in loans:
            loan_list.append({
                'user_id': loan[0],
                'loan_date': str(loan[1])
            })
        book_info['loans'] = loan_list

        return jsonify(book_info), 200