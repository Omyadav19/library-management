import sqlite3
from library.db import books_collection, issues_collection, config_collection
import uuid

def migrate():
    # Connect to SQLite
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Migrate Books
    print("Migrating books...")
    books_collection.delete_many({}) # Clear existing
    cursor.execute("SELECT * FROM library_book")
    books = cursor.fetchall()
    
    # Store ID mapping since SQLite IDs are integers and Mongo uses UUID strings
    # We will just map the integer ID string to the UUID, or keep the integer ID for issues?
    # Actually, our views expect _id to be strings, and we generate them using uuid.
    # We can just use the stringified integer ID as the _id so foreign keys still work!
    for b in books:
        book_id_str = str(b['id'])
        books_collection.insert_one({
            '_id': book_id_str,
            'title': b['title'],
            'author': b['author'],
            'genre': b['genre'],
            'isbn': b['isbn'],
            'total_copies': b['total_copies'],
            'available_copies': b['available_copies'],
            'issue_count': b['issue_count'],
            'added_on': b['added_on']
        })
        print(f" Migrated book: {b['title']}")
        
    # Migrate Issues
    print("\nMigrating issues...")
    issues_collection.delete_many({})
    cursor.execute("SELECT * FROM library_issuerecord")
    issues = cursor.fetchall()
    
    for issue in issues:
        issues_collection.insert_one({
            '_id': issue['issue_id'],
            'issue_id': issue['issue_id'],
            'book_id': str(issue['book_id']), # Map to the stringified integer ID
            'member_name': issue['member_name'],
            'member_id': issue['member_id'],
            'issue_date': issue['issue_date'],
            'due_date': issue['due_date'],
            'return_date': issue['return_date'],
            'status': issue['status'],
            'fine': issue['fine'],
            'renewed': issue['renewed'],
            'renewal_date': issue['renewal_date']
        })
        print(f" Migrated issue for member: {issue['member_name']}")
        
    # Migrate Config
    print("\nMigrating config...")
    config_collection.delete_many({})
    cursor.execute("SELECT * FROM library_libraryconfig")
    configs = cursor.fetchall()
    if configs:
        c = configs[0]
        config_collection.insert_one({
            '_id': 'system_config',
            'fine_per_day': c['fine_per_day']
        })
        print(f" Migrated config: fine_per_day={c['fine_per_day']}")
        
    print("\nMigration complete!")

if __name__ == '__main__':
    migrate()
