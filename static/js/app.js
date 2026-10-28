function updateFileName() {
    const input = document.getElementById('audioFile');
    const fileNameSpan = document.getElementById('fileName');
    if (input.files.length > 0) {
        fileNameSpan.textContent = input.files[0].name;
    }
}

function displayData(data) {
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('errorBox').classList.add('hidden');
    document.getElementById('ledger').classList.remove('hidden');

    document.getElementById('transcriptText').textContent = data.transcript || "No transcript available.";
    document.getElementById('amountPaid').textContent = `₦${(data.amount_paid || 0).toLocaleString()}`;
    document.getElementById('amountOwed').textContent = `₦${(data.amount_owed || 0).toLocaleString()}`;

    const tbody = document.getElementById('itemsTableBody');
    tbody.innerHTML = ''; 

    if (data.items && data.items.length > 0) {
        data.items.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${item}</td><td>${data.quantity[index]}</td>`;
            tbody.appendChild(tr);
        });
    }

    const agenticBox = document.getElementById('agenticAction');
    if (data.follow_up_sms && data.follow_up_sms.trim() !== "") {
        document.getElementById('smsText').textContent = `"${data.follow_up_sms}"`;
        agenticBox.classList.remove('hidden');
    } else {
        agenticBox.classList.add('hidden');
    }
}

function copySMS() {
    const text = document.getElementById('smsText').textContent.replace(/^"|"$/g, '');
    navigator.clipboard.writeText(text).then(() => {
        alert("SMS copied to clipboard!");
    });
}

async function processAudio() {
    const fileInput = document.getElementById('audioFile');
    const submitBtn = document.getElementById('submitBtn');
    const errorBox = document.getElementById('errorBox');
    
    if (!fileInput.files[0]) {
        alert("Please select an audio file first.");
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerText = "Processing...";
    errorBox.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/api/analyze_voice', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();

        if (data.error) {
            errorBox.textContent = data.error;
            errorBox.classList.remove('hidden');
            return;
        }

        displayData(data);

    } catch (error) {
        errorBox.textContent = "Network Error: " + error.message;
        errorBox.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Process Transaction";
    }
}

function loadDemoData() {
    const demoData = {
        transcript: "I sell 3 bags of rice for twenty thousand Naira, customer paid fifteen thousand, owes five thousand.",
        items: ["Rice (50kg)", "Beans (Olotu)"],
        quantity: [3, 1],
        amount_paid: 20000,
        amount_owed: 5000,
        follow_up_sms: "Hello! Just a quick reminder about the 5,000 Naira balance for the rice and beans. Please let me know when you can complete the payment. Thank you!"
    };
    displayData(demoData);
}