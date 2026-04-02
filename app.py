import os
import uuid
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from functools import wraps
from flask import Flask, request, jsonify, make_response, redirect, send_file, render_template
from flask_sqlalchemy import SQLAlchemy
import jwt
from passlib.context import CryptContext
from google import genai
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'pdf_crud.db')}"
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# App Setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

db = SQLAlchemy(app)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configure Gemini Client
client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        pass

# ==================== Models ====================

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False) # "admin" or "user"
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

class PDF(db.Model):
    __tablename__ = "pdfs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    upload_date = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

class Application(db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey("pdfs.id"), nullable=False)
    application_text = db.Column(db.Text, nullable=False)
    ai_score = db.Column(db.Float, nullable=True)
    ai_decision = db.Column(db.String(50), nullable=True)
    admin_decision = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default="pending", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey("pdfs.id"), nullable=False)
    granted_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())


# ==================== Services ====================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

def analyze_application(application_text: str):
    if not client:
        return _fallback_keyword_analysis(application_text)

    prompt = f"""
    You are an AI assistant for a secure document management system. 
    Analyze the following user application for access to a PDF document.
    Provide a score from 0 to 100 based on the professional intent, clarity, and legitimacy.
    Also provide a short 1-sentence analysis.
    
    Application Text: "{application_text}"
    
    Respond STRICTLY in the following JSON format:
    {{
        "score": (integer 0-100),
        "recommendation": ("approve", "reject", "review"),
        "analysis": "1-sentence summary"
    }}
    
    Guidelines:
    - 75-100: Academic/professional purpose with detail.
    - 40-74: Legitimate but brief or generic.
    - 0-39: Short, nonsensical, or suspicious.
    """
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        content = response.text.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        result = json.loads(content)
        return {
            "score": int(result.get("score", 0)),
            "recommendation": result.get("recommendation", "review").lower(),
            "analysis": result.get("analysis", "No analysis provided.")
        }
    except Exception as e:
        app.logger.error(f"GenAI analysis failed: {e}")
        return _fallback_keyword_analysis(application_text)

def _fallback_keyword_analysis(text: str):
    text_lower = text.lower()
    score = 0
    words = text.split()
    keywords = {
        "research": 15, "academic": 15, "thesis": 15, "project": 10, "study": 10,
        "assignment": 10, "evaluation": 10, "learn": 5, "knowledge": 5, "interest": 5, "read": 5,
    }
    for word, points in keywords.items():
        if word in text_lower: score += points
    if len(words) > 50: score += 20
    elif len(words) > 20: score += 10
    elif len(words) > 5: score += 5
    score = min(score, 100)
    
    if score >= 70: recommendation = "approve"
    elif score >= 40: recommendation = "review"
    else: recommendation = "reject"
        
    return {
        "score": score,
        "recommendation": recommendation,
        "analysis": "Analyzed using local keyword engine (Gemini API key not configured or failed)."
    }

# ==================== Auth Decorators ====================

def get_current_user_from_request():
    token = request.cookies.get("access_token")
    if not token:
        return None
    if token.startswith("Bearer "):
        token = token[7:]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    user = db.session.get(User, int(payload["sub"]))
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user_from_request()
        if not user:
            if request.headers.get("Accept") == "application/json" or request.is_json:
                return jsonify({"detail": "Not authenticated"}), 401
            return redirect("/login")
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user_from_request()
        if not user:
            if request.headers.get("Accept") == "application/json" or request.is_json:
                return jsonify({"detail": "Not authenticated"}), 401
            return redirect("/login")
        if user.role != "admin":
            if request.headers.get("Accept") == "application/json" or request.is_json:
                return jsonify({"detail": "Admin access required"}), 403
            return redirect("/")
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


# ==================== Page Routes ====================

@app.route("/")
def root():
    user = get_current_user_from_request()
    if user:
        if user.role == "admin":
            return redirect("/admin-dashboard")
        return redirect("/user-dashboard")
    return redirect("/login")

@app.route("/login")
def login_page():
    return render_template("base.html", page="login")

@app.route("/register")
def register_page():
    return render_template("base.html", page="register")

@app.route("/admin-dashboard")
@admin_required
def admin_dashboard_page():
    return render_template("base.html", page="admin_dashboard")

@app.route("/admin-requests")
@admin_required
def admin_requests_page():
    return render_template("base.html", page="admin_requests")

@app.route("/admin-users")
@admin_required
def admin_users_page():
    return render_template("base.html", page="admin_users")

@app.route("/admin-pdfs")
@admin_required
def admin_pdfs_page():
    return render_template("base.html", page="admin_pdfs")

@app.route("/user-dashboard")
@login_required
def user_dashboard_page():
    return render_template("base.html", page="user_dashboard")


