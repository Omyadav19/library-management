import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, Query, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from library.db import (
    books_collection,
    issues_collection,
    config_collection,
    get_config,
    set_fine_rate,
    generate_uuid
)

app = FastAPI(title="LIBRA - Library Management System")

# Session middleware for flash messages
SECRET_KEY = os.getenv("SECRET_KEY", "libra-super-secret-key-fastapi-2026")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Helper for flash messages in sessions
def flash(request: Request, message: str, category: str = "info"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "tags": category})

def get_flashed_messages(request: Request):
    return request.session.pop("_messages", [])

# Custom Jinja context processor
def render_template(template_name: str, request: Request, context: dict = None, status_code: int = 200):
    if context is None:
        context = {}
    context["request"] = request
    context["messages"] = get_flashed_messages(request)
    return templates.TemplateResponse(request=request, name=template_name, context=context, status_code=status_code)

def get_fine_rate():
    return get_config().get("fine_per_day", 5)

ALL_GENRES = [
    "Fiction", "Non-Fiction", "Science", "Technology", "Biography",
    "History", "Philosophy", "Self-Help", "Psychology", "Economics",
    "Literature", "Poetry", "Drama", "Horror", "Mystery", "Romance",
    "Fantasy", "Science Fiction", "Children", "Reference", "Other"
]

def format_book(b):
    if not b:
        return None
    b["id"] = str(b.get("_id"))
    return b

def format_issue(i):
    if not i:
        return None
    i["id"] = str(i.get("_id"))
    return i

def get_activity_data(days: int = 30):
    today = date.today()
    start = today - timedelta(days=days)
    labels = []
    issued_data = []
    returned_data = []
    
    for i in range(days + 1):
        d = start + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        labels.append(d_str)
        issued_data.append(issues_collection.count_documents({"issue_date": d_str}))
        returned_data.append(issues_collection.count_documents({"return_date": d_str}))
        
    return {"labels": labels, "issued": issued_data, "returned": returned_data}


# ── Web Endpoints ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    
    pipeline = [
        {"$group": {
            "_id": None, 
            "total_books": {"$sum": "$total_copies"},
            "available": {"$sum": "$available_copies"}
        }}
    ]
    book_stats = list(books_collection.aggregate(pipeline))
    if book_stats:
        total_books = book_stats[0]["total_books"]
        available = book_stats[0]["available"]
    else:
        total_books = 0
        available = 0
        
    issued_count = issues_collection.count_documents({"status": "issued"})
    
    overdue_qs = list(issues_collection.find({"status": "issued", "due_date": {"$lt": today_str}}).sort("due_date", 1))
    overdue_count = len(overdue_qs)
    
    overdue_list = []
    for r in overdue_qs:
        r = format_issue(r)
        book = format_book(books_collection.find_one({"_id": r["book_id"]}))
        if book:
            r["book_title"] = book.get("title")
            r["book_author"] = book.get("author")
        
        due_date_obj = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
        days_overdue = (today_date - due_date_obj).days
        r["days_overdue"] = days_overdue
        r["estimated_fine"] = days_overdue * get_fine_rate()
        overdue_list.append(r)
        
    fines_pipeline = [
        {"$match": {"status": "returned"}},
        {"$group": {"_id": None, "fines_collected": {"$sum": "$fine"}}}
    ]
    fines_res = list(issues_collection.aggregate(fines_pipeline))
    fines_collected = fines_res[0]["fines_collected"] if fines_res else 0
    
    genre_pipeline = [
        {"$group": {"_id": "$genre", "count": {"$sum": 1}}}
    ]
    genre_res = list(books_collection.aggregate(genre_pipeline))
    genre_counts = {g["_id"]: g["count"] for g in genre_res if g["_id"]}
    
    popular_books = [format_book(b) for b in books_collection.find().sort("issue_count", -1).limit(5)]
    recent_books  = [format_book(b) for b in books_collection.find().sort("added_on", -1).limit(5)]
    activity_7    = get_activity_data(7)

    total_members = len(issues_collection.distinct("member_id"))
    total_issues_ever = issues_collection.count_documents({})
    recent_transactions = [format_issue(i) for i in issues_collection.find().sort([("issue_date", -1), ("_id", -1)]).limit(6)]
    
    for r in recent_transactions:
        book = format_book(books_collection.find_one({"_id": r["book_id"]}))
        if book:
            r["book_title"] = book.get("title")

    availability_pct = round((available / total_books) * 100) if total_books > 0 else 0
    issued_pct = round((issued_count / total_books) * 100) if total_books > 0 else 0
    overdue_pct = round((overdue_count / issued_count) * 100) if issued_count > 0 else 0
    
    stats = {
        "total_books": total_books,
        "available": available,
        "issued_count": issued_count,
        "overdue_count": overdue_count,
        "availability_pct": availability_pct,
        "issued_pct": issued_pct,
        "overdue_pct": overdue_pct,
        "fines_collected": fines_collected,
        "genre_counts": genre_counts,
        "genre_counts_json": json.dumps(genre_counts),
        "popular_books": popular_books,
        "recent_books": recent_books,
        "overdue_list": overdue_list,
        "overdue_len": len(overdue_list),
        "activity_7": activity_7,
        "total_members": total_members,
        "total_issues_ever": total_issues_ever,
        "recent_transactions": recent_transactions,
    }

    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    date_str = now.strftime("%A, %B %d, %Y")

    return render_template("dashboard.html", request, {
        "stats": stats,
        "greeting": greeting,
        "date_str": date_str
    })


