from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
import json

from .db import books_collection, issues_collection, config_collection, get_config, set_fine_rate, generate_uuid

def get_fine_rate():
    return get_config().get('fine_per_day', 5)

ALL_GENRES = [
    'Fiction', 'Non-Fiction', 'Science', 'Technology', 'Biography',
    'History', 'Philosophy', 'Self-Help', 'Psychology', 'Economics',
    'Literature', 'Poetry', 'Drama', 'Horror', 'Mystery', 'Romance',
    'Fantasy', 'Science Fiction', 'Children', 'Reference', 'Other'
]

def format_book(b):
    if not b: return None
    b['id'] = b['_id']
    return b

def format_issue(i):
    if not i: return None
    i['id'] = i['_id']
    return i

def get_activity_data(days=30):
    today = timezone.now().date()
    start = today - timedelta(days=days)
    labels = []
    issued_data = []
    returned_data = []
    
    for i in range(days + 1):
        d = start + timedelta(days=i)
        d_str = d.strftime('%Y-%m-%d')
        labels.append(d_str)
        issued_data.append(issues_collection.count_documents({'issue_date': d_str}))
        returned_data.append(issues_collection.count_documents({'return_date': d_str}))
        
    return {'labels': labels, 'issued': issued_data, 'returned': returned_data}

def dashboard(request):
    today_date = timezone.now().date()
    today_str = today_date.strftime('%Y-%m-%d')
    
    pipeline = [
        {'$group': {
            '_id': None, 
            'total_books': {'$sum': '$total_copies'},
            'available': {'$sum': '$available_copies'}
        }}
    ]
    book_stats = list(books_collection.aggregate(pipeline))
    if book_stats:
        total_books = book_stats[0]['total_books']
        available = book_stats[0]['available']
    else:
        total_books = 0
        available = 0
        
    issued_count = issues_collection.count_documents({'status': 'issued'})
    
    overdue_qs = list(issues_collection.find({'status': 'issued', 'due_date': {'$lt': today_str}}).sort('due_date', 1))
    overdue_count = len(overdue_qs)
    
    overdue_list = []
    for r in overdue_qs:
        r = format_issue(r)
        book = format_book(books_collection.find_one({'_id': r['book_id']}))
        if book:
            r['book_title'] = book.get('title')
            r['book_author'] = book.get('author')
        
        due_date = datetime.strptime(r['due_date'], '%Y-%m-%d').date()
        days_overdue = (today_date - due_date).days
        r['days_overdue'] = days_overdue
        r['estimated_fine'] = days_overdue * get_fine_rate()
        overdue_list.append(r)
        
    fines_pipeline = [
        {'$match': {'status': 'returned'}},
        {'$group': {'_id': None, 'fines_collected': {'$sum': '$fine'}}}
    ]
    fines_res = list(issues_collection.aggregate(fines_pipeline))
    fines_collected = fines_res[0]['fines_collected'] if fines_res else 0
    
    genre_pipeline = [
        {'$group': {'_id': '$genre', 'count': {'$sum': 1}}}
    ]
    genre_res = list(books_collection.aggregate(genre_pipeline))
    genre_counts = {g['_id']: g['count'] for g in genre_res if g['_id']}
    
    popular_books = [format_book(b) for b in books_collection.find().sort('issue_count', -1).limit(5)]
    recent_books  = [format_book(b) for b in books_collection.find().sort('added_on', -1).limit(5)]
    activity_7    = get_activity_data(7)

    total_members = len(issues_collection.distinct('member_id'))
    total_issues_ever = issues_collection.count_documents({})
    recent_transactions = [format_issue(i) for i in issues_collection.find().sort([('issue_date', -1), ('_id', -1)]).limit(6)]
    
    for r in recent_transactions:
        book = format_book(books_collection.find_one({'_id': r['book_id']}))
        if book:
            r['book_title'] = book.get('title')

    availability_pct = round((available / total_books) * 100) if total_books > 0 else 0
    issued_pct = round((issued_count / total_books) * 100) if total_books > 0 else 0
    overdue_pct = round((overdue_count / issued_count) * 100) if issued_count > 0 else 0
    
    stats = {
        'total_books': total_books,
        'available': available,
        'issued_count': issued_count,
        'overdue_count': overdue_count,
        'availability_pct': availability_pct,
        'issued_pct': issued_pct,
        'overdue_pct': overdue_pct,
        'fines_collected': fines_collected,
        'genre_counts': genre_counts,
        'genre_counts_json': json.dumps(genre_counts),
        'popular_books': popular_books,
        'recent_books': recent_books,
        'overdue_list': overdue_list,
        'overdue_len': len(overdue_list),
        'activity_7': activity_7,
        'total_members': total_members,
        'total_issues_ever': total_issues_ever,
        'recent_transactions': recent_transactions,
    }

    now = timezone.now()
    hour = now.hour
    if hour < 12: greeting = 'Good morning'
    elif hour < 17: greeting = 'Good afternoon'
    else: greeting = 'Good evening'

    date_str = now.strftime('%A, %B %d, %Y')

    return render(request, 'dashboard.html', {
        'stats': stats,
        'greeting': greeting,
        'date_str': date_str
    })

