const roleSelect = document.getElementById('role');
const departmentGroup = document.getElementById('department-group');
const departmentSelect = document.getElementById('department');
const logo = document.querySelector('.auth-login .logo');

// Ask staff users for a department and clear it for other roles.
function toggleDepartmentField() {
    const isStaff = roleSelect.value === 'staff';
    departmentGroup.classList.toggle('is-hidden', !isStaff);
    if (!isStaff) {
        departmentSelect.value = '';
    }
}

roleSelect.addEventListener('change', toggleDepartmentField);
toggleDepartmentField();

// Hide the logo if its image file cannot be loaded.
logo.addEventListener('error', function () {
    logo.classList.add('is-hidden');
});
