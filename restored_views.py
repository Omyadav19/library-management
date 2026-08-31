from pymongo import MongoClient
...'.\n</bash_command_reminder>\n</EPHEMERAL_MESSAGE>"}

# Connect to MongoDB Atlas instance
client = MongoClient('mongodb+srv://ryadavom94_db_user:ryadavom94_db_user@cluster0.gknyteu.mongodb.net/?appName=Cluster0', serverSelectionTimeoutMS=5000)

# Select the library database
db = client['library_db']

# Collections
books_collection = db['books']
issues_collection = db['issues']
config_collection = db['config']

# Ensure indexes
books_collection.create_index('isbn', unique=True)
issues_collection.create_index('issue_id', unique=True)

# Helper function to get config
def get_config():

def get_activity_data(days=30):
    today = timezone.now().date()
    start = today - timedelta(days=days)
    labels = []
    issued_data = []
    returned_data = []
    
    for i in range(days + 1):
        d = start + timedelta(days=i)
        labels.append(d.strftime('%Y-%m-%d'))
        issued_data.append(IssueRecord.objects.filter(issue_date=d).count())
        returned_data.append(IssueRecord.objects.filter(return_date=d).count())
        
    return {'labels': labels, 'issued': issued_data, 'returned': returned_data}

def dashboard(request):
    today = timezone.now().date()
    books = Book.objects.all()
    
    total_books = books.aggregate(Sum('total_copies'))['total_copies__sum'] or 0
    available = books.aggregate(Sum('available_copies'))['available_copies__sum'] or 0
    issued_count = IssueRecord.objects.filter(status='issued').count()
    
    overdue_qs = IssueRecord.objects.filter(status='issued', due_date__lt=today)
    overdue_count = overdue_qs.count()
    
    overdue_list = []
    for r in overdue_qs.order_by('due_date'):
        days_overdue = (today - r.due_date).days
        r.days_overdue = days_overdue
        r.estimated_fine = days_overdue * get_fine_rate()
        overdue_list.append(r)
        
    fines_collected = IssueRecord.objects.filter(status='returned').aggregate(Sum('fine'))['fine__sum'] or 0
    
    genre_counts = dict(books.values('genre').annotate(count=Count('genre')).values_list('genre', 'count'))
    popular_books = list(books.order_by('-issue_count')[:5])
    recent_books  = list(books.order_by('-added_on')[:5])
    activity_7    = get_activity_data(7)

    total_members = IssueRecord.objects.values('member_id').distinct().count()
    total_issues_ever = IssueRecord.objects.count()
    recent_transactions = IssueRecord.objects.order_by('-issue_date', '-id')[:6]

    # Pre-compute values that Jinja2 could inline but Django cannot
    availability_pct = round((available / total_books) * 100) if total_books > 0 else 0
    issued_pct = round((issued_count / total_books) * 100) if total_books > 0 else 0
    overdue_pct = round((overdue_count / issued_count) * 100) if issued_count > 0 else 0
    overdue_len      = len(overdue_list)
    genre_counts_json = json.dumps(genre_counts)

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
        'genre_counts_json': genre_counts_json,
        'popular_books': popular_books,
        'recent_books': recent_books,
        'overdue_list': overdue_list,
        'overdue_len': overdue_len,
        'activity_7': activity_7,
        'total_members': total_members,
        'total_issues_ever': total_issues_ever,
        'recent_transactions': recent_transactions,
    }

    now = timezone.now()
    hour = now.hour
    if hour < 12:
        greeting = 'Good morning'
    elif hour < 17:
        greeting = 'Good afternoon'
    else:
        greeting = 'Good evening'

    date_str = now.strftime('%A, %B %d, %Y')

    return render(request, 'dashboard.html', {
        'stats': stats,
        'greeting': greeting,
        'date_str': date_str
    })