def books_view(request):
    search_q = request.GET.get('search', '')
    genre_filter = request.GET.get('genre', 'All')
    availability = request.GET.get('availability', '')
    sort_by = request.GET.get('sort', 'title')
    
    query = {}
    
    if search_q:
        query['$or'] = [
            {'title': {'$regex': search_q, '$options': 'i'}},
            {'author': {'$regex': search_q, '$options': 'i'}},
            {'genre': {'$regex': search_q, '$options': 'i'}},
            {'isbn': {'$regex': search_q, '$options': 'i'}}
        ]
        
    if genre_filter and genre_filter != 'All':
        query['genre'] = {'$regex': f'^{genre_filter}$', '$options': 'i'}
        
    if availability == 'available':
        query['available_copies'] = {'$gt': 0}
    elif availability == 'unavailable':
        query['available_copies'] = 0
        
    sort_map = {
        'title': ('title', 1),
        'author': ('author', 1),
        'genre': ('genre', 1),
        'available': ('available_copies', 1),
        'popular': ('issue_count', -1),
    }
    sort_field, sort_dir = sort_map.get(sort_by, ('title', 1))
    
    books = [format_book(b) for b in books_collection.find(query).sort(sort_field, sort_dir)]
    
    genres = issues_collection.distinct('genre') # fallback
    genres = books_collection.distinct('genre')
    genres.sort()
    
    return render(request, 'books.html', {
        'books': books,
        'genres': genres,
        'search': search_q,
        'genre_filter': genre_filter,
        'availability': availability,
        'sort_by': sort_by
    })

def add_book(request):
    if request.method == 'POST':
        title = request.POST.get('title', '')
        author = request.POST.get('author', '')
        genre = request.POST.get('genre', '')
        isbn = request.POST.get('isbn', '')
        total_copies = request.POST.get('total_copies', '')
        
        isbn_clean = isbn.replace('-', '').replace(' ', '')
        if not isbn_clean.isdigit() or len(isbn_clean) != 13:
            messages.error(request, 'ISBN must contain exactly 13 digits.')
            return render(request, 'add_book.html', {'genres': ALL_GENRES})
            
        if books_collection.find_one({'isbn': isbn_clean}):
            messages.error(request, 'A book with this ISBN already exists.')
            return render(request, 'add_book.html', {'genres': ALL_GENRES})
            
        try:
            total_copies = int(total_copies)
            if total_copies < 1:
                messages.error(request, 'Total copies must be at least 1.')
                return render(request, 'add_book.html', {'genres': ALL_GENRES})
        except ValueError:
            messages.error(request, 'Total copies must be a valid integer.')
            return render(request, 'add_book.html', {'genres': ALL_GENRES})
            
        books_collection.insert_one({
            '_id': generate_uuid(),
            'title': title.strip(),
            'author': author.strip(),
            'genre': genre.strip(),
            'isbn': isbn_clean,
            'total_copies': total_copies,
            'available_copies': total_copies,
            'issue_count': 0,
            'added_on': timezone.now().strftime('%Y-%m-%d')
        })
        messages.success(request, 'Book added successfully.')
        return redirect('books')
        
    return render(request, 'add_book.html', {'genres': ALL_GENRES})

