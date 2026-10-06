import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///helpdesk.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tickets = db.relationship("Ticket", backref="requester", lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    tickets = db.relationship("Ticket", backref="category", lazy=True)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="medium")
    status = db.Column(db.String(30), nullable=False, default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_at = db.Column(db.DateTime, nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    comments = db.relationship("Comment", backref="ticket", lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False)
    user = db.relationship("User")

def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def sla_hours(priority):
    return {"low": 72, "medium": 48, "high": 24, "critical": 8}.get(priority, 48)

@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            flash(f"Bem-vindo(a), {user.name}!", "success")
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    base = Ticket.query if user.role in ("admin", "agent") else Ticket.query.filter_by(requester_id=user.id)
    stats = {
        "total": base.count(),
        "open": base.filter(Ticket.status == "open").count(),
        "progress": base.filter(Ticket.status == "in_progress").count(),
        "resolved": base.filter(Ticket.status == "resolved").count(),
        "critical": base.filter(Ticket.priority == "critical").count(),
    }
    recent = base.order_by(Ticket.updated_at.desc()).limit(6).all()
    return render_template("dashboard.html", stats=stats, recent=recent)

@app.route("/tickets")
@login_required
def tickets():
    user = current_user()
    query = Ticket.query if user.role in ("admin", "agent") else Ticket.query.filter_by(requester_id=user.id)
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    priority = request.args.get("priority", "")
    if q:
        query = query.filter((Ticket.title.ilike(f"%{q}%")) | (Ticket.description.ilike(f"%{q}%")))
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    items = query.order_by(Ticket.updated_at.desc()).all()
    return render_template("tickets.html", tickets=items, q=q, status=status, priority=priority)

@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def new_ticket():
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        category_id = request.form.get("category_id", type=int)
        if len(title) < 5 or len(description) < 10 or not category_id:
            flash("Preencha todos os campos corretamente.", "danger")
            return render_template("ticket_form.html", categories=categories, ticket=None)
        if priority not in ("low", "medium", "high", "critical"):
            priority = "medium"
        now = datetime.utcnow()
        ticket = Ticket(title=title, description=description, priority=priority,
                        category_id=category_id, requester_id=current_user().id,
                        due_at=now + timedelta(hours=sla_hours(priority)))
        db.session.add(ticket)
        db.session.commit()
        flash("Chamado criado com sucesso.", "success")
        return redirect(url_for("ticket_detail", ticket_id=ticket.id))
    return render_template("ticket_form.html", categories=categories, ticket=None)

@app.route("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = db.session.get(Ticket, ticket_id) or abort(404)
    user = current_user()
    if user.role not in ("admin", "agent") and ticket.requester_id != user.id:
        abort(403)
    return render_template("ticket_detail.html", ticket=ticket)

@app.route("/tickets/<int:ticket_id>/status", methods=["POST"])
@roles_required("admin", "agent")
def update_status(ticket_id):
    ticket = db.session.get(Ticket, ticket_id) or abort(404)
    status = request.form.get("status")
    if status not in ("open", "in_progress", "resolved", "closed"):
        abort(400)
    ticket.status = status
    db.session.commit()
    flash("Status atualizado.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket.id))

@app.route("/tickets/<int:ticket_id>/comment", methods=["POST"])
@login_required
def add_comment(ticket_id):
    ticket = db.session.get(Ticket, ticket_id) or abort(404)
    user = current_user()
    if user.role not in ("admin", "agent") and ticket.requester_id != user.id:
        abort(403)
    content = request.form.get("content", "").strip()
    if not content:
        flash("O comentário não pode estar vazio.", "danger")
    else:
        db.session.add(Comment(content=content, user_id=user.id, ticket_id=ticket.id))
        db.session.commit()
        flash("Comentário adicionado.", "success")
    return redirect(url_for("ticket_detail", ticket_id=ticket.id))

@app.route("/tickets/<int:ticket_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id) or abort(404)
    db.session.delete(ticket)
    db.session.commit()
    flash("Chamado excluído.", "success")
    return redirect(url_for("tickets"))

@app.route("/users")
@roles_required("admin")
def users():
    return render_template("users.html", users=User.query.order_by(User.name).all())

@app.route("/users/new", methods=["GET", "POST"])
@roles_required("admin")
def new_user():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        if len(name) < 3 or "@" not in email or len(password) < 6 or role not in ("admin", "agent", "user"):
            flash("Dados inválidos. A senha deve ter pelo menos 6 caracteres.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "danger")
        else:
            db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), role=role))
            db.session.commit()
            flash("Usuário criado.", "success")
            return redirect(url_for("users"))
    return render_template("user_form.html")

def seed():
    db.create_all()
    if User.query.count() == 0:
        db.session.add_all([
            User(name="Administrador", email="admin@helpdesk.local", password_hash=generate_password_hash("Admin123!"), role="admin"),
            User(name="Agente de Suporte", email="agente@helpdesk.local", password_hash=generate_password_hash("Agente123!"), role="agent"),
            User(name="Usuário Demo", email="usuario@helpdesk.local", password_hash=generate_password_hash("Usuario123!"), role="user"),
        ])
    if Category.query.count() == 0:
        db.session.add_all([Category(name=x) for x in ["Hardware", "Software", "Acesso", "Rede", "Outro"]])
    db.session.commit()

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

with app.app_context():
    seed()

if __name__ == "__main__":
    app.run(debug=True)
