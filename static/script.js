document.addEventListener("DOMContentLoaded", function () {
    console.log("Student Grievance Portal JS loaded successfully.");

    // 1. Automatically dismiss Flask flash alert messages after 5 seconds
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // 2. Client-side validation & character counter for Grievance Submission Form
    const grievanceForm = document.querySelector("#grievanceForm");
    const complaintInput = document.querySelector("#complaintText");
    const charCounter = document.querySelector("#charCounter");

    if (complaintInput && charCounter) {
        const minChars = 15;
        const maxChars = 1000;

        complaintInput.addEventListener("input", function () {
            const currentLength = complaintInput.value.length;
            charCounter.textContent = `${currentLength} / ${maxChars} characters`;

            if (currentLength < minChars) {
                charCounter.classList.add("text-danger");
                charCounter.classList.remove("text-muted", "text-success");
            } else {
                charCounter.classList.remove("text-danger");
                charCounter.classList.add("text-success");
            }
        });
    }

    if (grievanceForm) {
        grievanceForm.addEventListener("submit", function (event) {
            if (complaintInput && complaintInput.value.trim().length < 15) {
                event.preventDefault();
                alert("Please provide a more detailed complaint description (at least 15 characters).");
            }
        });
    }

    // 3. Confirm logout before navigating away
    const logoutLinks = document.querySelectorAll(".logout-btn");
    logoutLinks.forEach((link) => {
        link.addEventListener("click", function (event) {
            if (!confirm("Are you sure you want to log out?")) {
                event.preventDefault();
            }
        });
    });

    // 4. Admin Dashboard Table Search Filter
    const searchInput = document.querySelector(".search-input");
    const tableRows = document.querySelectorAll("table tbody tr");

    if (searchInput && tableRows.length > 0) {
        searchInput.addEventListener("keyup", function () {
            const query = searchInput.value.toLowerCase();
            tableRows.forEach((row) => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? "" : "none";
            });
        });
    }
});