def search(request):
    query = request.GET.get('q', '')
    genre_filter = request.GET.get('genre', 'All')
    
    q_dict = {}
    if query:
        q_dict['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'author': {'$regex': query, '$options': 'i'}},
            {'genre': {'$regex': query, '$options': 'i'}},
            {'isbn': {'$regex': query, '$options': 'i'}}
        ]
                  
    if genre_filter != 'All':
        q_dict['genre'] = {'$regex': f'^{genre_filter}$', '$options': 'i'}
        
    results = [format_book(b) for b in books_collection.find(q_dict)]
        
    db_genres = books_collection.distinct('genre')
    all_genres_list = ['Fiction', 'Non-Fiction', 'Science', 'Technology', 'Biography', 'Self-Help']
    
    genres = sorted(list(set(db_genres + all_genres_list)))
    
    return render(request, 'search.html', {
        'results': results,
        'query': query,
        'genre_filter': genre_filter,
        'all_genres_list': genres
    })

def issue_book(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        member_name = request.POST.get('member_name')
        member_id = request.POST.get('member_id')
        due_date_str = request.POST.get('due_date')
        
        print(f"DEBUG issue_book POST: book_id={book_id}, member={member_id}")
        book = format_book(books_collection.find_one({'_id': book_id}))
        if not book:
            print(f"DEBUG: Book not found for id {book_id}")
            messages.error(request, 'Book not found.')
            return redirect('issue_book')
            
        if book.get('available_copies', 0) < 1:
            print("DEBUG: No available copies")
            messages.error(request, 'No copies available for this book.')
            return redirect('issue_book')
            
        if not member_name.strip() or not member_id.strip():
            print("DEBUG: Missing member name or ID")
            messages.error(request, 'Member name and ID are required.')
            return redirect('issue_book')
            
        member_name_clean = member_name.strip()
        member_id_clean = member_id.strip().upper()
        
        existing_member = issues_collection.find_one({'member_id': member_id_clean})
        if existing_member and existing_member.get('member_name', '').lower() != member_name_clean.lower():
            print("DEBUG: Member name mismatch")
            messages.error(request, f"This Member ID is already registered to '{existing_member.get('member_name')}'.")
            return redirect('issue_book')
            
        due_date = None
        if due_date_str:
            try:
                due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                if due_date_obj <= timezone.now().date():
                    print("DEBUG: Due date in past")
                    messages.error(request, 'Due date must be in the future.')
                    return redirect('issue_book')
                due_date = due_date_str
            except ValueError:
                print("DEBUG: ValueError in date")
                messages.error(request, 'Invalid due date format.')
                return redirect('issue_book')
                
        if not due_date:
            due_date = (timezone.now().date() + timedelta(days=14)).strftime('%Y-%m-%d')
            
        issue_id = generate_uuid()[:15]
        
        issues_collection.insert_one({
            '_id': issue_id,
            'issue_id': issue_id,
            'book_id': book_id,
            'member_name': member_name_clean,
            'member_id': member_id_clean,
            'issue_date': timezone.now().strftime('%Y-%m-%d'),
            'due_date': due_date,
            'return_date': None,
            'status': 'issued',
            'fine': 0,
            'renewed': False,
            'renewal_date': None
        })
        
        books_collection.update_one(
            {'_id': book_id},
            {'$inc': {'available_copies': -1, 'issue_count': 1}}
        )
        print("DEBUG: Success issuing book!")
        messages.success(request, f'Book issued successfully! Issue ID: {issue_id}')
        return redirect('issued')
        
    book_id = request.GET.get('book_id')
    selected_book = format_book(books_collection.find_one({'_id': book_id})) if book_id else None
    books_list = [format_book(b) for b in books_collection.find({'available_copies': {'$gt': 0}})]
    
    today = timezone.now().strftime('%Y-%m-%d')
    default_due = (timezone.now() + timedelta(days=14)).strftime('%Y-%m-%d')
    
    return render(request, 'issue_book.html', {
        'books': books_list,
        'selected_book': selected_book,
        'today': today,
        'default_due': default_due
    })

def return_book(request):
    record = None
    fine = 0
    days_overdue = 0
    today_date = timezone.now().date()
    today_str = today_date.strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        issue_id = request.POST.get('issue_id')
        
        if action == 'search':
            record = format_issue(issues_collection.find_one({'issue_id': issue_id}))
            if not record:
                messages.error(request, 'Issue record not found. Check the Issue ID.')
            elif record.get('status') == 'returned':
                messages.warning(request, 'This book has already been returned.')
                record = None
            else:
                due_date = datetime.strptime(record['due_date'], '%Y-%m-%d').date()
                days_overdue = max(0, (today_date - due_date).days)
                fine = days_overdue * get_fine_rate()
                
                book = format_book(books_collection.find_one({'_id': record['book_id']}))
                if book:
                    record['book_title'] = book.get('title')
                    record['book_author'] = book.get('author')
                    record['book_isbn'] = book.get('isbn')
                
        elif action == 'confirm':
            record = format_issue(issues_collection.find_one({'issue_id': issue_id}))
            if record and record.get('status') != 'returned':
                due_date = datetime.strptime(record['due_date'], '%Y-%m-%d').date()
                days_overdue = max(0, (today_date - due_date).days)
                fine_amount = days_overdue * get_fine_rate()
                
                issues_collection.update_one(
                    {'issue_id': issue_id},
                    {'$set': {
                        'return_date': today_str,
                        'fine': fine_amount,
                        'status': 'returned'
                    }}
                )
                
                books_collection.update_one(
                    {'_id': record['book_id']},
                    {'$inc': {'available_copies': 1}}
                )
                # Cap available_copies to total_copies
                book = books_collection.find_one({'_id': record['book_id']})
                if book and book.get('available_copies', 0) > book.get('total_copies', 0):
                    books_collection.update_one(
                        {'_id': record['book_id']},
                        {'$set': {'available_copies': book.get('total_copies')}}
                    )
                
                messages.success(request, f'Book returned successfully! Fine collected: ₹{fine_amount}')
                return redirect('issued')
                
    return render(request, 'return_book.html', {
        'record': record,
        'fine': fine,
        'days_overdue': days_overdue,
        'today': today_str
    })

def issued(request):
    today_date = timezone.now().date()
    records = [format_issue(i) for i in issues_collection.find({'status': 'issued'})]
    
    for r in records:
        due_date = datetime.strptime(r['due_date'], '%Y-%m-%d').date()
        r['days_remaining'] = (due_date - today_date).days
        book = format_book(books_collection.find_one({'_id': r['book_id']}))
        if book:
            r['book_title'] = book.get('title')
            r['book_author'] = book.get('author')
        
    records = sorted(records, key=lambda x: x.get('days_remaining', 0))
    return render(request, 'issued.html', {'records': records})

def overdue(request):
    today_date = timezone.now().date()
    today_str = today_date.strftime('%Y-%m-%d')
    overdue_qs = list(issues_collection.find({'status': 'issued', 'due_date': {'$lt': today_str}}))
    
    overdue_list = []
    total_fine = 0
    
    for r in overdue_qs:
        r = format_issue(r)
        due_date = datetime.strptime(r['due_date'], '%Y-%m-%d').date()
        days_overdue = (today_date - due_date).days
        r['days_overdue'] = days_overdue
        r['estimated_fine'] = days_overdue * get_fine_rate()
        total_fine += r['estimated_fine']
        
        book = format_book(books_collection.find_one({'_id': r['book_id']}))
        if book:
            r['book_title'] = book.get('title')
            r['book_author'] = book.get('author')
            
        overdue_list.append(r)
        
    overdue_list.sort(key=lambda x: -x.get('days_overdue', 0))
    
    return render(request, 'overdue.html', {
        'overdue_list': overdue_list,
        'total_fine': total_fine
    })

def member_history(request):
    profile = None
    records = []
    member_id = ''
    
    if request.method == 'POST':
        member_id = request.POST.get('member_id', '').strip().upper()
        if member_id:
            all_records = list(issues_collection.find({'member_id': member_id}).sort('issue_date', -1))
            
            if all_records:
                today_date = timezone.now().date()
                total = len(all_records)
                returned = sum(1 for r in all_records if r.get('status') == 'returned')
                current = sum(1 for r in all_records if r.get('status') == 'issued')
                total_fine = sum(r.get('fine', 0) for r in all_records if r.get('status') == 'returned')
                
                for r in all_records:
                    r = format_issue(r)
                    book = format_book(books_collection.find_one({'_id': r['book_id']}))
                    if book:
                        r['book_title'] = book.get('title')
                        
                    if r.get('status') == 'issued':
                        due_date = datetime.strptime(r['due_date'], '%Y-%m-%d').date()
                        days_overdue = (today_date - due_date).days
                        r['estimated_fine'] = days_overdue * get_fine_rate() if days_overdue > 0 else 0
                        r['days_remaining'] = (due_date - today_date).days
                    records.append(r)
                    
                profile = {
                    'member_id': member_id,
                    'member_name': all_records[0].get('member_name'),
                    'total_borrowed': total,
                    'total_returned': returned,
                    'currently_issued': current,
                    'total_fines': total_fine
                }
            else:
                messages.warning(request, f'No records found for Member ID: {member_id}')
                
    return render(request, 'member_history.html', {
        'profile': profile,
        'records': records,
        'member_id': member_id
    })

def delete_book(request, book_id):
    book_id_str = str(book_id)
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '')
        if confirm != 'YES':
            messages.warning(request, 'Deletion cancelled. You must type YES to confirm.')
            return redirect('books')
            
        book = format_book(books_collection.find_one({'_id': book_id_str}))
        if book:
            if book.get('available_copies', 0) < book.get('total_copies', 0):
                messages.error(request, f"{book.get('total_copies', 0) - book.get('available_copies', 0)} copy/copies are currently issued. Return them first.")
            else:
                books_collection.delete_one({'_id': book_id_str})
                messages.success(request, 'Book deleted successfully.')
        else:
            messages.error(request, 'Book not found.')
            
    return redirect('books')

