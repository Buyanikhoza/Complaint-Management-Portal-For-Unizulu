const latestReferenceElement = document.getElementById('latest-reference');
const latestReference = latestReferenceElement?.dataset.reference || 'No reference yet';
const chatbotToggle = document.getElementById('chatbot-toggle');
const chatbotPanel = document.getElementById('chatbot-panel');
const chatbotInput = document.getElementById('chatbot-input');
const chatbotBody = document.getElementById('chatbot-body');
const chatbotSend = document.getElementById('chatbot-send');
const chatbotEvidenceInput = document.getElementById('chatbot-evidence');
const chatbotUploadBtn = document.getElementById('chatbot-upload');
const chatbotEvidenceLabel = document.getElementById('chatbot-evidence-label');
const chatState = { mode: null, category: null, description: null, evidence: null };
const chatHistory = [];
let isBusy = false;

// Add a message to the chat and retain it for the assistant conversation.
function addMessage(type, text) {
    const message = document.createElement('div');
    message.className = `chat-message ${type}`;
    message.textContent = text;
    chatbotBody.appendChild(message);
    chatHistory.push({ role: type === 'user' ? 'user' : 'assistant', content: text });
    chatbotBody.scrollTop = chatbotBody.scrollHeight;
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || 'The assistant could not complete that request.');
    }
    return data;
}

async function generateChatbotReply() {
    return postJson('/chatbot/chat', { messages: chatHistory.slice(-12) });
}

async function lookupComplaintStatus(referenceNumber) {
    const data = await postJson('/complaint_status', { reference_number: referenceNumber });
    return `Reference: ${data.reference_number}. Status: ${data.status}. Category: ${data.category}. Submitted: ${data.created_at}.`;
}

function getSelectedEvidenceFile() {
    return chatbotEvidenceInput.files?.[0] || chatState.evidence;
}

async function submitComplaint() {
    const formData = new FormData();
    formData.append('category', chatState.category);
    formData.append('description', chatState.description);
    if (chatState.anonymous) {
        formData.append('anonymous', 'on');
    }
    formData.append('evidence', chatState.evidence, chatState.evidence.name);

    const response = await fetch('/submit_grievance', { method: 'POST', body: formData });
    const html = await response.text();
    if (!response.ok || html.includes('Grievance submission failed')) {
        addMessage('bot', 'I could not submit the grievance. Please check the form message and try again.');
        return;
    }

    const reference = html.match(/Reference number: (GRV-[A-Z0-9-]+)/i)?.[1];
    addMessage('bot', reference
        ? `Your grievance was submitted. Your reference number is ${reference}.`
        : 'Your grievance was submitted. You can find its reference number on the dashboard.');
    chatState.mode = null;
    chatState.category = null;
    chatState.description = null;
    chatState.evidence = null;
    chatbotEvidenceInput.value = '';
    chatbotEvidenceLabel.textContent = 'No evidence selected';
}

// Handle status lookups and the assistant's guided submission flow.
async function handleChatInput() {
    if (isBusy) return;
    const value = chatbotInput.value.trim();
    if (!value) return;

    addMessage('user', value);
    chatbotInput.value = '';
    isBusy = true;
    chatbotSend.disabled = true;

    try {
        // Collect evidence and anonymity consent before submitting a grievance.
        if (chatState.mode === 'submit-evidence') {
            const evidence = getSelectedEvidenceFile();
            if (!evidence) {
                addMessage('bot', 'Please use Upload Evidence to select a supporting file before continuing.');
                return;
            }
            chatState.evidence = evidence;
            chatState.mode = 'submit-anonymous';
            addMessage('bot', 'Would you like to submit this grievance anonymously? Reply Yes or No.');
            return;
        }

        if (chatState.mode === 'submit-anonymous') {
            if (/^(yes|y|anonymous)(\b|$)/i.test(value)) {
                chatState.anonymous = true;
            } else if (/^(no|n|with my name)(\b|$)/i.test(value)) {
                chatState.anonymous = false;
            } else {
                addMessage('bot', 'Please reply Yes to submit anonymously or No to include your name.');
                return;
            }
            addMessage('bot', 'Submitting your grievance...');
            await submitComplaint();
            return;
        }

        const referenceNumber = value.match(/GRV-[A-Z0-9-]+/i)?.[0];
        const asksForStatus = /status|track|reference|latest|recent/i.test(value);
        if (referenceNumber || asksForStatus) {
            const reference = referenceNumber || (/latest|recent/i.test(value) ? latestReference : null);
            if (!reference || reference === 'No reference yet') {
                addMessage('bot', 'Please provide the reference number from your dashboard so I can check its status.');
                return;
            }
            addMessage('bot', await lookupComplaintStatus(reference));
            return;
        }

        const result = await generateChatbotReply();
        addMessage('bot', result.reply);
        if (result.needs_safety_review) {
            return;
        }
        if (!result.category) return;

        chatState.category = result.category;
        chatState.description = value;
        chatState.mode = 'submit-evidence';
        addMessage('bot', `Suggested category: ${result.category}. Select supporting evidence and type continue when ready. Nothing will be submitted until you confirm anonymity.`);
    } catch (error) {
        addMessage('bot', error.message || 'The assistant is temporarily unavailable. Please use the grievance form.');
    } finally {
        isBusy = false;
        chatbotSend.disabled = false;
    }
}

chatbotToggle.addEventListener('click', function () {
    chatbotPanel.classList.toggle('open');
    if (chatbotPanel.classList.contains('open')) chatbotInput.focus();
});

chatbotUploadBtn.addEventListener('click', function () {
    chatbotEvidenceInput.click();
});

chatbotEvidenceInput.addEventListener('change', function () {
    const file = getSelectedEvidenceFile();
    chatbotEvidenceLabel.textContent = file ? file.name : 'No evidence selected';
    if (file) addMessage('bot', 'Evidence selected. Type continue when you are ready.');
});

chatbotSend.addEventListener('click', handleChatInput);
chatbotInput.addEventListener('keydown', function (event) {
    if (event.key === 'Enter') handleChatInput();
});

document.querySelectorAll('.withdraw-form').forEach(form => {
    form.addEventListener('submit', function (event) {
        if (!confirm('Are you sure you want to withdraw this grievance?')) event.preventDefault();
    });
});