# ==================== API Routes: Auth ====================

@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    existing = User.query.filter_by(email=data.get("email")).first()
    if existing:
        return jsonify({"detail": "Email already registered"}), 400

    new_user = User(
        name=data.get("name"),
        email=data.get("email"),
        hashed_password=hash_password(data.get("password")),
        role="user",
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful", "user_id": new_user.id})

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not verify_password(data.get("password"), user.hashed_password):
        return jsonify({"detail": "Invalid email or password"}), 401

    token = create_access_token({"sub": str(user.id), "role": user.role})
    resp = make_response(jsonify({
        "message": "Login successful",
        "role": user.role,
        "user_id": user.id,
        "name": user.name,
    }))
    resp.set_cookie(
        "access_token",
        f"Bearer {token}",
        httponly=True,
        max_age=60 * 60 * 24, # 24 hours
        samesite="Lax"
    )
    return resp

@app.route("/auth/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"message": "Logged out successfully"}))
    resp.delete_cookie("access_token")
    return resp

@app.route("/auth/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.json
    user = request.current_user
    if not verify_password(data.get("old_password"), user.hashed_password):
        return jsonify({"detail": "Incorrect old password"}), 400
    user.hashed_password = hash_password(data.get("new_password"))
    db.session.commit()
    return jsonify({"message": "Password updated successfully"})

# ==================== API Routes: Admin ====================

@app.route("/admin/upload", methods=["POST"])
@admin_required
def admin_upload_pdf():
    title = request.form.get("title")
    description = request.form.get("description", "")
    file = request.files.get("file")
    
    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"detail": "Only PDF files are allowed"}), 400

    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    file.save(file_path)

    new_pdf = PDF(
        title=title,
        description=description,
        file_path=unique_name,
        uploaded_by=request.current_user.id
    )
    db.session.add(new_pdf)
    db.session.commit()
    return jsonify({"message": "PDF uploaded successfully", "pdf_id": new_pdf.id})

@app.route("/admin/pdfs", methods=["GET"])
@admin_required
def list_pdfs():
    pdfs = PDF.query.order_by(PDF.upload_date.desc()).all()
    result = []
    for p in pdfs:
        result.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "upload_date": str(p.upload_date) if p.upload_date else None,
            "uploaded_by": p.uploaded_by,
        })
    return jsonify(result)

@app.route("/admin/pdfs/<int:pdf_id>", methods=["DELETE"])
@admin_required
def delete_pdf(pdf_id):
    pdf = db.session.get(PDF, pdf_id)
    if not pdf:
        return jsonify({"detail": "PDF not found"}), 404

    file_path = os.path.join(UPLOAD_DIR, pdf.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    Permission.query.filter_by(pdf_id=pdf_id).delete()
    Application.query.filter_by(pdf_id=pdf_id).delete()
    db.session.delete(pdf)
    db.session.commit()
    return jsonify({"message": "PDF deleted successfully"})

@app.route("/admin/applications", methods=["GET"])
@admin_required
def list_applications():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    result = []
    for app in apps:
        user = db.session.get(User, app.user_id)
        pdf = db.session.get(PDF, app.pdf_id)
        result.append({
            "id": app.id,
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "Unknown",
            "pdf_title": pdf.title if pdf else "Deleted",
            "pdf_id": app.pdf_id,
            "application_text": app.application_text,
            "ai_score": app.ai_score,
            "ai_decision": app.ai_decision,
            "admin_decision": app.admin_decision,
            "status": app.status,
            "created_at": str(app.created_at) if app.created_at else None,
        })
    return jsonify(result)

@app.route("/admin/applications/<int:app_id>/decide", methods=["POST"])
@admin_required
def decide_application(app_id):
    decision = request.args.get("decision")
    if decision not in ("approve", "reject"):
        return jsonify({"detail": "Decision must be 'approve' or 'reject'"}), 400

    app_obj = db.session.get(Application, app_id)
    if not app_obj:
        return jsonify({"detail": "Application not found"}), 404

    app_obj.admin_decision = decision
    app_obj.status = "approved" if decision == "approve" else "rejected"

    if decision == "approve":
        existing_perm = Permission.query.filter_by(user_id=app_obj.user_id, pdf_id=app_obj.pdf_id).first()
        if not existing_perm:
            perm = Permission(user_id=app_obj.user_id, pdf_id=app_obj.pdf_id)
            db.session.add(perm)

    db.session.commit()
    return jsonify({"message": f"Application {decision}d successfully"})

@app.route("/admin/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "created_at": str(u.created_at) if u.created_at else None,
        })
    return jsonify(result)