def renew(request, issue_id):
    if request.method == 'POST':
        record = format_issue(issues_collection.find_one({'issue_id': issue_id}))
        if not record:
            messages.error(request, 'Issue record not found.')
        elif record.get('status') == 'returned':
            messages.error(request, 'This book has already been returned.')
        elif record.get('renewed'):
            messages.error(request, 'This book has already been renewed once.')
        else:
            today_date = timezone.now().date()
            due_date = datetime.strptime(record['due_date'], '%Y-%m-%d').date()
            if today_date > due_date:
                messages.error(request, 'Cannot renew an overdue book. Please return it and pay the fine.')
            else:
                new_due = (due_date + timedelta(days=7)).strftime('%Y-%m-%d')
                issues_collection.update_one(
                    {'issue_id': issue_id},
                    {'$set': {
                        'due_date': new_due,
                        'renewed': True,
                        'renewal_date': today_date.strftime('%Y-%m-%d')
                    }}
                )
                
                messages.success(request, f'Book renewed successfully! New due date: {datetime.strptime(new_due, "%Y-%m-%d").strftime("%B %d, %Y")}')
                
    return redirect('issued')

def report(request):
    today_date = timezone.now().date()
    today_str = today_date.strftime('%Y-%m-%d')
    
    total_books = books_collection.count_documents({})
    total_titles = len(books_collection.distinct('isbn'))
    
    book_stats = list(books_collection.aggregate([{
        '$group': {
            '_id': None, 
            'total_copies': {'$sum': '$total_copies'},
            'available': {'$sum': '$available_copies'}
        }
    }]))
    
    if book_stats:
        total_copies = book_stats[0]['total_copies']
        available = book_stats[0]['available']
    else:
        total_copies = 0
        available = 0
        
    issued_count = issues_collection.count_documents({'status': 'issued'})
    overdue_qs = list(issues_collection.find({'status': 'issued', 'due_date': {'$lt': today_str}}))
    overdue_count = len(overdue_qs)
    
    estimated_fines = 0
    for r in overdue_qs:
        due_date = datetime.strptime(r['due_date'], '%Y-%m-%d').date()
        estimated_fines += (today_date - due_date).days * get_fine_rate()
        
    fines_res = list(issues_collection.aggregate([
        {'$match': {'status': 'returned'}},
        {'$group': {'_id': None, 'fines_collected': {'$sum': '$fine'}}}
    ]))
    fines_collected = fines_res[0]['fines_collected'] if fines_res else 0
    
    genre_res = list(books_collection.aggregate([{'$group': {'_id': '$genre', 'count': {'$sum': 1}}}]))
    genre_counts = {g['_id']: g['count'] for g in genre_res if g['_id']}
    
    popular_books = [format_book(b) for b in books_collection.find().sort('issue_count', -1).limit(5)]
    max_issue_count = popular_books[0].get('issue_count') if popular_books and popular_books[0].get('issue_count', 0) > 0 else 1
    activity = get_activity_data(30)
    
    genre_distribution = []
    if total_titles > 0:
        for g, c in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True):
            genre_distribution.append({
                'genre': g,
                'count': c,
                'pct': round((c / total_titles) * 100, 1),
                'pct_int': int(round((c / total_titles) * 100))
            })
            
    data = {
        'total_books': total_books,
        'total_titles': total_titles,
        'total_copies': total_copies,
        'available': available,
        'issued_count': issued_count,
        'overdue_count': overdue_count,
        'estimated_fines': estimated_fines,
        'fines_collected': fines_collected,
        'genre_counts': json.dumps(genre_counts),
        'genre_distribution': genre_distribution,
        'popular_books': popular_books,
        'max_issue_count': max_issue_count,
        'activity': activity
    }
    
    return render(request, 'report.html', {'data': data})