def books_view(request):
    search = request.GET.get('search', '')
    genre_filter = request.GET.get('genre', 'All')
    availability = request.GET.get('availability', '')
    sort_by = request.GET.get('sort', 'title')
    
    books = Book.objects.all()
    
    if search:
        books = books.filter(title__icontains=search) | \
                books.filter(author__icontains=search) | \
                books.filter(genre__icontains=search) | \
                books.filter(isbn__icontains=search)
                
    if genre_filter and genre_filter != 'All':
        books = books.filter(genre__iexact=genre_filter)
        
    if availability == 'available':
        books = books.filter(available_copies__gt=0)
    elif availability == 'unavailable':
        books = books.filter(available_copies=0)
        
    sort_map = {
        'title': 'title',
        'author': 'author',
        'genre': 'genre',
        'available': 'available_copies',
        'popular': '-issue_count',
    }
    books = books.order_by(sort_map.get(sort_by, 'title'))
    
    genres = list(Book.objects.values_list('genre', flat=True).distinct().order_by('genre'))
    
    return render(request, 'books.html', {
        'books': books,
        'genres': genres,
        'search': search,
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
            
        if Book.objects.filter(isbn=isbn_clean).exists():
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
            
        Book.objects.create(
            title=title.strip(),
            author=author.strip(),
            genre=genre.strip(),
            isbn=isbn_clean,
            total_copies=total_copies,
            available_copies=total_copies
        )
        messages.success(request, 'Book added successfully.')
        return redirect('books')
        
    return render(request, 'add_book.html', {'genres': ALL_GENRES})

def search(request):
    query = request.GET.get('q', '')
    genre_filter = request.GET.get('genre', 'All')
    
    results = Book.objects.all()
    if query:
        results = results.filter(title__icontains=query) | \
                  results.filter(author__icontains=query) | \
                  results.filter(genre__icontains=query) | \
                  results.filter(isbn__icontains=query)
                  
    if genre_filter != 'All':
        results = results.filter(genre__iexact=genre_filter)
        
    db_genres = list(Book.objects.values_list('genre', flat=True).distinct())
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
        
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            messages.error(request, 'Book not found.')
            return redirect('issue_book')
            
        if book.available_copies < 1:
            messages.error(request, 'No copies available for this book.')
            return redirect('issue_book')
            
        if not member_name.strip() or not member_id.strip():
            messages.error(request, 'Member name and ID are required.')
            return redirect('issue_book')
            
        member_name_clean = member_name.strip()
        member_id_clean = member_id.strip().upper()
        
        existing_member = IssueRecord.objects.filter(member_id=member_id_clean).first()
        if existing_member and existing_member.member_name.lower() != member_name_clean.lower():
            messages.error(request, f"This Member ID is already registered to '{existing_member.member_name}'.")
            return redirect('issue_book')
            
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                if due_date <= timezone.now().date():
                    messages.error(request, 'Due date must be in the future.')
                    return redirect('issue_book')
            except ValueError:
                messages.error(request, 'Invalid due date format.')
                return redirect('issue_book')
                
        issue = IssueRecord(
            book=book,
            member_name=member_name.strip(),
            member_id=member_id.strip().upper(),
            due_date=due_date if due_date else (timezone.now().date() + timedelta(days=14))
        )
        issue.save()
        
        book.available_copies -= 1
        book.issue_count += 1
        book.save()
        
        messages.success(request, f'Book issued successfully! Issue ID: {issue.issue_id}')
        return redirect('issued')
        
    book_id = request.GET.get('book_id')
    selected_book = Book.objects.filter(id=book_id).first() if book_id else None
    books_list = Book.objects.filter(available_copies__gt=0)
    
    today = timezone.now().date().strftime('%Y-%m-%d')
    default_due = (timezone.now().date() + timedelta(days=14)).strftime('%Y-%m-%d')
    
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
    today = timezone.now().date()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        issue_id = request.POST.get('issue_id')
        
        if action == 'search':
            record = IssueRecord.objects.filter(issue_id=issue_id).first()
            if not record:
                messages.error(request, 'Issue record not found. Check the Issue ID.')
            elif record.status == 'returned':
                messages.warning(request, 'This book has already been returned.')
                record = None
            else:
                days_overdue = max(0, (today - record.due_date).days)
                fine = days_overdue * get_fine_rate()
                
                # Add attributes needed by template
                record.book_title = record.book.title
                record.book_author = record.book.author
                record.book_isbn = record.book.isbn
                
        elif action == 'confirm':
            record = IssueRecord.objects.filter(issue_id=issue_id).first()
            if record and record.status != 'returned':
                days_overdue = max(0, (today - record.due_date).days)
                fine_amount = days_overdue * get_fine_rate()
                
                record.return_date = today
                record.fine = fine_amount
                record.status = 'returned'
                record.save()
                
                book = record.book
                book.available_copies = min(book.available_copies + 1, book.total_copies)
                book.save()
                
                messages.success(request, f'Book returned successfully! Fine collected: ₹{fine_amount}')
                return redirect('issued')
                
    return render(request, 'return_book.html', {
        'record': record,
        'fine': fine,
        'days_overdue': days_overdue,
        'today': today.strftime('%Y-%m-%d')
    })

def issued(request):
    today = timezone.now().date()
    records = IssueRecord.objects.filter(status='issued').select_related('book')
    
    for r in records:
        r.days_remaining = (r.due_date - today).days
        r.book_title = r.book.title
        r.book_author = r.book.author
        
    records = sorted(records, key=lambda x: x.days_remaining)
    return render(request, 'issued.html', {'records': records})

def overdue(request):
    today = timezone.now().date()
    overdue_qs = IssueRecord.objects.filter(status='issued', due_date__lt=today).select_related('book')
    
    overdue_list = []
    total_fine = 0
    
    for r in overdue_qs:
        days_overdue = (today - r.due_date).days
        r.days_overdue = days_overdue
        r.estimated_fine = days_overdue * get_fine_rate()
        total_fine += r.estimated_fine
        
        r.book_title = r.book.title
        r.book_author = r.book.author
        overdue_list.append(r)
        
    overdue_list.sort(key=lambda x: -x.days_overdue)
    
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
            all_records = IssueRecord.objects.filter(member_id=member_id).order_by('-issue_date').select_related('book')
            
            if all_records.exists():
                today = timezone.now().date()
                total = all_records.count()
                returned = all_records.filter(status='returned').count()
                current = all_records.filter(status='issued').count()
                total_fine = all_records.filter(status='returned').aggregate(Sum('fine'))['fine__sum'] or 0
                
                for r in all_records:
                    r.book_title = r.book.title
                    if r.status == 'issued':
                        days_overdue = (today - r.due_date).days
                        r.estimated_fine = days_overdue * get_fine_rate() if days_overdue > 0 else 0
                        r.days_remaining = (r.due_date - today).days
                    records.append(r)
                    
                profile = {
                    'member_id': member_id,
                    'member_name': all_records.first().member_name,
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
    if request.method == 'POST':
        confirm = request.POST.get('confirm', '')
        if confirm != 'YES':
            messages.warning(request, 'Deletion cancelled. You must type YES to confirm.')
            return redirect('books')
            
        try:
            book = Book.objects.get(id=book_id)
            if book.available_copies < book.total_copies:
                messages.error(request, f"{book.total_copies - book.available_copies} copy/copies are currently issued. Return them first.")
            else:
                book.delete()
                messages.success(request, 'Book deleted successfully.')
        except Book.DoesNotExist:
            messages.error(request, 'Book not found.')
            
    return redirect('books')

def renew(request, issue_id):
    if request.method == 'POST':
        record = IssueRecord.objects.filter(issue_id=issue_id).first()
        if not record:
            messages.error(request, 'Issue record not found.')
        elif record.status == 'returned':
            messages.error(request, 'This book has already been returned.')
        elif record.renewed:
            messages.error(request, 'This book has already been renewed once.')
        else:
            today = timezone.now().date()
            if today > record.due_date:
                messages.error(request, 'Cannot renew an overdue book. Please return it and pay the fine.')
            else:
                record.due_date = record.due_date + timedelta(days=7)
                record.renewed = True
                record.renewal_date = today
                record.save()
                messages.success(request, f'Book renewed successfully! New due date: {record.due_date.strftime("%B %d, %Y")}')
                
    return redirect('issued')

def report(request):
    today = timezone.now().date()
    books = Book.objects.all()
    
    total_books = books.count()
    total_titles = books.values('isbn').distinct().count()
    total_copies = books.aggregate(Sum('total_copies'))['total_copies__sum'] or 0
    available = books.aggregate(Sum('available_copies'))['available_copies__sum'] or 0
    
    issued_count = IssueRecord.objects.filter(status='issued').count()
    overdue_qs = IssueRecord.objects.filter(status='issued', due_date__lt=today)
    overdue_count = overdue_qs.count()
    
    estimated_fines = 0
    for r in overdue_qs:
        estimated_fines += (today - r.due_date).days * get_fine_rate()
        
    fines_collected = IssueRecord.objects.filter(status='returned').aggregate(Sum('fine'))['fine__sum'] or 0
    
    genre_counts = dict(books.values('genre').annotate(count=Count('genre')).values_list('genre', 'count'))
    popular_books = list(books.order_by('-issue_count')[:5])
    max_issue_count = popular_books[0].issue_count if popular_books and popular_books[0].issue_count > 0 else 1
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
    config, _ = LibraryConfig.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        fine_rate_str = request.POST.get('fine_per_day')
        try:
            fine_rate = int(fine_rate_str)
            if fine_rate < 0:
                messages.error(request, 'Fine rate cannot be negative.')
            else:
                config.fine_per_day = fine_rate
                config.save()
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
    is_unique = not Book.objects.filter(isbn=isbn_clean).exists()
    return JsonResponse({'valid': is_valid, 'unique': is_unique, 'clean': isbn_clean})

def api_activity(request):
    days = int(request.GET.get('days', 7))
    data = get_activity_data(days)
    return JsonResponse(data)

def api_book(request, book_id):
    try:
        book = Book.objects.get(id=book_id)
        return JsonResponse({
            'id': str(book.id),
            'title': book.title,
            'author': book.author,
            'genre': book.genre,
            'isbn': book.isbn,
            'total_copies': book.total_copies,
            'available_copies': book.available_copies
        })
    except Book.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

  margin-bottom: var(--spacing-2xl);
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  position: relative;
  overflow: hidden;
  transition: all var(--transition-base);
  cursor: default;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--grad);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: var(--border-accent);
  box-shadow: var(--shadow-lg), var(--shadow-glow-indigo);
}

.stat-card:hover::before { opacity: 0.04; }

.stat-icon {
document.addEventListener('DOMContentLoaded', initReportGenreChart);
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
document.addEventListener('DOMContentLoaded', () => {
  position: relative;
  z-index: 1;
}

.stat-icon-indigo { background: rgba(99, 102, 241, 0.15); }
.stat-icon-violet { background: rgba(139, 92, 246, 0.15); }
}

document.addEventListener('DOMContentLoaded', initSearchPage);

// ── Print / Export ────────────────────────────────────────────────────────────

function printReport() {
  window.print();
}

function exportReport() {
  const content = document.getElementById('reportContent');
  if (!content) return;
  const text = content.innerText;
  const blob = new Blob([text], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `Library_Report_${new Date().toISOString().slice(0,10)}.txt`;
  a.click();
  URL.revokeObjectURL(a.href);
  showToast('success', 'Report exported', 'Report saved as .txt file');
}

document.addEventListener('DOMContentLoaded', initSearchPage);

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// Animate numbers on dashboard
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.stat-value[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    if (isNaN(target)) return;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 40));
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      const prefix = el.dataset.prefix || '';
      const suffix = el.dataset.suffix || '';
      el.textContent = prefix + current.toLocaleString('en-IN') + suffix;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
});

