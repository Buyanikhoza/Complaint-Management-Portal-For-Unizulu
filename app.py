import io
import json
import os
import uuid
import smtplib
from email.message import EmailMessage
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from openpyxl import Workbook
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_environment_file(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

    if not os.path.exists(path):
        return False

    with open(path, 'r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip().strip('"\'')
            value = value.strip().strip('"\'')
            os.environ[key] = value

    return True


if load_dotenv:
    load_dotenv()
else:
    load_environment_file()

app = Flask(__name__)
app.secret_key = 'unizulu_grievance_portal_secret_key'
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE = os.getenv('PORTAL_STATE_FILE', os.path.join(app.root_path, 'database', 'portal_state.json'))

DEFAULT_USERS_DB = {
    "student1": {"password": "123", "full_name": "Sbusiso Nkomo", "role": "student", "department": "IT Services", "email": "student1@unizulu.ac.za"},
    "staff1": {"password": "123", "full_name": "Dr. Mthembu", "role": "staff", "department": "Academic Affairs", "email": "staff1@unizulu.ac.za"},
    "admin1": {"password": "123", "full_name": "System Administrator", "role": "admin", "department": "Academic Affairs", "email": "admin1@unizulu.ac.za"}
}

DEFAULT_COMPLAINTS_DB = [
    {
        "id": 1,
        "full_name": "Sbusiso Nkomo",
        "username": "student1",
        "description": "WiFi in Residence Block B is not working.",
        "category": "ICT",
        "status": "Pending",
        "created_at": "2026-09-08",
        "reference_number": "GRV-20260908-0001",
        "is_anonymous": False,
        "evidence_path": None
    }
]

DEFAULT_DEPARTMENTS = ["Academic Affairs", "IT Services", "Finance", "Student Housing"]
DEFAULT_COMPLAINT_CATEGORIES = ["Academic", "ICT", "Facilities / Housing", "Finance", "General"]


def persist_state(users_data=None, complaints_data=None, departments_data=None, categories_data=None):
    if app.config.get('TESTING'):
        return

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if users_data is None:
        users_data = globals().get('users_db', DEFAULT_USERS_DB)
    if complaints_data is None:
        complaints_data = globals().get('complaints_db', DEFAULT_COMPLAINTS_DB)
    if departments_data is None:
        departments_data = globals().get('departments', DEFAULT_DEPARTMENTS)
    if categories_data is None:
        categories_data = globals().get('complaint_categories', DEFAULT_COMPLAINT_CATEGORIES)

    state = {
        'users_db': users_data,
        'complaints_db': complaints_data,
        'departments': departments_data,
        'complaint_categories': categories_data,
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as file:
        json.dump(state, file, indent=2)


def load_state():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        default_users = DEFAULT_USERS_DB.copy()
        default_complaints = [item.copy() for item in DEFAULT_COMPLAINTS_DB]
        default_departments = DEFAULT_DEPARTMENTS.copy()
        default_categories = DEFAULT_COMPLAINT_CATEGORIES.copy()
        persist_state(default_users, default_complaints, default_departments, default_categories)
        return default_users, default_complaints, default_departments, default_categories

    with open(DATA_FILE, 'r', encoding='utf-8') as file:
        try:
            state = json.load(file) or {}
        except json.JSONDecodeError:
            state = {}

    users = state.get('users_db') or DEFAULT_USERS_DB
    complaints = state.get('complaints_db') or DEFAULT_COMPLAINTS_DB
    departments_list = state.get('departments') or DEFAULT_DEPARTMENTS
    categories_list = state.get('complaint_categories') or DEFAULT_COMPLAINT_CATEGORIES

    return users, complaints, departments_list, categories_list


def normalize_category(category):
    if not category:
        return 'General'

    cleaned = category.strip()
    if not cleaned:
        return 'General'

    lookup = {
        'it / network': 'ICT',
        'it network': 'ICT',
        'ict': 'ICT',
        'finance / nsfas': 'Finance',
        'finance': 'Finance',
        'nsfas': 'Finance',
        'nsfas / finance': 'Finance',
    }

    return lookup.get(cleaned.lower(), cleaned)


def get_department_for_category(category):
    normalized = normalize_category(category)
    department_map = {
        'Academic': 'Academic Affairs',
        'ICT': 'IT Services',
        'Finance': 'Finance',
        'Facilities / Housing': 'Student Housing',
        'General': 'Academic Affairs',
    }
    return department_map.get(normalized, 'Academic Affairs')


def get_staff_department_filter():
    selected_department = session.get('department')
    if selected_department:
        return selected_department
    user = users_db.get(session.get('username'), {})
    return user.get('department', 'Academic Affairs')


def filter_complaints_for_staff():
    department = get_staff_department_filter()
    return [
        complaint for complaint in complaints_db
        if (complaint.get('department') or get_department_for_category(complaint.get('category'))) == department
    ]


def save_uploaded_evidence(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, unique_name))
    return f"uploads/{unique_name}"


def get_evidence_preview_url(evidence_path):
    if not evidence_path:
        return None
    return url_for('static', filename=evidence_path)


app.jinja_env.globals['get_evidence_preview_url'] = get_evidence_preview_url


def generate_reference_number():
    count = len(complaints_db) + 1
    today = datetime.now().strftime('%Y%m%d')
    return f'GRV-{today}-{count:04d}'


def build_admin_analytics():
    category_counts = {}
    status_counts = {"Pending": 0, "In-Progress": 0, "Rejected": 0, "Resolved": 0}

    for complaint in complaints_db:
        category = complaint.get('category', 'General')
        category_counts[category] = category_counts.get(category, 0) + 1

        status = complaint.get('status', 'Pending')
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts[status] = status_counts.get(status, 0) + 1

    total_complaints = len(complaints_db) or 1
    category_percentages = {
        key: round((value / total_complaints) * 100, 1)
        for key, value in category_counts.items()
    }
    status_percentages = {
        key: round((value / total_complaints) * 100, 1)
        for key, value in status_counts.items()
    }

    return {
        'total_complaints': len(complaints_db),
        'status_counts': status_counts,
        'status_percentages': status_percentages,
        'category_counts': category_counts,
        'category_percentages': category_percentages,
        'latest_report': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# Mock Databases for Testing
system_roles = ["student", "staff", "admin"]
users_db, complaints_db, departments, complaint_categories = load_state()
online_users = {}

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USERNAME = (os.getenv('EMAIL_USERNAME') or '').strip() or None
EMAIL_PASSWORD = (os.getenv('EMAIL_PASSWORD') or '').strip() or None
EMAIL_FROM = os.getenv('EMAIL_FROM', 'no-reply@gmail.com')
EMAIL_USE_TLS = str(os.getenv('EMAIL_USE_TLS', 'true')).lower() == 'true'


def get_email_status():
    missing = []
    for key, value in {
        'EMAIL_HOST': EMAIL_HOST,
        'EMAIL_PORT': EMAIL_PORT,
        'EMAIL_USERNAME': EMAIL_USERNAME,
        'EMAIL_PASSWORD': EMAIL_PASSWORD,
        'EMAIL_FROM': EMAIL_FROM,
    }.items():
        if key in {'EMAIL_PORT', 'EMAIL_FROM'}:
            continue
        if not value:
            missing.append(key)

    return {
        'configured': not missing,
        'missing': missing,
        'host': EMAIL_HOST,
        'from_address': EMAIL_FROM,
        'use_tls': EMAIL_USE_TLS,
    }


def get_user_email(username, role='student'):
    user = users_db.get(username, {})
    if user.get('email'):
        return user['email']
    if role == 'student':
        student_number = str(username).strip()
        if student_number.isdigit() and len(student_number) == 9:
            return f'{student_number}@stu.unizulu.ac.za'
        if student_number and student_number != 'None':
            return f'{student_number}@stu.unizulu.ac.za'
        return None
    return 'support@unizulu.ac.za'


def send_email_notification(subject, body, recipients):
    recipients = [email for email in recipients if email]
    if not recipients:
        print('Email notification skipped: no recipients provided.')
        return False
    if not EMAIL_HOST or not EMAIL_USERNAME or not EMAIL_PASSWORD:
        print('Email notification skipped: Outlook SMTP credentials not configured. Set EMAIL_HOST, EMAIL_USERNAME, and EMAIL_PASSWORD.')
        return False

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = EMAIL_FROM
    message['To'] = ', '.join(recipients)
    message.set_content(body)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError, ValueError) as exc:
        print(f'Email notification failed: {exc}')
        return False


def send_student_confirmation_email(complaint):
    student_email = get_user_email(complaint.get('username'), complaint.get('role', 'student'))
    if not student_email:
        return False

    subject = f'Confirmation of complaint submission: {complaint.get("reference_number")}'
    body = (
        f"Hello {complaint.get('full_name')},\n\n"
        f"Your grievance has been submitted successfully.\n"
        f"Reference Number: {complaint.get('reference_number')}\n"
        f"Category: {complaint.get('category')}\n"
        f"Status: {complaint.get('status')}\n"
        f"Description: {complaint.get('description')}\n\n"
        f"Our staff will review your complaint and provide updates as needed."
    )
    return send_email_notification(subject, body, [student_email])


def send_complaint_notification(complaint):
    student_email = get_user_email(complaint.get('username'), complaint.get('role', 'student'))
    staff_emails = [
        get_user_email(username, data.get('role', 'staff'))
        for username, data in users_db.items()
        if data.get('role') in {'staff', 'admin'}
    ]

    staff_subject = f'New grievance submitted: {complaint.get("reference_number")}'
    staff_body = (
        f"Hello,\n\nA new grievance has been submitted.\n"
        f"Reference Number: {complaint.get('reference_number')}\n"
        f"Student: {complaint.get('full_name')}\n"
        f"Category: {complaint.get('category')}\n"
        f"Status: {complaint.get('status')}\n"
        f"Description: {complaint.get('description')}\n\n"
        f"Please log in to the grievance portal to review or update it."
    )

    staff_sent = send_email_notification(staff_subject, staff_body, [email for email in staff_emails if email])
    confirmation_sent = send_student_confirmation_email(complaint)
    return staff_sent or confirmation_sent or bool(student_email)


def send_status_update_notification(complaint, old_status, new_status):
    student_email = get_user_email(complaint.get('username'))
    if not student_email:
        return False

    subject = f'Grievance status update: {complaint.get("reference_number")}'
    body = (
        f"Hello {complaint.get('full_name')},\n\n"
        f"Your grievance status has been updated.\n"
        f"Reference Number: {complaint.get('reference_number')}\n"
        f"Previous Status: {old_status}\n"
        f"New Status: {new_status}\n"
        f"Category: {complaint.get('category')}\n\n"
        f"Please log in to the grievance portal to view the latest update."
    )
    return send_email_notification(subject, body, [student_email])


@app.before_request
def track_online_users():
    username = session.get('username')
    if not username:
        return

    user_data = users_db.get(username, {})
    online_users[username] = {
        'username': username,
        'full_name': session.get('full_name') or user_data.get('full_name', username),
        'role': session.get('role') or user_data.get('role', 'student'),
        'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def get_online_users():
    active_users = []
    for username, data in online_users.items():
        if not data:
            continue
        active_users.append({
            'username': data.get('username', username),
            'full_name': data.get('full_name') or users_db.get(username, {}).get('full_name', username),
            'role': data.get('role') or users_db.get(username, {}).get('role', 'student'),
            'last_seen': data.get('last_seen', '')
        })

    return sorted(active_users, key=lambda user: (user['role'], user['full_name']))


# Landing / Welcome Page
@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/home')
def home_page():
    return render_template('home.html')


@app.route('/email_status')
def email_status():
    return jsonify(get_email_status())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        role = request.form.get('role')
        department = (request.form.get('department') or '').strip()

        if not role:
            flash('Please select a role before logging in.', 'danger')
            return render_template('login.html', departments=departments)

        if role == 'student' and (not username.isdigit() or len(username) != 9):
            flash('Student number must be exactly 9 digits.', 'danger')
            return render_template('login.html', departments=departments)

        if role == 'staff' and not department:
            flash('Please select a department before logging in as staff.', 'danger')
            return render_template('login.html', departments=departments)

        user = users_db.get(username)
        if user and user['password'] == password and user['role'] == role:
            session['username'] = username
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            if role == 'staff':
                session['department'] = department or user.get('department', 'Academic Affairs')
            else:
                session.pop('department', None)

            flash('Logged in successfully!', 'success')
            if role == 'staff':
                return redirect(url_for('staff_dashboard'))
            elif role == 'admin':
                return redirect(url_for('administrator'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username, password, or role selection.', 'danger')

    return render_template('login.html', departments=departments)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        full_name = (request.form.get('full_name') or '').strip()
        password = request.form.get('password') or ''
        role = request.form.get('role', 'student')

        if role == 'student' and (not username.isdigit() or len(username) != 9):
            flash('Student username must be exactly 9 digits.', 'danger')
            return render_template('register.html')

        if username in users_db:
            flash('Username already exists.', 'danger')
        else:
            users_db[username] = {'password': password, 'full_name': full_name, 'role': role}
            persist_state()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        if username in users_db:
            flash('A password reset link has been sent to your registered email.', 'info')
        else:
            flash('Username not found.', 'danger')
    return render_template('forgot_password.html')

@app.route('/student_dashboard')
def student_dashboard():
    if 'username' not in session or session.get('role') != 'student':
        flash('Please login as a student to access this page.', 'danger')
        return redirect(url_for('login'))

    student_complaints = [c for c in complaints_db if c['username'] == session['username']]
    latest_reference = next((c.get('reference_number') for c in reversed(student_complaints) if c.get('reference_number')), None)
    if latest_reference:
        session['last_reference_number'] = latest_reference

    return render_template('student_dashboard.html', complaints=student_complaints, latest_reference=latest_reference)


@app.route('/track_status')
def track_status():
    if 'username' not in session or session.get('role') != 'student':
        flash('Please login as a student to access this page.', 'danger')
        return redirect(url_for('login'))

    student_complaints = [c for c in complaints_db if c['username'] == session['username']]
    latest_reference = next((c.get('reference_number') for c in reversed(student_complaints) if c.get('reference_number')), None)
    if latest_reference:
        session['last_reference_number'] = latest_reference

    return render_template('track_status.html', complaints=student_complaints, latest_reference=latest_reference)


@app.route('/withdraw_grievance/<int:complaint_id>', methods=['POST'])
def withdraw_grievance(complaint_id):
    if 'username' not in session or session.get('role') != 'student':
        flash('Please login as a student to withdraw a grievance.', 'danger')
        return redirect(url_for('login'))

    complaint = next((c for c in complaints_db if c['id'] == complaint_id and c['username'] == session['username']), None)
    if complaint is None:
        flash('Grievance not found or it is not assigned to your account.', 'danger')
        return redirect(url_for('student_dashboard'))

    if complaint.get('status') in {'Resolved', 'Rejected', 'Withdrawn'}:
        flash('This grievance cannot be withdrawn because it is already resolved, rejected, or withdrawn.', 'danger')
        return redirect(url_for('student_dashboard'))

    complaint['status'] = 'Withdrawn'
    persist_state()
    flash(f'Grievance #{complaint_id} has been withdrawn successfully.', 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/submit_grievance', methods=['POST'])
def submit_grievance():
    if 'username' not in session:
        return redirect(url_for('login'))

    description = (request.form.get('description') or '').strip()
    category = normalize_category(request.form.get('category', 'General'))
    anonymous = request.form.get('anonymous') == 'on' or request.form.get('anonymous') == 'true'
    evidence_file = request.files.get('evidence')
    evidence_path = save_uploaded_evidence(evidence_file)

    if not description:
        flash('Please provide a description for your grievance.', 'danger')
        return redirect(url_for('student_dashboard'))

    if not evidence_file or not evidence_file.filename:
        flash('Grievance submission failed: evidence is required. Failure to submit supporting evidence may lead to rejection of your grievance.', 'danger')
        return redirect(url_for('student_dashboard'))

    new_id = len(complaints_db) + 1
    reference_number = generate_reference_number()
    complaint = {
        "id": new_id,
        "full_name": 'Anonymous' if anonymous else session.get('full_name'),
        "username": session.get('username'),
        "description": description,
        "category": category,
        "department": get_department_for_category(category),
        "status": "Pending",
        "created_at": datetime.now().strftime('%Y-%m-%d'),
        "reference_number": reference_number,
        "is_anonymous": anonymous,
        "evidence_path": evidence_path
    }
    complaints_db.append(complaint)
    persist_state()

    send_complaint_notification(complaint)

    session['last_reference_number'] = reference_number
    flash(f'Grievance submitted successfully! Reference number: {reference_number}', 'success')
    return redirect(url_for('student_dashboard'))

def get_complaint_by_reference(reference_number):
    if 'username' not in session:
        return None

    return next((
        complaint for complaint in complaints_db
        if complaint.get('reference_number') == reference_number and complaint.get('username') == session.get('username')
    ), None)


@app.route('/complaint_status', methods=['POST'])
def complaint_status_post():
    if 'username' not in session:
        return jsonify({'error': 'Please log in to check complaint status.'}), 401

    data = request.get_json(silent=True) or {}
    reference_number = (data.get('reference_number') or request.form.get('reference_number') or '').strip()
    if not reference_number:
        return jsonify({'error': 'A reference number is required.'}), 400

    complaint = get_complaint_by_reference(reference_number)
    if complaint is None:
        return jsonify({'error': 'No complaint found for this reference number.'}), 404

    return jsonify({
        'reference_number': complaint.get('reference_number'),
        'category': complaint.get('category'),
        'status': complaint.get('status'),
        'description': complaint.get('description'),
        'created_at': complaint.get('created_at')
    })


@app.route('/complaint_status/<reference_number>')
def complaint_status(reference_number):
    if 'username' not in session:
        return jsonify({'error': 'Please log in to check complaint status.'}), 401

    complaint = get_complaint_by_reference(reference_number)
    if complaint is None:
        return jsonify({'error': 'No complaint found for this reference number.'}), 404

    return jsonify({
        'reference_number': complaint.get('reference_number'),
        'category': complaint.get('category'),
        'status': complaint.get('status'),
        'description': complaint.get('description'),
        'created_at': complaint.get('created_at')
    })


@app.route('/staff_dashboard')
def staff_dashboard():
    if 'username' not in session or session.get('role') != 'staff':
        flash('Access restricted to staff only.', 'danger')
        return redirect(url_for('login'))

    selected_department = session.get('department') or users_db.get(session.get('username'), {}).get('department', 'Academic Affairs')
    if not selected_department:
        flash('Please select a department before viewing grievances.', 'danger')
        return redirect(url_for('login'))

    staff_complaints = filter_complaints_for_staff()
    return render_template('staff_dashboard.html', complaints=staff_complaints, selected_department=selected_department, departments=departments)

@app.route('/update_status/<int:complaint_id>', methods=['POST'])
def update_status(complaint_id):
    if 'username' not in session or session.get('role') != 'staff':
        return redirect(url_for('login'))

    new_status = request.form.get('status')
    for c in complaints_db:
        if c['id'] == complaint_id:
            previous_status = c.get('status')
            c['status'] = new_status
            persist_state()
            if previous_status != new_status:
                send_status_update_notification(c, previous_status, new_status)
            break

    flash(f'Grievance #{complaint_id} status updated to {new_status}.', 'success')
    return redirect(url_for('staff_dashboard'))

# Added to handle administrator link referenced in index.html
@app.route('/administrator')
def administrator():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Access restricted to administrators.', 'danger')
        return redirect(url_for('login'))

    users_list = [
        {
            "username": username,
            "full_name": data["full_name"],
            "role": data.get("role", "student"),
            "department": data.get("department", "General")
        }
        for username, data in users_db.items()
    ]
    analytics = build_admin_analytics()
    return render_template(
        'Administrator.html',
        users_list=users_list,
        roles=system_roles,
        departments=departments,
        complaint_categories=complaint_categories,
        analytics=analytics,
        online_users_list=get_online_users()
    )


@app.route('/administrator/add_user', methods=['POST'])
def add_user():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'student')
    department = request.form.get('department', 'Academic Affairs')

    if username and full_name:
        users_db[username] = {
            'password': request.form.get('password', '123'),
            'full_name': full_name,
            'role': role,
            'department': department
        }
        persist_state()
        flash(f'User {full_name} added successfully.', 'success')
    else:
        flash('Username and full name are required.', 'danger')

    return redirect(url_for('administrator'))


@app.route('/administrator/update_user_role/<username>', methods=['POST'])
def update_user_role(username):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if username in users_db:
        users_db[username]['role'] = request.form.get('role', users_db[username].get('role', 'student'))
        users_db[username]['department'] = request.form.get('department', users_db[username].get('department', 'Academic Affairs'))
        persist_state()
        flash(f'User {username} updated successfully.', 'success')

    return redirect(url_for('administrator'))


@app.route('/administrator/remove_user/<username>', methods=['POST'])
def remove_user(username):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    user = users_db.pop(username, None)
    if user:
        persist_state()
        flash(f'User {username} removed successfully.', 'success')
    else:
        flash(f'User {username} was not found.', 'danger')

    return redirect(url_for('administrator'))


@app.route('/administrator/add_department', methods=['POST'])
def add_department():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    department_name = request.form.get('department', '').strip()
    if department_name and department_name not in departments:
        departments.append(department_name)
        persist_state()
        flash(f'Department {department_name} added successfully.', 'success')
    else:
        flash('Department name is invalid or already exists.', 'danger')

    return redirect(url_for('administrator'))


@app.route('/administrator/add_category', methods=['POST'])
def add_category():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    category_name = request.form.get('category', '').strip()
    if category_name and category_name not in complaint_categories:
        complaint_categories.append(category_name)
        persist_state()
        flash(f'Complaint category {category_name} added successfully.', 'success')
    else:
        flash('Category name is invalid or already exists.', 'danger')

    return redirect(url_for('administrator'))


@app.route('/administrator/remove_department/<path:department>', methods=['POST'])
def remove_department(department):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    normalized = department.strip()
    if normalized in departments:
        departments.remove(normalized)
        persist_state()
        flash(f'Department {normalized} removed successfully.', 'success')
    else:
        flash(f'Department {normalized} was not found.', 'danger')

    return redirect(url_for('administrator'))


@app.route('/administrator/remove_category/<path:category>', methods=['POST'])
def remove_category(category):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    normalized = category.strip()
    if normalized in complaint_categories:
        complaint_categories.remove(normalized)
        persist_state()
        flash(f'Category {normalized} removed successfully.', 'success')
    else:
        flash(f'Category {normalized} was not found.', 'danger')

    return redirect(url_for('administrator'))


@app.route('/administrator/generate_report')
def generate_report():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    analytics = build_admin_analytics()
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = 'Summary'
    summary_sheet['A1'] = 'Grievance Report'
    summary_sheet['A1'].font = Font(size=16, bold=True, color='FFFFFF')
    summary_sheet['A1'].fill = PatternFill('solid', fgColor='003366')
    summary_sheet.merge_cells('A1:C1')
    summary_sheet['A1'].alignment = Alignment(horizontal='center')

    summary_sheet['A3'] = 'Generated At'
    summary_sheet['A3'].font = Font(bold=True)
    summary_sheet['B3'] = analytics['latest_report']
    summary_sheet['A5'] = 'Total Complaints'
    summary_sheet['A5'].font = Font(bold=True)
    summary_sheet['B5'] = analytics['total_complaints']
    summary_sheet['B5'].font = Font(bold=True)

    header_fill = PatternFill('solid', fgColor='D9EAF7')
    summary_sheet['A7'] = 'Status'
    summary_sheet['A7'].font = Font(bold=True)
    summary_sheet['A7'].fill = header_fill
    summary_sheet['B7'] = 'Count'
    summary_sheet['B7'].font = Font(bold=True)
    summary_sheet['B7'].fill = header_fill
    summary_sheet['C7'] = 'Percentage'
    summary_sheet['C7'].font = Font(bold=True)
    summary_sheet['C7'].fill = header_fill
    status_row = 8
    for status in ['Pending', 'In-Progress', 'Rejected', 'Resolved']:
        summary_sheet.cell(row=status_row, column=1, value=status)
        summary_sheet.cell(row=status_row, column=2, value=analytics['status_counts'].get(status, 0))
        summary_sheet.cell(row=status_row, column=3, value=f"{analytics['status_percentages'].get(status, 0)}%")
        status_row += 1

    light_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for cell in summary_sheet['A7:C' + str(status_row - 1)]:
        for item in cell:
            item.border = light_border

    status_chart = BarChart()
    status_chart.title = 'Status Breakdown'
    status_chart.y_axis.title = 'Count'
    status_chart.x_axis.title = 'Status'
    data = Reference(summary_sheet, min_col=2, min_row=7, max_row=11, max_col=2)
    categories = Reference(summary_sheet, min_col=1, min_row=8, max_row=11)
    status_chart.add_data(data, titles_from_data=False)
    status_chart.set_categories(categories)
    status_chart.height = 7
    status_chart.width = 13
    summary_sheet.add_chart(status_chart, 'E7')

    category_sheet = workbook.create_sheet('Category Breakdown')
    category_sheet['A1'] = 'Category'
    category_sheet['B1'] = 'Count'
    category_sheet['C1'] = 'Percentage'
    category_sheet['A1'].font = Font(bold=True)
    category_sheet['B1'].font = Font(bold=True)
    category_sheet['C1'].font = Font(bold=True)
    category_sheet['A1'].fill = header_fill
    category_sheet['B1'].fill = header_fill
    category_sheet['C1'].fill = header_fill
    category_row = 2
    for category, count in analytics['category_counts'].items():
        category_sheet.cell(row=category_row, column=1, value=category)
        category_sheet.cell(row=category_row, column=2, value=count)
        category_sheet.cell(row=category_row, column=3, value=f"{analytics['category_percentages'].get(category, 0)}%")
        category_row += 1

    for cell in category_sheet['A1:C' + str(category_row - 1)]:
        for item in cell:
            item.border = light_border

    pie_chart = PieChart()
    pie_chart.title = 'Complaint Categories'
    pie_data = Reference(category_sheet, min_col=2, min_row=1, max_row=category_row - 1, max_col=2)
    pie_categories = Reference(category_sheet, min_col=1, min_row=2, max_row=category_row - 1, max_col=1)
    pie_chart.add_data(pie_data, titles_from_data=False)
    pie_chart.set_categories(pie_categories)
    pie_chart.height = 7
    pie_chart.width = 12
    category_sheet.add_chart(pie_chart, 'E4')

    detail_sheet = workbook.create_sheet('Detailed Complaints')
    detail_headers = ['Reference Number', 'Student Username', 'Student Name', 'Category', 'Department', 'Status', 'Created At', 'Anonymous']
    for column_index, header in enumerate(detail_headers, start=1):
        cell = detail_sheet.cell(row=1, column=column_index, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill('solid', fgColor='D9EAF7')
        cell.alignment = Alignment(horizontal='center')

    for row_index, complaint in enumerate(complaints_db, start=2):
        detail_sheet.cell(row=row_index, column=1, value=complaint.get('reference_number', ''))
        detail_sheet.cell(row=row_index, column=2, value=complaint.get('username', ''))
        detail_sheet.cell(row=row_index, column=3, value=complaint.get('full_name', ''))
        detail_sheet.cell(row=row_index, column=4, value=complaint.get('category', ''))
        detail_sheet.cell(row=row_index, column=5, value=complaint.get('department', get_department_for_category(complaint.get('category'))))
        detail_sheet.cell(row=row_index, column=6, value=complaint.get('status', 'Pending'))
        detail_sheet.cell(row=row_index, column=7, value=complaint.get('created_at', ''))
        detail_sheet.cell(row=row_index, column=8, value='Yes' if complaint.get('is_anonymous') else 'No')

    for row in detail_sheet.iter_rows(min_row=1, max_row=detail_sheet.max_row, min_col=1, max_col=8):
        for cell in row:
            cell.border = light_border

    for sheet in [summary_sheet, category_sheet, detail_sheet]:
        for column_cells in sheet.columns:
            visible_cells = [cell for cell in column_cells if hasattr(cell, 'column_letter')]
            if not visible_cells:
                continue
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in visible_cells)
            sheet.column_dimensions[visible_cells[0].column_letter].width = min(max_length + 2, 26)

    summary_sheet.freeze_panes = 'A8'
    category_sheet.freeze_panes = 'A2'
    detail_sheet.freeze_panes = 'A2'

    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    response = Response(output.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers['Content-Disposition'] = 'attachment; filename=grievance_report.xlsx'
    return response


@app.route('/logout')
def logout():
    username = session.get('username')
    if username:
        online_users.pop(username, None)
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)