@app.get("/books", response_class=HTMLResponse)
async def books_view(
    request: Request,
    search: str = Query("", alias="search"),
    genre: str = Query("All", alias="genre"),
    availability: str = Query("", alias="availability"),
    sort: str = Query("title", alias="sort")
):
    query = {}
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}},
            {"genre": {"$regex": search, "$options": "i"}},
            {"isbn": {"$regex": search, "$options": "i"}}
        ]
        
    if genre and genre != "All":
        query["genre"] = {"$regex": f"^{genre}$", "$options": "i"}
        
    if availability == "available":
        query["available_copies"] = {"$gt": 0}
    elif availability == "unavailable":
        query["available_copies"] = 0
        
    sort_map = {
        "title": ("title", 1),
        "author": ("author", 1),
        "genre": ("genre", 1),
        "available": ("available_copies", 1),
        "popular": ("issue_count", -1),
    }
    sort_field, sort_dir = sort_map.get(sort, ("title", 1))
    
    books = [format_book(b) for b in books_collection.find(query).sort(sort_field, sort_dir)]
    
    genres = books_collection.distinct("genre")
    genres = [g for g in genres if g]
    genres.sort()
    
    return render_template("books.html", request, {
        "books": books,
        "genres": genres,
        "search": search,
        "genre_filter": genre,
        "availability": availability,
        "sort_by": sort
    })


@app.get("/add_book", response_class=HTMLResponse)
async def add_book_get(request: Request):
    return render_template("add_book.html", request, {"genres": ALL_GENRES})