def settings(request):
    config = get_config()
    
    if request.method == 'POST':
        fine_rate_str = request.POST.get('fine_per_day')
        try:
            fine_rate = int(fine_rate_str)
            if fine_rate < 0:
                messages.error(request, 'Fine rate cannot be negative.')
            else:
                set_fine_rate(fine_rate)
                config['fine_per_day'] = fine_rate
                messages.success(request, 'Settings saved successfully.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid fine rate value.')
            
        return redirect('settings')
        
    return render(request, 'settings.html', {'config': config})

# API Endpoints

def api_validate_isbn(request):
    isbn = request.GET.get('isbn', '')
    isbn_clean = isbn.replace('-', '').replace(' ', '')
    is_valid = isbn_clean.isdigit() and len(isbn_clean) == 13
    is_unique = not books_collection.find_one({'isbn': isbn_clean})
    return JsonResponse({'valid': is_valid, 'unique': is_unique, 'clean': isbn_clean})

def api_activity(request):
    days = int(request.GET.get('days', 7))
    data = get_activity_data(days)
    return JsonResponse(data)

def api_book(request, book_id):
    book_id_str = str(book_id)
    book = format_book(books_collection.find_one({'_id': book_id_str}))
    if book:
        return JsonResponse({
            'id': str(book.get('id')),
            'title': book.get('title'),
            'author': book.get('author'),
            'genre': book.get('genre'),
            'isbn': book.get('isbn'),
            'total_copies': book.get('total_copies'),
            'available_copies': book.get('available_copies')
        })
    else:
        return JsonResponse({'error': 'Not found'}, status=404)