// Date auto-fill
document.addEventListener('DOMContentLoaded', () => {
  const today = new Date();
  const dateStr = today.toISOString().slice(0, 10);
  document.querySelectorAll('input[type="date"][data-today]').forEach(el => {
document.addEventListener('DOMContentLoaded', () => {
  });
  document.querySelectorAll('input[type="date"][data-due]').forEach(el => {
    if (!el.value) {
      const due = new Date(today);
      due.setDate(due.getDate() + 14);
      el.value = due.toISOString().slice(0, 10);
    }
  });
});

// Renew confirmation
function confirmRenew(issueId, title) {
  if (confirm(`Renew "${title}"? This will extend the due date by 7 days.`)) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/renew/${issueId}`;
document.addEventListener('DOMContentLoaded', () => {
    form.submit();
  }
}























  position: relative;
  height: 240px;
}

/* Chart legend */
.chart-legend {
  display: flex;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-md);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.legend-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
}

/* ── Popular Books ───────────────────────────────────────────────────────────── */
.popular-books-list { display: flex; flex-direction: column; gap: var(--spacing-md); }

.popular-book-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  transition: all var(--transition-base);
}

.popular-book-item:hover {
  border-color: var(--border-hover);
  background: var(--bg-glass-hover);
  transform: translateX(4px);
}

.book-rank {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 800;
  color: var(--text-muted);
  width: 36px;
  text-align: center;
  flex-shrink: 0;
}

.book-rank.rank-1 { color: #fbbf24; }
.book-rank.rank-2 { color: #94a3b8; }
.book-rank.rank-3 { color: #cd7c2f; }

.popular-book-cover {
  width: 42px; height: 56px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  background: var(--grad-indigo);
  box-shadow: var(--shadow-md);
}

.popular-book-info { flex: 1; min-width: 0; }

.popular-book-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.popular-book-author { font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }

.popularity-bar {
  height: 4px;
  background: var(--bg-glass);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.popularity-fill {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--grad-indigo);
  transition: width 1s cubic-bezier(0.4,0,0.2,1);
}

.popularity-count {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* ── Quick Actions ───────────────────────────────────────────────────────────── */
.quick-actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-2xl);
}

.quick-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xl);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  transition: all var(--transition-spring);
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  position: relative;
  overflow: hidden;
}

.quick-action-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--btn-grad);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.quick-action-btn:hover {
  transform: translateY(-4px) scale(1.01);
  border-color: var(--border-accent);
  color: white;
  box-shadow: var(--shadow-lg);
}

.quick-action-btn:hover::before { opacity: 1; }

.quick-action-btn .action-icon {
  width: 48px; height: 48px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  background: var(--btn-grad);
  transition: all var(--transition-spring);
  position: relative;
  z-index: 1;
}

.quick-action-btn:hover .action-icon { transform: scale(1.15) rotate(-5deg); }

.quick-action-btn .action-label {
  position: relative;
  z-index: 1;
  transition: color var(--transition-base);
}

/* ── Overdue Alert ───────────────────────────────────────────────────────────── */
.overdue-alert {
  background: rgba(244, 63, 94, 0.08);
  border: 1px solid rgba(244, 63, 94, 0.25);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  position: relative;
  overflow: hidden;
  margin-bottom: var(--spacing-2xl);
}

.overdue-alert::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--grad-rose);
}

.alert-ok {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.25);
}

.alert-ok::before { background: var(--grad-emerald); }

/* ── Buttons ─────────────────────────────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  border: none;
  font-size: 14px;
  font-weight: 600;
  font-family: var(--font-body);
  transition: all var(--transition-base);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  white-space: nowrap;
}

.btn::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0);
  transition: background var(--transition-fast);
}

.btn:hover::after { background: rgba(255,255,255,0.06); }
.btn:active { transform: scale(0.97); }

.btn-primary {
  background: var(--grad-indigo);
  color: white;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

.btn-primary:hover { box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5); transform: translateY(-1px); }

.btn-secondary {
  background: var(--bg-glass);
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--bg-glass-hover);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.btn-danger {
  background: var(--grad-rose);
  color: white;
  box-shadow: 0 4px 14px rgba(244, 63, 94, 0.3);
}

.btn-danger:hover { box-shadow: 0 6px 20px rgba(244, 63, 94, 0.45); transform: translateY(-1px); }

.btn-warning {
  background: var(--grad-amber);




.btn-lg { padding: 14px 28px; font-size: 16px; }
.btn-full { width: 100%; }
.btn-icon { width: 36px; height: 36px; padding: 0; border-radius: var(--radius-md); }

/* ── Forms ───────────────────────────────────────────────────────────────────── */
.form-group { margin-bottom: var(--spacing-lg); }

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
  letter-spacing: 0.3px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  background: var(--bg-glass);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: var(--font-body);
  transition: all var(--transition-base);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--indigo);
  background: rgba(99, 102, 241, 0.08);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
}

.form-input::placeholder { color: var(--text-muted); }
.form-input.error { border-color: var(--rose); box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.1); }
.form-input.success { border-color: var(--emerald); box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1); }

.form-select {
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 14px center;
  padding-right: 40px;
}

.form-select option { background: var(--bg-secondary); color: var(--text-primary); }

.form-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

.form-error { font-size: 12px; color: var(--rose); margin-top: 6px; }
.form-success { font-size: 12px; color: var(--emerald); margin-top: 6px; }

.isbn-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  margin-top: 6px;
}

.isbn-status.valid { color: var(--emerald); }
.isbn-status.invalid { color: var(--rose); }

/* ── Table ───────────────────────────────────────────────────────────────────── */
.table-container {
  overflow-x: auto;
  border-radius: var(--radius-xl);
  border: 1px solid var(--border);
  background: var(--bg-card);
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead th {
  padding: 14px var(--spacing-lg);
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

tbody tr {
  border-bottom: 1px solid var(--border);
  transition: background var(--transition-fast);
}

tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: var(--bg-glass-hover); }

tbody td {
  padding: 16px var(--spacing-lg);
  font-size: 14px;
  color: var(--text-primary);
  vertical-align: middle;
}

/* Book cell */
.book-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.book-cover-mini {
  width: 38px; height: 50px;
  border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.book-title-text { font-weight: 600; color: var(--text-primary); }
.book-author-text { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

/* ── Badges / Pills ──────────────────────────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
