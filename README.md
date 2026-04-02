# PDF Access Management System

A secure, role-based PDF document management system built with **Flask**. It features cookie-based JWT authentication, an AI-driven application review module powered by **Google Gemini**, an admin control panel, and a modern glassmorphic UI — all packed into a single consolidated codebase.

---

## 🌟 Overview

This system allows administrators to upload and manage PDF documents. Users can browse available documents and submit applications requesting access. Each application is automatically analyzed by an AI module (Google Gemini 1.5 Flash) that returns a numerical score, a recommendation, and a one-sentence analysis summary — helping administrators make fast, informed approval or rejection decisions. Approved users can then read PDFs inline in the browser or download them.

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Flask 3.0 (Python 3.12+) |
| **Database** | SQLite with Flask-SQLAlchemy ORM |
| **Authentication** | JWT (PyJWT) stored in HttpOnly cookies |
| **Password Security** | Passlib with bcrypt |
| **AI Module** | Google Gemini 1.5 Flash (`google-genai`) with keyword fallback |
| **Frontend** | Jinja2 Templates, Vanilla JavaScript, Modern CSS (Glassmorphism) |
| **File Storage** | Secure `uploads/` directory with permission-gated access |
| **Config** | `python-dotenv` for environment variable management |

---

## 📁 Project Structure

```text
pdf_crud_Flask/
├── app.py              # Single-file application: models, services, routes & startup
├── .env                # Environment variables (SECRET_KEY, GEMINI_API_KEY)
├── requirements.txt    # Python package dependencies
├── pdf_crud.db         # SQLite database (auto-created on first run)
├── templates/
│   └── base.html       # Single Jinja2 template (all pages rendered via `page` variable)
├── static/
│   ├── style.css       # Glassmorphic UI styles & responsive layout
│   └── app.js          # Client-side logic, routing, and API calls
└── uploads/            # Secure directory for uploaded PDF files (auto-created)
```

---

## 🛠️ Setup & Installation

### 1. Clone & Navigate
```powershell
cd pdf_crud_Flask
```

### 2. Create a Virtual Environment
```powershell
python -m venv venv
```

### 3. Activate the Environment
- **PowerShell**: `.\venv\Scripts\Activate.ps1`
- **CMD**: `.\venv\Scripts\activate.bat`

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the `.env` file and set your values:

```env
# .env

# Secret key for JWT signing — change this in production!
SECRET_KEY=your-super-secret-key-here

# Google Gemini API Key (optional — falls back to keyword analysis if not set)
# Get yours at: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

> **Note:** If `GEMINI_API_KEY` is not set or is invalid, the system automatically falls back to a local keyword-based scoring engine.

---

## 🚩 Running the Application

Start the Flask development server:

```powershell
.\venv\Scripts\python.exe app.py
```

Or using the Flask CLI:

```powershell
flask --app app run --debug --port 8000
```

Then visit: **http://127.0.0.1:8000**

---

## 🔐 Default Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@admin.com` | `admin123` |

> The admin account is **automatically seeded** on first startup. Change the password after your first login.

---

## 🔄 Core Workflows

### 👑 Admin Workflow
1. **Login** — Access the system with admin credentials.
2. **Upload PDFs** — Go to the "PDFs" tab, provide a title, description, and upload a `.pdf` file.
3. **Review Requests** — Visit the "Requests" tab to see incoming user applications.
4. **AI Insights** — Each request shows an AI score (0–100), a recommendation, and a 1-sentence analysis.
5. **Decide** — Approve or reject applications. Approved users immediately gain access.
6. **Manage Users** — View all registered users and delete accounts if necessary.
7. **Manage PDFs** — Delete PDFs (automatically cascades to related permissions and applications).

### 👤 User Workflow
1. **Register** — Create a new account via the registration page.
2. **Login** — Authenticate to access the user dashboard.
3. **Browse** — See the full list of available PDFs and their access status.
4. **Apply** — Submit a written application explaining why you need access to a specific document.
5. **Track** — Monitor your application statuses in the "My Applications" section.
6. **Access** — Once approved, click **👁️ Read** to view inline or **⬇️ Download** for offline use.
7. **Settings** — Change your password at any time via the settings modal.

---

## 🧠 AI Analysis Module

The system uses **Google Gemini 1.5 Flash** as its primary analysis engine. When configured, it evaluates application text based on professional intent, clarity, and legitimacy.

**Gemini Scoring Guidelines (as prompted):**
| Score Range | Meaning | Recommendation |
|---|---|---|
| 75 – 100 | Academic/professional with clear purpose | ✅ Approve |
| 40 – 74 | Legitimate but brief or generic | 🔍 Review |
| 0 – 39 | Short, nonsensical, or suspicious | ❌ Reject |

### Fallback: Keyword Engine

If the Gemini API is unavailable or not configured, the system automatically uses a local keyword-based scoring engine:

**Weighted Keywords:** `research` (+15), `academic` (+15), `thesis` (+15), `project` (+10), `study` (+10), `assignment` (+10), `evaluation` (+10), `learn` (+5), `knowledge` (+5), `interest` (+5), `read` (+5)

**Length Bonus:** +20 pts (>50 words), +10 pts (>20 words), +5 pts (>5 words)

---

## 🌐 API Reference

All routes are served from the single `app.py` file.

### Authentication
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register` | Register a new user account | No |
| `POST` | `/auth/login` | Login and receive a session cookie | No |
| `POST` | `/auth/logout` | Clear the session cookie | No |
| `POST` | `/auth/change-password` | Change authenticated user's password | ✅ User |

### Admin API
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/admin/upload` | Upload a new PDF document | ✅ Admin |
| `GET` | `/admin/pdfs` | List all uploaded PDFs | ✅ Admin |
| `DELETE` | `/admin/pdfs/<id>` | Delete a PDF and cascade related data | ✅ Admin |
| `GET` | `/admin/applications` | List all user access applications | ✅ Admin |
| `POST` | `/admin/applications/<id>/decide` | Approve or reject an application | ✅ Admin |
| `GET` | `/admin/users` | List all registered users | ✅ Admin |
| `DELETE` | `/admin/users/<id>` | Delete a user and their data | ✅ Admin |

### User API
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/user/pdfs` | List available PDFs with access status | ✅ User |
| `POST` | `/user/apply` | Submit an access application for a PDF | ✅ User |
| `GET` | `/user/applications` | View own application history | ✅ User |
| `GET` | `/user/view/<id>` | Stream a permitted PDF inline | ✅ User |
| `GET` | `/user/download/<id>` | Download a permitted PDF | ✅ User |

---

## 🗄️ Database Models

```
User          → id, name, email, hashed_password, role, created_at
PDF           → id, title, description, file_path, uploaded_by (FK), upload_date
Application   → id, user_id (FK), pdf_id (FK), application_text,
                ai_score, ai_decision, admin_decision, status, created_at
Permission    → id, user_id (FK), pdf_id (FK), granted_at
```

---

## 🔒 Security Notes

- JWT tokens are stored in **HttpOnly cookies** (not accessible via JavaScript) with `SameSite=Lax`.
- Passwords are hashed using **bcrypt** via Passlib.
- PDF file access is **always permission-checked** server-side before streaming/download.
- Files are stored with **UUID-based names** to prevent enumeration.
- **Change the `SECRET_KEY`** in `.env` before deploying to production.

---

## 📦 Dependencies

```
flask==3.0.3
flask-sqlalchemy==3.1.1
sqlalchemy==2.0.35
python-jose[cryptography]==3.3.0
pyjwt==2.8.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
google-genai==1.69.0
python-dotenv==1.2.2
```
