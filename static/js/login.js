const roleSelect = document.getElementById('role');
const departmentGroup = document.getElementById('department-group');
const departmentSelect = document.getElementById('department');
const usernameInput = document.getElementById('username');
const logo = document.querySelector('.auth-login .logo');

// Only staff need a department; only students use a nine-digit username.
function toggleDepartmentField() {
    const isStaff = roleSelect.value === 'staff';
    const isStudent = roleSelect.value === 'student';
    departmentGroup.classList.toggle('is-hidden', !isStaff);
    departmentSelect.required = isStaff;
    if (!isStaff) {
        departmentSelect.value = '';
    }

    if (isStudent) {
        usernameInput.pattern = '[0-9]{9}';
        usernameInput.title = 'Student number must be exactly 9 digits.';
        usernameInput.placeholder = 'Enter your 9-digit student number';
        usernameInput.inputMode = 'numeric';
    } else {
        usernameInput.removeAttribute('pattern');
        usernameInput.removeAttribute('title');
        usernameInput.placeholder = 'Enter your username';
        usernameInput.inputMode = 'text';
    }
}

roleSelect.addEventListener('change', toggleDepartmentField);
toggleDepartmentField();

// Hide the logo if its image file cannot be loaded.
logo.addEventListener('error', function () {
    logo.classList.add('is-hidden');
});
