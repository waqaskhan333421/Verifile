# PDF Access Management System

A secure, role-based PDF document management system built with **FastAPI**. It features an integrated AI module for analyzing access requests, an admin review interface, and a modern, glassmorphic UI.

---

## 🌟 Overview

This system allows administrators to upload and manage PDF documents. Users can browse these documents and submitted applications to request access. Each application is automatically analyzed by an AI module that provides a numerical score and a recommendation, helping administrators make final approval or rejection decisions. Approved users can then view or download the secured PDFs.

---

## 🚀 Tech Stack

- **Backend**: FastAPI (Python 3.12+)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT (JSON Web Tokens) with cookie-based storage
- **Security**: Passlib with bcrypt for password hashing
- **AI Module**: Keyword-based analysis service for access requests
- **Frontend**: Jinja2 Templates, Vanilla JavaScript, Modern CSS (Glassmorphism)
- **File Storage**: Secure `uploads/` directory with permission-gated access

---

## 📁 Project Structure

```text
pdf_crud/
├── main.py              # Application entry point & DB initialization
├── config.py            # Global settings & configuration
├── database/
│   └── db.py            # SQLAlchemy engine & session management
├── models/              # SQLAlchemy Database Models
│   ├── user.py          # User & Role models
│   ├── pdf.py           # PDF metadata model
│   ├── application.py   # Access application model
│   └── permission.py    # Granted permissions model
├── schemas/             # Pydantic validation schemas
│   ├── user.py
│   ├── pdf.py
│   └── application.py
├── services/            # Core business logic
│   ├── auth.py          # JWT, Hashing, & RBAC dependencies
│   └── ai_service.py    # AI application analysis service
├── routers/             # API Endpoints (Gated by Auth)
│   ├── auth.py          # Registration, Login, Change Password
│   ├── admin.py         # PDF/User management, Request review
│   ├── user.py          # PDF browsing, Applications, Viewing/Download
│   └── pages.py         # UI Template rendering
├── templates/           # Jinja2 HTML Templates
├── static/              # CSS (style.css) & JS (app.js)
├── uploads/             # Secure directory for PDF files
├── venv/                # Python virtual environment
└── requirements.txt     # Project dependencies
```

---

## 🛠️ Setup & Installation

### 1. Create Virtual Environment
```powershell
python -m venv venv
```

### 2. Activate Environment
- **Powershell**: `.\venv\Scripts\Activate.ps1`
- **CMD**: `.\venv\Scripts\activate.bat`

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 🚩 Running the Application

Start the server using `uvicorn`:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Then visit: **http://127.0.0.1:8000**

---

## 🔐 Default Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@admin.com` | `admin123` |

*Note: The admin account is automatically created on first startup.*

---

## 🔄 Core Workflows

### 1. Admin Workflow
1.  **Login**: Access the dashboard with admin credentials.
2.  **Upload**: Upload a PDF file with a title and description.
3.  **Review**: Go to "User Requests" to see incoming applications.
4.  **AI Insights**: View the AI's numerical score and "Approve/Reject" recommendation.
5.  **Decision**: Finalize the request (Granting access automatically notifies the user system).
6.  **Manage**: Delete PDFs or manage user accounts as needed.

### 2. User Workflow
1.  **Register/Login**: Create a new account and login.
2.  **Browse**: See the list of available PDFs.
3.  **Apply**: Submit an application explaining why access is needed.
4.  **Track**: Monitor the application status in "My Applications".
5.  **Access**: Once approved, click **👁️ Read** to view inline or **⬇️ Download** for offline use.
6.  **Settings**: Change your password at any time via the settings modal.

---

## 🧠 AI Analysis Module

The system uses a custom scoring engine (`services/ai_service.py`) that evaluates application text based on:
- **Professional Keywords**: Weighting for academic/research terminology.
- **Intent Analysis**: Identifying the purpose of the request.
- **Length & Detail**: Rewarding comprehensive explanations.

**Scores:**
- **70+**: High confidence (AI suggests Approval)
- **40-69**: Medium confidence (AI suggests Manual Review)
- **<40**: Low confidence (AI suggests Rejection)
