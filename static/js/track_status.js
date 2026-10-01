const statusInput = document.getElementById('status-reference');
const statusResult = document.getElementById('track-status-result');
const statusCheckBtn = document.getElementById('status-check-btn');

async function checkComplaintStatus() {
    const referenceNumber = (statusInput.value || '').trim();
    if (!referenceNumber) {
        statusResult.textContent = 'Please enter a reference number to track the complaint.';
        statusResult.classList.add('error');
        return;
    }

    statusResult.textContent = 'Checking status...';
    statusResult.classList.remove('error');

    try {
        const response = await fetch('/complaint_status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reference_number: referenceNumber })
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Reference number not found.');
        }

        statusResult.replaceChildren();
        [
            ['Reference:', data.reference_number],
            ['Status:', data.status],
            ['Category:', data.category],
            ['Submitted:', data.created_at]
        ].forEach(([label, value]) => {
            const strong = document.createElement('strong');
            strong.textContent = label + ' ';
            statusResult.append(strong, document.createTextNode(value));
            if (label !== 'Submitted:') {
                statusResult.append(document.createElement('br'));
            }
        });
    } catch (error) {
        statusResult.textContent = error.message || 'Unable to find this complaint.';
        statusResult.classList.add('error');
    }
}

statusCheckBtn.addEventListener('click', checkComplaintStatus);
statusInput.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        checkComplaintStatus();
    }
});
