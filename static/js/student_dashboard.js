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
const pausedDrafts = [];
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

function isOfficialInfoQuestion(message) {
    const asksForInformation = /\b(what|how|when|where|which|tell me|information|info|find|look up)\b/i.test(message);
    const mentionsUniversityTopic = /\b(unizulu|university|admission|apply|application|fee|tuition|programme|course|calendar|contact|campus)\b/i.test(message);
    const describesPersonalGrievance = /\b(grievance|complaint|debt|balance|owe|allowance|not received|not paid)\b/i.test(message);
    return asksForInformation && mentionsUniversityTopic && !describesPersonalGrievance;
}

async function lookupOfficialInfo(query) {
    const data = await postJson('/chatbot/unizulu-search', { query });
    return data.reply;
}

function getSelectedEvidenceFile() {
    return chatbotEvidenceInput.files?.[0] || chatState.evidence;
}

function clearActiveDraft() {
    chatState.mode = null;
    chatState.category = null;
    chatState.description = null;
    chatState.evidence = null;
    chatState.anonymous = false;
    chatbotEvidenceInput.value = '';
    chatbotEvidenceLabel.textContent = 'No evidence selected';
}

function pauseActiveDraft() {
    if (!chatState.mode) return false;

    pausedDrafts.push({
        mode: chatState.mode,
        category: chatState.category,
        description: chatState.description,
        evidence: getSelectedEvidenceFile(),
        anonymous: chatState.anonymous
    });
    clearActiveDraft();
    return true;
}

function resumePausedDraft() {
    const draft = pausedDrafts.pop();
    if (!draft) return false;

    Object.assign(chatState, draft);
    chatbotEvidenceLabel.textContent = draft.evidence ? draft.evidence.name : 'No evidence selected';
    return true;
}

async function submitComplaint() {
    const formData = new FormData();
    formData.append('category', chatState.category);
    formData.append('description', chatState.description);
    if (chatState.anonymous) {
        formData.append('anonymous', 'on');
    }
    formData.append('evidence', chatState.evidence, chatState.evidence.name);

    const response = await fetch('/submit_grievance', {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: formData
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.error || 'I could not submit the grievance. Please try again.');
    }

    addMessage('bot', result.reference_number
        ? `Your grievance was submitted. Your reference number is ${result.reference_number}.${result.email_sent ? '' : ' The confirmation email could not be sent, but your grievance is saved.'}`
        : 'Your grievance was submitted. You can find its reference number on the dashboard.');
    clearActiveDraft();
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

        if (isOfficialInfoQuestion(value)) {
            addMessage('bot', await lookupOfficialInfo(value));
            return;
        }

        if (/^(resume|resume draft|continue previous draft)$/i.test(value) && !chatState.mode) {
            if (resumePausedDraft()) {
                addMessage('bot', `I resumed your ${chatState.category} grievance draft. You can continue it, or ask me something else at any time.`);
            } else {
                addMessage('bot', 'There is no paused grievance draft to resume.');
            }
            return;
        }

        if (chatState.mode && /^(cancel|cancel submission|start over)$/i.test(value)) {
            clearActiveDraft();
            addMessage('bot', 'I cancelled the draft. You can ask a question or describe a grievance whenever you are ready.');
            return;
        }

        if (chatState.mode === 'submit-evidence' && /^(continue|ready|i am ready|done|next|proceed)$/i.test(value)) {
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
                // Unrecognized input is handled as a new request below.
                chatState.anonymous = null;
            }
            if (chatState.anonymous !== null) {
                addMessage('bot', 'Submitting your grievance...');
                await submitComplaint();
                return;
            }
        }

        const result = await generateChatbotReply();
        addMessage('bot', result.reply);
        if (result.needs_safety_review) {
            return;
        }
        if (!result.category) return;

        if (pauseActiveDraft()) {
            addMessage('bot', 'I paused your previous grievance draft so I can handle this new request. Say “resume draft” whenever you want to return to it.');
        }
        chatState.category = result.category;
        chatState.description = value;
        chatState.evidence = null;
        chatState.anonymous = false;
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