@app.route("/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    if user_id == request.current_user.id:
        return jsonify({"detail": "Cannot delete your own account"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"detail": "User not found"}), 404

    Permission.query.filter_by(user_id=user_id).delete()
    Application.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"})

# ==================== API Routes: User ====================

@app.route("/user/pdfs", methods=["GET"])
@login_required
def list_available_pdfs():
    user = request.current_user
    pdfs = PDF.query.order_by(PDF.upload_date.desc()).all()
    result = []
    for p in pdfs:
        perm = Permission.query.filter_by(user_id=user.id, pdf_id=p.id).first()
        app_obj = Application.query.filter_by(user_id=user.id, pdf_id=p.id).order_by(Application.created_at.desc()).first()
        result.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "upload_date": str(p.upload_date) if p.upload_date else None,
            "has_access": perm is not None,
            "application_status": app_obj.status if app_obj else None,
        })
    return jsonify(result)

@app.route("/user/apply", methods=["POST"])
@login_required
def submit_application():
    data = request.json
    pdf_id = data.get("pdf_id")
    app_text = data.get("application_text")
    user = request.current_user

    pdf = db.session.get(PDF, pdf_id)
    if not pdf:
        return jsonify({"detail": "PDF not found"}), 404

    if Permission.query.filter_by(user_id=user.id, pdf_id=pdf_id).first():
        return jsonify({"detail": "You already have access to this PDF"}), 400

    if Application.query.filter_by(user_id=user.id, pdf_id=pdf_id, status="pending").first():
        return jsonify({"detail": "You already have a pending application for this PDF"}), 400

    ai_result = analyze_application(app_text)
    new_app = Application(
        user_id=user.id,
        pdf_id=pdf_id,
        application_text=app_text,
        ai_score=ai_result["score"],
        ai_decision=ai_result["recommendation"],
    )
    db.session.add(new_app)
    db.session.commit()

    return jsonify({
        "message": "Application submitted successfully",
        "application_id": new_app.id,
        "ai_score": ai_result["score"],
        "ai_recommendation": ai_result["recommendation"],
        "ai_analysis": ai_result["analysis"],
    })

@app.route("/user/applications", methods=["GET"])
@login_required
def my_applications():
    user = request.current_user
    apps = Application.query.filter_by(user_id=user.id).order_by(Application.created_at.desc()).all()
    result = []
    for app_obj in apps:
        pdf = db.session.get(PDF, app_obj.pdf_id)
        result.append({
            "id": app_obj.id,
            "pdf_title": pdf.title if pdf else "Deleted",
            "pdf_id": app_obj.pdf_id,
            "application_text": app_obj.application_text,
            "ai_score": app_obj.ai_score,
            "ai_decision": app_obj.ai_decision,
            "status": app_obj.status,
            "admin_decision": app_obj.admin_decision,
            "created_at": str(app_obj.created_at) if app_obj.created_at else None,
        })
    return jsonify(result)

@app.route("/user/download/<int:pdf_id>", methods=["GET"])
@login_required
def download_pdf(pdf_id):
    user = request.current_user
    if not Permission.query.filter_by(user_id=user.id, pdf_id=pdf_id).first():
        return jsonify({"detail": "Access denied. You do not have permission to download this PDF."}), 403

    pdf = db.session.get(PDF, pdf_id)
    if not pdf:
        return jsonify({"detail": "PDF not found"}), 404

    file_path = os.path.join(UPLOAD_DIR, pdf.file_path)
    if not os.path.exists(file_path):
        return jsonify({"detail": "File not found on server"}), 404

    return send_file(file_path, as_attachment=True, download_name=f"{pdf.title}.pdf", mimetype="application/pdf")

@app.route("/user/view/<int:pdf_id>", methods=["GET"])
@login_required
def view_pdf(pdf_id):
    user = request.current_user
    if not Permission.query.filter_by(user_id=user.id, pdf_id=pdf_id).first():
        return jsonify({"detail": "Access denied."}), 403

    pdf = db.session.get(PDF, pdf_id)
    if not pdf:
        return jsonify({"detail": "PDF not found"}), 404

    file_path = os.path.join(UPLOAD_DIR, pdf.file_path)
    if not os.path.exists(file_path):
        return jsonify({"detail": "File not found on server"}), 404

    return send_file(file_path, mimetype="application/pdf", as_attachment=False)


# ==================== Main / Startup ====================

with app.app_context():
    db.create_all()
    # Seed default admin
    existing_admin = User.query.filter_by(email="admin@admin.com").first()
    if not existing_admin:
        admin_user = User(
            name="Admin",
            email="admin@admin.com",
            hashed_password=hash_password("admin123"),
            role="admin"
        )
        db.session.add(admin_user)
        db.session.commit()
        print("[OK] Default admin account created: admin@admin.com / admin123")

if __name__ == "__main__":
    app.run(debug=True, port=8000)
