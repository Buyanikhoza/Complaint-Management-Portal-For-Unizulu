import io

import pytest

from app import app


def test_load_environment_file_reads_dotenv_without_python_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text('EMAIL_USERNAME=test@gmail.com\nEMAIL_PASSWORD=secret\nEMAIL_FROM=sender@gmail.com\n', encoding='utf-8')

    monkeypatch.chdir(tmp_path)

    import app as app_module

    app_module.load_environment_file(str(env_file))

    assert app_module.os.environ.get('EMAIL_USERNAME') == 'test@gmail.com'
    assert app_module.os.environ.get('EMAIL_PASSWORD') == 'secret'
    assert app_module.os.environ.get('EMAIL_FROM') == 'sender@gmail.com'


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
        data={
            'description': 'WiFi is failing in the hostel',
            'category': 'IT / Network',
            'evidence': (io.BytesIO(b'fake evidence'), 'evidence.pdf'),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Reference number' in response.data
    assert b'GRV-' in response.data


def test_student_can_withdraw_pending_grievance(client):
    from app import complaints_db

    complaints_db.append({
        'id': 9997,
        'full_name': 'Sbusiso Nkomo',
        'username': 'student1',
        'description': 'Withdraw me',
        'category': 'ICT',
        'status': 'Pending',
        'created_at': '2026-09-23',
        'reference_number': 'GRV-20260923-9997',
        'is_anonymous': False,
        'evidence_path': None,
    })
    import app as app_module
    app_module.persist_state()

    try:
        response = client.post('/withdraw_grievance/9997', follow_redirects=True)

        assert response.status_code == 200
        assert b'withdrawn' in response.data.lower()
        assert b'GRV-20260923-9997' in response.data
        complaint = next(item for item in complaints_db if item['id'] == 9997)
        assert complaint['status'] == 'Withdrawn'
    finally:
        complaints_db[:] = [item for item in complaints_db if item.get('id') != 9997]
        app_module.persist_state()


def test_student_dashboard_lists_reference_numbers(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    assert b'Reference Number' in response.data


def test_student_submission_requires_evidence_and_shows_rejection_warning(client):
    response = client.post(
        '/submit_grievance',
        data={'description': 'WiFi is failing in the hostel', 'category': 'ICT'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'evidence' in response.data.lower()
    assert b'rejection' in response.data.lower()
    assert b'Grievance submission failed' in response.data


def test_student_dashboard_bot_prompts_for_reference_and_evidence(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Please send your reference number, for example GRV-20260908-0001' in html
    assert 'Do you want to upload a supporting document? Reply with Yes or No.' in html
    assert 'Academic, ICT, Finance, Facilities / Housing, or General' in html


def test_student_dashboard_has_track_status_button_and_pane(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Track Status' in html
    assert '/track_status' in html

    status_page = client.get('/track_status')
    assert status_page.status_code == 200
    status_html = status_page.get_data(as_text=True)
    assert 'Check Status' in status_html
    assert 'Back to Dashboard' in status_html


def test_student_dashboard_chatbot_asks_about_anonymous_submission(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Do you want to submit this complaint anonymously? Reply with Yes or No.' in html


def test_student_dashboard_ai_assistant_is_anchored_away_from_withdraw_buttons(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'left: 20px;' in html
    assert 'left: 24px;' in html


def test_student_track_status_button_navigates_to_separate_page(client):
    response = client.get('/student_dashboard')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '/track_status' in html

    status_page = client.get('/track_status')
    assert status_page.status_code == 200
    status_html = status_page.get_data(as_text=True)
    assert b'Track Status' in status_page.data
    assert 'Enter complaint reference number' in status_html
    assert 'placeholder="Enter complaint reference number"' in status_html


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


def test_login_requires_role_selection_and_student_dashboard_has_blank_default_category():
    login_response = app.test_client().get('/login')
    client = app.test_client()
    with client.session_transaction() as session:
        session['username'] = 'student1'
        session['full_name'] = 'Sbusiso Nkomo'
        session['role'] = 'student'
    student_dashboard_response = client.get('/student_dashboard')

    assert login_response.status_code == 200
    login_html = login_response.get_data(as_text=True)
    assert 'Select Role' in login_html
    assert 'Student' in login_html
    assert b'NSFAS' not in login_html.encode('utf-8')

    assert student_dashboard_response.status_code == 200
    dashboard_html = student_dashboard_response.get_data(as_text=True)
    assert 'Select Category' in dashboard_html
    assert 'Academic' in dashboard_html
    assert 'NSFAS' not in dashboard_html


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


def test_staff_login_requires_department_and_filters_complaints():
    client = app.test_client()
    complaints_db = __import__('app').complaints_db
    complaints_db[:] = [
        {
            'id': 9998,
            'full_name': 'Academic Student',
            'username': 'student99',
            'description': 'Academic issue for staff view',
            'category': 'Academic',
            'status': 'Pending',
            'created_at': '2026-09-10',
            'reference_number': 'GRV-20260910-9998',
            'is_anonymous': False,
            'evidence_path': None,
            'department': 'Academic Affairs',
        },
        {
            'id': 9999,
            'full_name': 'IT Student',
            'username': 'student98',
            'description': 'IT issue not for academic staff',
            'category': 'ICT',
            'status': 'Pending',
            'created_at': '2026-09-10',
            'reference_number': 'GRV-20260910-9999',
            'is_anonymous': False,
            'evidence_path': None,
            'department': 'IT Services',
        },
    ]

    try:
        response = client.post(
            '/login',
            data={'username': 'staff1', 'password': '123', 'role': 'staff', 'department': 'Academic Affairs'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Academic issue for staff view' in html
        assert 'IT issue not for academic staff' not in html
    finally:
        complaints_db[:] = [entry for entry in complaints_db if entry.get('id') not in {9998, 9999}]


def test_staff_dashboard_shows_housing_and_general_complaints_for_relevant_departments():
    from app import complaints_db

    complaints_db.extend([
        {
            'id': 9981,
            'full_name': 'Housing Student',
            'username': 'housing_student',
            'description': 'Housing complaint for student housing staff',
            'category': 'Housing',
            'status': 'Pending',
            'created_at': '2026-09-23',
            'reference_number': 'GRV-20260923-9981',
            'is_anonymous': False,
            'evidence_path': None,
        },
        {
            'id': 9982,
            'full_name': 'General Student',
            'username': 'general_student',
            'description': 'General complaint for all staff',
            'category': 'General',
            'status': 'Pending',
            'created_at': '2026-09-23',
            'reference_number': 'GRV-20260923-9982',
            'is_anonymous': False,
            'evidence_path': None,
        },
    ])

    try:
        client = app.test_client()
        with client.session_transaction() as session:
            session['username'] = 'staff1'
            session['full_name'] = 'Dr. Mthembu'
            session['role'] = 'staff'
            session['department'] = 'Student Housing'

        housing_response = client.get('/staff_dashboard')
        housing_html = housing_response.get_data(as_text=True)
        assert 'Housing complaint for student housing staff' in housing_html
        assert 'General complaint for all staff' in housing_html

        with client.session_transaction() as session:
            session['department'] = 'Academic Affairs'

        academic_response = client.get('/staff_dashboard')
        academic_html = academic_response.get_data(as_text=True)
        assert 'General complaint for all staff' in academic_html
    finally:
        complaints_db[:] = [entry for entry in complaints_db if entry.get('id') not in {9981, 9982}]


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

    remove_user_response = client.post('/administrator/remove_user/admin_student', follow_redirects=True)
    assert remove_user_response.status_code == 200
    assert b'removed' in remove_user_response.data.lower()

    remove_department_response = client.post('/administrator/remove_department/Psychology', follow_redirects=True)
    assert remove_department_response.status_code == 200
    assert b'removed' in remove_department_response.data.lower()

    remove_category_response = client.post('/administrator/remove_category/Admissions', follow_redirects=True)
    assert remove_category_response.status_code == 200
    assert b'removed' in remove_category_response.data.lower()


def test_admin_generate_report_downloads_excel_workbook_with_charts_and_tables():
    client = app.test_client()
    complaints_db = __import__('app').complaints_db
    complaints_db.insert(0, {
        'id': 2026,
        'full_name': 'Sample Student',
        'username': 'student99',
        'description': 'Sample complaint for report generation',
        'category': 'ICT',
        'department': 'IT Services',
        'status': 'Pending',
        'created_at': '2026-09-23',
        'reference_number': 'GRV-20260923-0001',
        'is_anonymous': False,
        'evidence_path': None,
    })

    try:
        with client.session_transaction() as session:
            session['username'] = 'admin1'
            session['full_name'] = 'System Administrator'
            session['role'] = 'admin'

        response = client.get('/administrator/generate_report')

        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        assert 'attachment; filename=' in response.headers.get('Content-Disposition', '')

        workbook = __import__('openpyxl').load_workbook(filename=__import__('io').BytesIO(response.data), read_only=True)
        assert 'Summary' in workbook.sheetnames
        assert 'Category Breakdown' in workbook.sheetnames
        assert 'Detailed Complaints' in workbook.sheetnames
        assert workbook['Summary']['A1'].value == 'Grievance Report'
        assert workbook['Summary']['A7'].value == 'Status'
        assert workbook['Detailed Complaints']['A1'].value == 'Reference Number'
        assert workbook['Detailed Complaints']['A2'].value == 'GRV-20260923-0001'
    finally:
        complaints_db[:] = [entry for entry in complaints_db if entry.get('id') != 2026]


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


def test_state_persists_across_reload(monkeypatch, tmp_path):
    import json
    import importlib
    import app as app_module

    monkeypatch.setenv('PORTAL_STATE_FILE', str(tmp_path / 'portal_state.json'))
    app_module.DATA_FILE = str(tmp_path / 'portal_state.json')
    app_module.app.config['TESTING'] = False
    app_module.users_db['student_reload'] = {
        'password': '123',
        'full_name': 'Reload Student',
        'role': 'student',
        'department': 'IT Services',
        'email': 'reload@unizulu.ac.za',
    }
    app_module.complaints_db.append({
        'id': 901,
        'full_name': 'Reload Student',
        'username': 'student_reload',
        'description': 'Persisted complaint',
        'category': 'ICT',
        'status': 'Pending',
        'created_at': '2026-09-23',
        'reference_number': 'GRV-20260923-0901',
        'is_anonymous': False,
        'evidence_path': None,
    })
    app_module.persist_state()

    importlib.reload(app_module)

    try:
        assert 'student_reload' in app_module.users_db
        assert any(item.get('reference_number') == 'GRV-20260923-0901' for item in app_module.complaints_db)
        assert 'IT Services' in app_module.departments
    finally:
        app_module.app.config['TESTING'] = True
        app_module.users_db.pop('student_reload', None)
        app_module.complaints_db[:] = [item for item in app_module.complaints_db if item.get('id') != 901]
        app_module.persist_state()


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
        data={
            'description': 'Email notification test grievance',
            'category': 'ICT',
            'evidence': (io.BytesIO(b'fake evidence'), 'evidence.pdf'),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'subject' in sent
    assert 'student1@unizulu.ac.za' in sent['recipients']
    assert any('@unizulu.ac.za' in email for email in sent['recipients'])


def test_submission_confirmation_email_contains_reference_number(monkeypatch):
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
        data={
            'description': 'Confirmation email test grievance',
            'category': 'ICT',
            'evidence': (io.BytesIO(b'fake evidence'), 'evidence.pdf'),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert 'subject' in sent
    assert 'Confirmation' in sent['subject']
    assert 'student1@unizulu.ac.za' in sent['recipients']
    assert 'Reference Number' in sent['body']
    assert 'GRV-' in sent['body']


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