@app.post("/add_book")
async def add_book_post(
    request: Request,
    title: str = Form(""),
    author: str = Form(""),
    genre: str = Form(""),
    isbn: str = Form(""),
    total_copies: str = Form("")
):
    isbn_clean = isbn.replace("-", "").replace(" ", "")
    if not isbn_clean.isdigit() or len(isbn_clean) != 13:
        flash(request, "ISBN must contain exactly 13 digits.", "error")
        return render_template("add_book.html", request, {"genres": ALL_GENRES}, status_code=400)
        
    if books_collection.find_one({"isbn": isbn_clean}):
        flash(request, "A book with this ISBN already exists.", "error")
        return render_template("add_book.html", request, {"genres": ALL_GENRES}, status_code=400)
        
    try:
        copies_val = int(total_copies)
        if copies_val < 1:
            flash(request, "Total copies must be at least 1.", "error")
            return render_template("add_book.html", request, {"genres": ALL_GENRES}, status_code=400)
    except ValueError:
        flash(request, "Total copies must be a valid integer.", "error")
        return render_template("add_book.html", request, {"genres": ALL_GENRES}, status_code=400)
        
    books_collection.insert_one({
        "_id": generate_uuid(),
        "title": title.strip(),
        "author": author.strip(),
        "genre": genre.strip(),
        "isbn": isbn_clean,
        "total_copies": copies_val,
        "available_copies": copies_val,
        "issue_count": 0,
        "added_on": date.today().strftime("%Y-%m-%d")
    })
    flash(request, "Book added successfully.", "success")
    return RedirectResponse(url="/books", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/search", response_class=HTMLResponse)
async def search_view(
    request: Request,
    q: str = Query("", alias="q"),
    genre: str = Query("All", alias="genre")
):
    q_dict = {}
    if q:
        q_dict["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"author": {"$regex": q, "$options": "i"}},
            {"genre": {"$regex": q, "$options": "i"}},
            {"isbn": {"$regex": q, "$options": "i"}}
        ]
              
    if genre != "All":
        q_dict["genre"] = {"$regex": f"^{genre}$", "$options": "i"}
        
    results = [format_book(b) for b in books_collection.find(q_dict)]
        
    db_genres = [g for g in books_collection.distinct("genre") if g]
    all_genres_list = ["Fiction", "Non-Fiction", "Science", "Technology", "Biography", "Self-Help"]
    
    genres = sorted(list(set(db_genres + all_genres_list)))
    
    return render_template("search.html", request, {
        "results": results,
        "query": q,
        "genre_filter": genre,
        "all_genres_list": genres
    })


@app.get("/issue_book", response_class=HTMLResponse)
async def issue_book_get(request: Request, book_id: Optional[str] = Query(None)):
    selected_book = format_book(books_collection.find_one({"_id": book_id})) if book_id else None
    books_list = [format_book(b) for b in books_collection.find({"available_copies": {"$gt": 0}})]
    
    today = date.today().strftime("%Y-%m-%d")
    default_due = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
    
    return render_template("issue_book.html", request, {
        "books": books_list,
        "selected_book": selected_book,
        "today": today,
        "default_due": default_due
    })


@app.post("/issue_book")
async def issue_book_post(
    request: Request,
    book_id: str = Form(...),
    member_name: str = Form(...),
    member_id: str = Form(...),
    due_date: Optional[str] = Form(None)
):
    book = format_book(books_collection.find_one({"_id": book_id}))
    if not book:
        flash(request, "Book not found.", "error")
        return RedirectResponse(url="/issue_book", status_code=status.HTTP_303_SEE_OTHER)
        
    if book.get("available_copies", 0) < 1:
        flash(request, "No copies available for this book.", "error")
        return RedirectResponse(url="/issue_book", status_code=status.HTTP_303_SEE_OTHER)
        
    if not member_name.strip() or not member_id.strip():
        flash(request, "Member name and ID are required.", "error")
        return RedirectResponse(url="/issue_book", status_code=status.HTTP_303_SEE_OTHER)
        
    member_name_clean = member_name.strip()
    member_id_clean = member_id.strip().upper()
    
    existing_member = issues_collection.find_one({"member_id": member_id_clean})
    if existing_member and existing_member.get("member_name", "").lower() != member_name_clean.lower():
        flash(request, f"This Member ID is already registered to '{existing_member.get('member_name')}'.", "error")
        return RedirectResponse(url="/issue_book", status_code=status.HTTP_303_SEE_OTHER)
        
    final_due_date = None
    if due_date:
        try:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
            if due_date_obj <= date.today():
                flash(request, "Due date must be in the future.", "error")
                return RedirectResponse(url="/issue_book", status_code=status.HTTP_303_SEE_OTHER)
            final_due_date = due_date
        except ValueError:
            flash(request, "Invalid due date format.", "error")
            return RedirectResponse(url="/issue_book", status_code=status.HTTP_303_SEE_OTHER)
            
    if not final_due_date:
        final_due_date = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")
        
    issue_id = generate_uuid()[:15]
    
    issues_collection.insert_one({
        "_id": issue_id,
        "issue_id": issue_id,
        "book_id": book_id,
        "member_name": member_name_clean,
        "member_id": member_id_clean,
        "issue_date": date.today().strftime("%Y-%m-%d"),
        "due_date": final_due_date,
        "return_date": None,
        "status": "issued",
        "fine": 0,
        "renewed": False,
        "renewal_date": None
    })
    
    books_collection.update_one(
        {"_id": book_id},
        {"$inc": {"available_copies": -1, "issue_count": 1}}
    )
    flash(request, f"Book issued successfully! Issue ID: {issue_id}", "success")
    return RedirectResponse(url="/issued", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/return_book", response_class=HTMLResponse)
async def return_book_get(request: Request):
    today_str = date.today().strftime("%Y-%m-%d")
    return render_template("return_book.html", request, {
        "record": None,
        "fine": 0,
        "days_overdue": 0,
        "today": today_str
    })


@app.post("/return_book")
async def return_book_post(
    request: Request,
    action: str = Form(...),
    issue_id: str = Form(...)
):
    record = None
    fine = 0
    days_overdue = 0
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    
    if action == "search":
        record = format_issue(issues_collection.find_one({"issue_id": issue_id}))
        if not record:
            flash(request, "Issue record not found. Check the Issue ID.", "error")
        elif record.get("status") == "returned":
            flash(request, "This book has already been returned.", "warning")
            record = None
        else:
            due_date_obj = datetime.strptime(record["due_date"], "%Y-%m-%d").date()
            days_overdue = max(0, (today_date - due_date_obj).days)
            fine = days_overdue * get_fine_rate()
            
            book = format_book(books_collection.find_one({"_id": record["book_id"]}))
            if book:
                record["book_title"] = book.get("title")
                record["book_author"] = book.get("author")
                record["book_isbn"] = book.get("isbn")
            
    elif action == "confirm":
        record = format_issue(issues_collection.find_one({"issue_id": issue_id}))
        if record and record.get("status") != "returned":
            due_date_obj = datetime.strptime(record["due_date"], "%Y-%m-%d").date()
            days_overdue = max(0, (today_date - due_date_obj).days)
            fine_amount = days_overdue * get_fine_rate()
            
            issues_collection.update_one(
                {"issue_id": issue_id},
                {"$set": {
                    "return_date": today_str,
                    "fine": fine_amount,
                    "status": "returned"
                }}
            )
            
            books_collection.update_one(
                {"_id": record["book_id"]},
                {"$inc": {"available_copies": 1}}
            )
            
            # Cap available_copies to total_copies
            book = books_collection.find_one({"_id": record["book_id"]})
            if book and book.get("available_copies", 0) > book.get("total_copies", 0):
                books_collection.update_one(
                    {"_id": record["book_id"]},
                    {"$set": {"available_copies": book.get("total_copies")}}
                )
            
            flash(request, f"Book returned successfully! Fine collected: ₹{fine_amount}", "success")
            return RedirectResponse(url="/issued", status_code=status.HTTP_303_SEE_OTHER)
            
    return render_template("return_book.html", request, {
        "record": record,
        "fine": fine,
        "days_overdue": days_overdue,
        "today": today_str
    })


@app.get("/issued", response_class=HTMLResponse)
async def issued_view(request: Request):
    today_date = date.today()
    records = [format_issue(i) for i in issues_collection.find({"status": "issued"})]
    
    for r in records:
        due_date_obj = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
        r["days_remaining"] = (due_date_obj - today_date).days
        book = format_book(books_collection.find_one({"_id": r["book_id"]}))
        if book:
            r["book_title"] = book.get("title")
            r["book_author"] = book.get("author")
        
    records = sorted(records, key=lambda x: x.get("days_remaining", 0))
    return render_template("issued.html", request, {"records": records})


@app.get("/overdue", response_class=HTMLResponse)
async def overdue_view(request: Request):
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    overdue_qs = list(issues_collection.find({"status": "issued", "due_date": {"$lt": today_str}}))
    
    overdue_list = []
    total_fine = 0
    
    for r in overdue_qs:
        r = format_issue(r)
        due_date_obj = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
        days_overdue = (today_date - due_date_obj).days
        r["days_overdue"] = days_overdue
        r["estimated_fine"] = days_overdue * get_fine_rate()
        total_fine += r["estimated_fine"]
        
        book = format_book(books_collection.find_one({"_id": r["book_id"]}))
        if book:
            r["book_title"] = book.get("title")
            r["book_author"] = book.get("author")
            
        overdue_list.append(r)
        
    overdue_list.sort(key=lambda x: -x.get("days_overdue", 0))
    
    return render_template("overdue.html", request, {
        "overdue_list": overdue_list,
        "total_fine": total_fine
    })


@app.get("/member_history", response_class=HTMLResponse)
async def member_history_get(request: Request):
    return render_template("member_history.html", request, {
        "profile": None,
        "records": [],
        "member_id": ""
    })


@app.post("/member_history", response_class=HTMLResponse)
async def member_history_post(
    request: Request,
    member_id: str = Form("")
):
    profile = None
    records = []
    clean_id = member_id.strip().upper()
    
    if clean_id:
        all_records = list(issues_collection.find({"member_id": clean_id}).sort("issue_date", -1))
        
        if all_records:
            today_date = date.today()
            total = len(all_records)
            returned = sum(1 for r in all_records if r.get("status") == "returned")
            current = sum(1 for r in all_records if r.get("status") == "issued")
            total_fine = sum(r.get("fine", 0) for r in all_records if r.get("status") == "returned")
            
            for r in all_records:
                r = format_issue(r)
                book = format_book(books_collection.find_one({"_id": r["book_id"]}))
                if book:
                    r["book_title"] = book.get("title")
                    
                if r.get("status") == "issued":
                    due_date_obj = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
                    days_overdue = (today_date - due_date_obj).days
                    r["estimated_fine"] = days_overdue * get_fine_rate() if days_overdue > 0 else 0
                    r["days_remaining"] = (due_date_obj - today_date).days
                records.append(r)
                
            profile = {
                "member_id": clean_id,
                "member_name": all_records[0].get("member_name"),
                "total_borrowed": total,
                "total_returned": returned,
                "currently_issued": current,
                "total_fines": total_fine
            }
        else:
            flash(request, f"No records found for Member ID: {clean_id}", "warning")
            
    return render_template("member_history.html", request, {
        "profile": profile,
        "records": records,
        "member_id": clean_id
    })


@app.post("/delete_book/{book_id}")
async def delete_book_post(
    request: Request,
    book_id: str,
    confirm: str = Form("")
):
    if confirm != "YES":
        flash(request, "Deletion cancelled. You must type YES to confirm.", "warning")
        return RedirectResponse(url="/books", status_code=status.HTTP_303_SEE_OTHER)
        
    book = format_book(books_collection.find_one({"_id": book_id}))
    if book:
        if book.get("available_copies", 0) < book.get("total_copies", 0):
            flash(request, f"{book.get('total_copies', 0) - book.get('available_copies', 0)} copy/copies are currently issued. Return them first.", "error")
        else:
            books_collection.delete_one({"_id": book_id})
            flash(request, "Book deleted successfully.", "success")
    else:
        flash(request, "Book not found.", "error")
        
    return RedirectResponse(url="/books", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/renew/{issue_id}")
async def renew_post(request: Request, issue_id: str):
    record = format_issue(issues_collection.find_one({"issue_id": issue_id}))
    if not record:
        flash(request, "Issue record not found.", "error")
    elif record.get("status") == "returned":
        flash(request, "This book has already been returned.", "error")
    elif record.get("renewed"):
        flash(request, "This book has already been renewed once.", "error")
    else:
        today_date = date.today()
        due_date_obj = datetime.strptime(record["due_date"], "%Y-%m-%d").date()
        if today_date > due_date_obj:
            flash(request, "Cannot renew an overdue book. Please return it and pay the fine.", "error")
        else:
            new_due = (due_date_obj + timedelta(days=7)).strftime("%Y-%m-%d")
            issues_collection.update_one(
                {"issue_id": issue_id},
                {"$set": {
                    "due_date": new_due,
                    "renewed": True,
                    "renewal_date": today_date.strftime("%Y-%m-%d")
                }}
            )
            flash(request, f"Book renewed successfully! New due date: {datetime.strptime(new_due, '%Y-%m-%d').strftime('%B %d, %Y')}", "success")
            
    return RedirectResponse(url="/issued", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/report", response_class=HTMLResponse)
async def report_view(request: Request):
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    
    total_books = books_collection.count_documents({})
    total_titles = len(books_collection.distinct("isbn"))
    
    book_stats = list(books_collection.aggregate([{
        "$group": {
            "_id": None, 
            "total_copies": {"$sum": "$total_copies"},
            "available": {"$sum": "$available_copies"}
        }
    }]))
    
    if book_stats:
        total_copies = book_stats[0]["total_copies"]
        available = book_stats[0]["available"]
    else:
        total_copies = 0
        available = 0
        
    issued_count = issues_collection.count_documents({"status": "issued"})
    overdue_qs = list(issues_collection.find({"status": "issued", "due_date": {"$lt": today_str}}))
    overdue_count = len(overdue_qs)
    
    estimated_fines = 0
    for r in overdue_qs:
        due_date_obj = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
        estimated_fines += (today_date - due_date_obj).days * get_fine_rate()
        
    fines_res = list(issues_collection.aggregate([
        {"$match": {"status": "returned"}},
        {"$group": {"_id": None, "fines_collected": {"$sum": "$fine"}}}
    ]))
    fines_collected = fines_res[0]["fines_collected"] if fines_res else 0
    
    genre_res = list(books_collection.aggregate([{"$group": {"_id": "$genre", "count": {"$sum": 1}}}]))
    genre_counts = {g["_id"]: g["count"] for g in genre_res if g["_id"]}
    
    popular_books = [format_book(b) for b in books_collection.find().sort("issue_count", -1).limit(5)]
    max_issue_count = popular_books[0].get("issue_count") if popular_books and popular_books[0].get("issue_count", 0) > 0 else 1
    activity = get_activity_data(30)
    
    genre_distribution = []
    if total_titles > 0:
        for g, c in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True):
            genre_distribution.append({
                "genre": g,
                "count": c,
                "pct": round((c / total_titles) * 100, 1),
                "pct_int": int(round((c / total_titles) * 100))
            })
            
    data = {
        "total_books": total_books,
        "total_titles": total_titles,
        "total_copies": total_copies,
        "available": available,
        "issued_count": issued_count,
        "overdue_count": overdue_count,
        "estimated_fines": estimated_fines,
        "fines_collected": fines_collected,
        "genre_counts": json.dumps(genre_counts),
        "genre_distribution": genre_distribution,
        "popular_books": popular_books,
        "max_issue_count": max_issue_count,
        "activity": activity
    }
    
    return render_template("report.html", request, {"data": data})


@app.get("/settings", response_class=HTMLResponse)
async def settings_get(request: Request):
    config = get_config()
    return render_template("settings.html", request, {"config": config})


@app.post("/settings")
async def settings_post(
    request: Request,
    fine_per_day: str = Form(...)
):
    config = get_config()
    try:
        fine_rate = int(fine_per_day)
        if fine_rate < 0:
            flash(request, "Fine rate cannot be negative.", "error")
        else:
            set_fine_rate(fine_rate)
            config["fine_per_day"] = fine_rate
            flash(request, "Settings saved successfully.", "success")
    except (ValueError, TypeError):
        flash(request, "Invalid fine rate value.", "error")
        
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)


# ── JSON APIs ─────────────────────────────────────────────────────────────────

@app.get("/api/validate_isbn")
async def api_validate_isbn(isbn: str = Query("")):
    isbn_clean = isbn.replace("-", "").replace(" ", "")
    is_valid = isbn_clean.isdigit() and len(isbn_clean) == 13
    is_unique = not bool(books_collection.find_one({"isbn": isbn_clean}))
    return JSONResponse({"valid": is_valid, "unique": is_unique, "clean": isbn_clean})


@app.get("/api/activity")
async def api_activity(days: int = Query(7)):
    data = get_activity_data(days)
    return JSONResponse(data)


@app.get("/api/book/{book_id}")
async def api_book(book_id: str):
    book = format_book(books_collection.find_one({"_id": book_id}))
    if book:
        return JSONResponse({
            "id": str(book.get("id")),
            "title": book.get("title"),
            "author": book.get("author"),
            "genre": book.get("genre"),
            "isbn": book.get("isbn"),
            "total_copies": book.get("total_copies"),
            "available_copies": book.get("available_copies")
        })
    return JSONResponse({"error": "Not found"}, status_code=404)
