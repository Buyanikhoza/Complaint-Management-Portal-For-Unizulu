import pytest

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with client.session_transaction() as session:
            session['username'] = 'student1'
            session['full_name'] = 'Sbusiso Nkomo'
            session['role'] = 'student'
        yield client


def test_home_page_route_exists():
    response = app.test_client().get('/home')

    assert response.status_code == 200
    assert b'UNIZULU Portal' in response.data


def test_student_submission_shows_reference_number(client):
    response = client.post(
        '/submit_grievance',
        data={'description': 'WiFi is failing in the hostel', 'category': 'IT / Network'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Reference number' in response.data
    assert b'GRV-' in response.data


def test_student_dashboard_lists_reference_numbers(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    assert b'Reference Number' in response.data


def test_student_dashboard_bot_prompts_for_reference_and_evidence(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Please send your reference number, for example GRV-20260908-0001' in html
    assert 'Do you want to upload a supporting document? Reply with Yes or No.' in html
    assert 'Academic, ICT, Finance, NSFAS, Facilities / Housing, or General' in html


def test_student_can_check_status_by_reference_number(client):
    response = client.get('/complaint_status/GRV-20260908-0001')

    assert response.status_code == 200
    data = response.get_json()
    assert data['reference_number'] == 'GRV-20260908-0001'
    assert data['status'] == 'Pending'

    post_response = client.post('/complaint_status', json={'reference_number': 'GRV-20260908-0001'})
    assert post_response.status_code == 200
    post_data = post_response.get_json()
    assert post_data['reference_number'] == 'GRV-20260908-0001'
    assert post_data['status'] == 'Pending'


def test_admin_options_are_available_in_login_and_register():
    login_response = app.test_client().get('/login')
    register_response = app.test_client().get('/register')

    assert login_response.status_code == 200
    assert b'Administrator' in login_response.data
    assert register_response.status_code == 200
    assert b'Administrator' in register_response.data


def test_admin_login_redirects_to_administrator_dashboard():
    client = app.test_client()
    response = client.post(
        '/login',
        data={'username': 'admin1', 'password': '123', 'role': 'admin'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'System Administration Control Panel' in response.data


def test_admin_can_manage_users_departments_and_categories():
    client = app.test_client()
    with client.session_transaction() as session:
        session['username'] = 'admin1'
        session['full_name'] = 'System Administrator'
        session['role'] = 'admin'

    add_user_response = client.post(
        '/administrator/add_user',
        data={'username': 'admin_student', 'full_name': 'Ava Smith', 'role': 'student', 'department': 'IT Services'},
        follow_redirects=True,
    )
    assert add_user_response.status_code == 200
    assert b'AVA SMITH' in add_user_response.data or b'Ava Smith' in add_user_response.data

    dept_response = client.post('/administrator/add_department', data={'department': 'Psychology'}, follow_redirects=True)
    assert dept_response.status_code == 200
    assert b'Psychology' in dept_response.data

    category_response = client.post('/administrator/add_category', data={'category': 'Admissions'}, follow_redirects=True)
    assert category_response.status_code == 200
    assert b'Admissions' in category_response.data


def test_admin_report_analytics_are_visible():
    client = app.test_client()
    with client.session_transaction() as session:
        session['username'] = 'admin1'
        session['full_name'] = 'System Administrator'
        session['role'] = 'admin'

    response = client.get('/administrator')

    assert response.status_code == 200
    assert b'Complaint Analytics' in response.data
    assert b'Total Complaints' in response.data


def test_admin_can_see_who_is_online():
    from app import online_users

    online_users.clear()
    online_users['student1'] = {
        'username': 'student1',
        'full_name': 'Sbusiso Nkomo',
        'role': 'student',
        'last_seen': '2026-09-20 10:00:00',
    }

    try:
        client = app.test_client()
        with client.session_transaction() as session:
            session['username'] = 'admin1'
            session['full_name'] = 'System Administrator'
            session['role'] = 'admin'

        response = client.get('/administrator')

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Online Users' in html
        assert 'Sbusiso Nkomo' in html
        assert 'student1' in html
    finally:
        online_users.clear()


def test_submit_grievance_sends_email_notification(monkeypatch):
    sent = {}

    def fake_send(subject, body, recipients):
        sent['subject'] = subject
        sent['body'] = body
        sent['recipients'] = recipients
        return True

    monkeypatch.setattr('app.send_email_notification', fake_send)

    client = app.test_client()
    with client.session_transaction() as session:
        session['username'] = 'student1'
        session['full_name'] = 'Sbusiso Nkomo'
        session['role'] = 'student'

    response = client.post(
        '/submit_grievance',
        data={'description': 'Email notification test grievance', 'category': 'ICT'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'subject' in sent
    assert 'student1@unizulu.ac.za' in sent['recipients']
    assert any('@unizulu.ac.za' in email for email in sent['recipients'])


def test_status_update_sends_student_email_notification(monkeypatch):
    sent = {}

    def fake_send(subject, body, recipients):
        sent['subject'] = subject
        sent['body'] = body
        sent['recipients'] = recipients
        return True

    monkeypatch.setattr('app.send_email_notification', fake_send)

    client = app.test_client()
    with client.session_transaction() as session:
        session['username'] = 'staff1'
        session['full_name'] = 'Dr. Mthembu'
        session['role'] = 'staff'

    response = client.post(
        '/update_status/1',
        data={'status': 'Resolved'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'subject' in sent
    assert 'student1@unizulu.ac.za' in sent['recipients']
    assert 'Resolved' in sent['body']


def test_admin_analytics_include_rejected_status():
    from app import complaints_db

    complaints_db.append({
        'id': 999,
        'full_name': 'Rejected User',
        'username': 'student2',
        'description': 'Rejected complaint example',
        'category': 'General',
        'status': 'Rejected',
        'created_at': '2026-09-20',
        'reference_number': 'GRV-20260920-0999',
        'is_anonymous': False,
        'evidence_path': None,
    })

    try:
        client = app.test_client()
        with client.session_transaction() as session:
            session['username'] = 'admin1'
            session['full_name'] = 'System Administrator'
            session['role'] = 'admin'

        response = client.get('/administrator')

        assert response.status_code == 200
        assert b'Rejected' in response.data
    finally:
        complaints_db[:] = [item for item in complaints_db if item.get('id') != 999]


def test_staff_dashboard_hides_identity_for_anonymous_complaints():
    from app import complaints_db

    complaints_db.append({
        'id': 997,
        'full_name': 'Anonymous',
        'username': 'student_hidden',
        'description': 'Anonymous complaint for testing',
        'category': 'Academic',
        'status': 'Pending',
        'created_at': '2026-09-20',
        'reference_number': 'GRV-20260920-0997',
        'is_anonymous': True,
        'evidence_path': None,
    })

    try:
        client = app.test_client()
        with client.session_transaction() as session:
            session['username'] = 'staff1'
            session['full_name'] = 'Dr. Mthembu'
            session['role'] = 'staff'

        response = client.get('/staff_dashboard')

        assert response.status_code == 200
        assert b'Anonymous' in response.data
        assert b'Anonymous (student_hidden)' not in response.data
        assert b'student_hidden' not in response.data
    finally:
        complaints_db[:] = [item for item in complaints_db if item.get('id') != 997]


def test_staff_dashboard_shows_student_evidence_links():
    from app import complaints_db

    complaints_db.append({
        'id': 998,
        'full_name': 'Evidence Student',
        'username': 'student2',
        'description': 'Needs review with document',
        'category': 'Academic',
        'status': 'Pending',
        'created_at': '2026-09-20',
        'reference_number': 'GRV-20260920-0998',
        'is_anonymous': False,
        'evidence_path': 'uploads/sample_document.pdf',
    })

    try:
        client = app.test_client()
        with client.session_transaction() as session:
            session['username'] = 'staff1'
            session['full_name'] = 'Dr. Mthembu'
            session['role'] = 'staff'

        response = client.get('/staff_dashboard')

        assert response.status_code == 200
        assert b'View Evidence' in response.data
        assert b'/static/uploads/sample_document.pdf' in response.data
    finally:
        complaints_db[:] = [item for item in complaints_db if item.get('id') != 998]
