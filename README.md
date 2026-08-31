# 📚 LIBRA — Premium Library Management System

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live-success?style=for-the-badge)

**LIBRA** is a modern, high-performance, and beautifully crafted Library Management System built with **FastAPI**, **MongoDB Atlas**, **Jinja2**, and **Vanilla CSS/JS**. Designed for both speed and aesthetics, LIBRA delivers sub-second response times on serverless environments like **Vercel**.

🌐 **Live Demo:** [https://library-managements-ashy.vercel.app](https://library-managements-ashy.vercel.app)

---

## ✨ Features

- 📊 **Executive Dashboard**: Real-time stats for total books, active members, active issues, fines collected, and interactive visual charts powered by Chart.js.
- 📖 **Book Management**:
  - Add, edit, delete books with automated ISBN-13 validation and uniqueness checks.
  - Multi-criteria filtering (by genre, availability status, search query) and custom sorting.
  - Dynamic, color-coded 3D book cover visual cards.
- 📤 **Issue & Return Flow**:
  - Multi-step interactive wizard for issuing books to members.
  - Due date tracking and automatic daily fine calculation for overdue items.
  - Streamlined one-click return processing with fine settlement.
- 👤 **Member Profiles & History**:
  - Detailed member activity timeline, historical checkouts, active borrowings, and fines.
- ⚡ **High-Performance Architecture**:
  - Sub-second page loads using `concurrent.futures.ThreadPoolExecutor` for parallel database execution and in-memory aggregation.
  - Fully responsive, glassmorphism-inspired UI with smooth transitions and toast notifications.

---

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.9+)
- **Database:** [MongoDB Atlas](https://www.mongodb.com/atlas) via `pymongo` & `dnspython`
- **Frontend / Templating:** Jinja2 HTML Templates, Vanilla CSS, Modern JavaScript
- **Visuals / Charts:** [Chart.js](https://www.chartjs.org/)
- **Deployment:** [Vercel Serverless](https://vercel.com/) (`@vercel/python`)

---

## 🚀 Getting Started Locally

### 1. Prerequisites
- Python 3.9+ installed
- MongoDB connection URI (e.g. MongoDB Atlas cluster)

### 2. Clone the Repository
```bash
git clone https://github.com/Omyadav19/library-management.git
cd library-management
```

### 3. Create a Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=Cluster1
SECRET_KEY=your-super-secret-key-fastapi-2026
```

### 5. Run the Server
```bash
uvicorn main:app --reload --port 8000
```
Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## 📁 Project Structure

```text
library_management/
├── library/
│   └── db.py              # MongoDB Atlas connection & database helpers
├── static/
│   ├── css/
│   │   └── style.css      # Custom design tokens, glassmorphism & responsive layout
│   └── js/
│       └── app.js         # Interactive charts, wizard step logic, toasts & previews
├── templates/             # Jinja2 HTML views
│   ├── base.html          # Global navigation, sidebar & layout structure
│   ├── dashboard.html     # Analytics dashboard, metrics & quick actions
│   ├── books.html         # Catalog management & filter controls
│   ├── add_book.html      # Add book form with real-time card preview
│   ├── issue_book.html    # Step-by-step issue workflow
│   ├── return_book.html   # Return processing & fine calculation
│   ├── issued.html        # Active borrowed books list
│   ├── overdue.html       # Overdue book tracking & settlement
│   ├── member_history.html# Member history lookup
│   ├── report.html        # Analytics reports
│   ├── search.html        # Universal search
│   └── settings.html      # System configuration (fine rate per day)
├── main.py                # FastAPI routes & optimized data aggregation engine
├── requirements.txt       # Python dependencies
├── vercel.json            # Vercel serverless build & routing configuration
└── README.md
```

---

## 🚢 Deployment to Vercel

1. Push your code to GitHub.
2. Import the repository in [Vercel](https://vercel.com).
3. In **Project Settings → Environment Variables**, configure:
   - `MONGO_URI`
   - `SECRET_KEY`
4. Make sure MongoDB Atlas Network Access allows connections (`0.0.0.0/0` for serverless environments).
5. Deploy!

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
