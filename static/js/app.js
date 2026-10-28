const state = {
    base: null,
    lang: "English",
    translations: {},
    photo: null,
};

function switchView(name, event) {
    if (event) event.preventDefault();
    document.querySelectorAll('.nav-item').forEach((el) => {
        el.classList.toggle('active', el.dataset.view === name);
    });
    document.querySelectorAll('.view').forEach((el) => el.classList.add('hidden'));
    const target = document.getElementById(`view-${name}`);
    if (target) target.classList.remove('hidden');
    if (name === 'invoices') renderInvoiceList();
}

(function initParticles() {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const HUES = [231, 217, 199, 174]; 
    let W, H, particles;

    function resize() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    }

    function spawn() {
        particles = Array.from({ length: 55 }, () => ({
            x: Math.random() * W,
            y: Math.random() * H,
            r: 1.2 + Math.random() * 2.6,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
            hue: HUES[Math.floor(Math.random() * HUES.length)],
            alpha: 0.15 + Math.random() * 0.25,
            pulse: Math.random() * Math.PI * 2,
        }));
    }

    function tick() {
        ctx.clearRect(0, 0, W, H);
        const dark = document.body.classList.contains('dark');
        for (const p of particles) {
            p.x += p.vx;
            p.y += p.vy;
            p.pulse += 0.02;
            if (p.x < -10) p.x = W + 10;
            if (p.x > W + 10) p.x = -10;
            if (p.y < -10) p.y = H + 10;
            if (p.y > H + 10) p.y = -10;

            const a = p.alpha * (0.7 + 0.3 * Math.sin(p.pulse)) * (dark ? 1.4 : 1);
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${p.hue}, 85%, ${dark ? 70 : 55}%, ${a})`;
            ctx.fill();
        }
        requestAnimationFrame(tick);
    }

    window.addEventListener('resize', resize);
    resize();
    spawn();
    tick();
})();

/* ---------------- Theme ---------------- */
function syncThemeIcon() {
    const isDark = document.body.classList.contains('dark');
    const btn = document.getElementById('themeToggle');
    if (btn) {
        btn.textContent = isDark ? '☀️' : '🌙';
        btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    }
}

function toggleTheme() {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
    syncThemeIcon();
}

if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark');
}
syncThemeIcon();

/* ---------------- Helpers ---------------- */
function updateFileName() {
    const input = document.getElementById('audioFile');
    const label = document.getElementById('fileName');
    label.textContent = input.files.length ? input.files[0].name : "No file selected";
}

function showError(message) {
    const box = document.getElementById('errorBox');
    box.textContent = message;
    box.classList.remove('hidden');
}

function hideError() {
    document.getElementById('errorBox').classList.add('hidden');
}

function englishView() {
    const b = state.base;
    return {
        transcript: b.transcript || "",
        items: b.items || [],
        summary: b.summary || "",
        follow_up_sms: b.follow_up_sms || "",
    };
}

function setActiveChip(language) {
    document.querySelectorAll('#langChips .chip').forEach((chip) => {
        chip.classList.toggle('active', chip.dataset.lang === language);
    });
}

function setTranslating(isTranslating) {
    document.getElementById('langChips').classList.toggle('loading', isTranslating);
    document.getElementById('transcriptText').classList.toggle('loading', isTranslating);
}

/* ---------------- Rendering ---------------- */
function renderLedger(view) {
    const base = state.base;
    const isEnglish = state.lang === "English";

    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('ledger').classList.remove('hidden');

    document.getElementById('transcriptText').textContent =
        view.transcript || "No transcript available.";

    const originalEl = document.getElementById('originalTranscript');
    if (!isEnglish && base.transcript) {
        originalEl.textContent = `Original (English): ${base.transcript}`;
        originalEl.classList.remove('hidden');
    } else {
        originalEl.classList.add('hidden');
    }

    const summaryEl = document.getElementById('summaryText');
    summaryEl.textContent = view.summary || "";
    summaryEl.classList.toggle('hidden', !view.summary);

    // Confidence badge (Feature: Confidence Ledger)
    const badge = document.getElementById('confidenceBadge');
    const confidence = Number.isFinite(base.confidence) ? base.confidence : null;
    if (confidence === null) {
        badge.textContent = "Verified";
        badge.classList.remove('warn');
    } else {
        badge.textContent = confidence < 80 ? `${confidence}% · review` : `${confidence}% confidence`;
        badge.classList.toggle('warn', confidence < 80);
    }

    document.getElementById('amountPaid').textContent = `₦${(base.amount_paid || 0).toLocaleString()}`;
    document.getElementById('amountOwed').textContent = `₦${(base.amount_owed || 0).toLocaleString()}`;

    const tbody = document.getElementById('itemsTableBody');
    tbody.innerHTML = '';

    const quantities = Array.isArray(base.quantity) ? base.quantity : [];
    const itemConfidence = Array.isArray(base.item_confidence) ? base.item_confidence : [];
    const items = Array.isArray(view.items) ? view.items : [];

    items.forEach((item, index) => {
        const tr = document.createElement('tr');
        const tdItem = document.createElement('td');
        const tdQty = document.createElement('td');

        tdItem.textContent = item;

        const score = itemConfidence[index];
        if (Number.isFinite(score) && score < 80) {
            tr.classList.add('warn');
            const hint = document.createElement('span');
            hint.className = 'verify-hint';
            hint.textContent = 'verify';
            hint.title = `${score}% confidence on this quantity`;
            tdItem.appendChild(hint);
        }

        tdQty.className = 'num';
        tdQty.textContent = quantities[index] ?? '—';

        tr.appendChild(tdItem);
        tr.appendChild(tdQty);
        tbody.appendChild(tr);
    });

    const agenticBox = document.getElementById('agenticAction');
    if (view.follow_up_sms && view.follow_up_sms.trim() !== "") {
        document.getElementById('smsText').textContent = `"${view.follow_up_sms}"`;
        agenticBox.classList.remove('hidden');
    } else {
        agenticBox.classList.add('hidden');
    }
}

function displayData(data) {
    state.base = data;
    state.translations = {};
    state.photo = null;
    resetAudit();
    hideError();

    renderLedger(englishView());
    saveInvoice(data);

    if (state.lang !== "English") {
        switchLanguage(state.lang);
    }
}

/* ---------------- Invoices ---------------- */
function invoiceStore() {
    try {
        return JSON.parse(localStorage.getItem('voizgger_invoices') || '[]');
    } catch {
        return [];
    }
}

function saveInvoice(data) {
    if (!data || data.error) return;
    const invoices = invoiceStore();
    const entry = {
        id: `VG-${String(Date.now()).slice(-6)}`,
        date: new Date().toLocaleString(),
        summary: data.summary || '',
        items: data.items || [],
        quantity: data.quantity || [],
        amount_paid: data.amount_paid || 0,
        amount_owed: data.amount_owed || 0,
    };
    invoices.unshift(entry);
    localStorage.setItem('voizgger_invoices', JSON.stringify(invoices.slice(0, 25)));
}

function clearInvoices() {
    localStorage.removeItem('voizgger_invoices');
    renderInvoiceList();
}

function invoiceTotal(inv) {
    return (inv.amount_paid || 0) + (inv.amount_owed || 0);
}

function renderInvoiceList() {
    const list = document.getElementById('invoiceList');
    const empty = document.getElementById('invoiceEmpty');
    const invoices = invoiceStore();

    list.innerHTML = '';
    empty.classList.toggle('hidden', invoices.length > 0);

    invoices.forEach((inv) => {
        const row = document.createElement('button');
        row.className = 'invoice-row';
        row.onclick = () => showInvoice(inv.id);
        row.innerHTML = `
            <span class="inv-id">${inv.id}</span>
            <span class="inv-desc">${inv.summary || 'Voice transaction'}</span>
            <span class="inv-amt">₦${invoiceTotal(inv).toLocaleString()}</span>`;
        list.appendChild(row);
    });
}

let currentInvoice = null;

function showInvoice(id) {
    const inv = invoiceStore().find((i) => i.id === id);
    if (!inv) return;
    currentInvoice = inv;

    document.getElementById('invoicePlaceholder').classList.add('hidden');
    document.getElementById('invoicePaper').classList.remove('hidden');

    document.getElementById('invNumber').textContent = inv.id;
    document.getElementById('invDate').textContent = inv.date;
    document.getElementById('invSummary').textContent = inv.summary || '';

    const tbody = document.getElementById('invItemsBody');
    tbody.innerHTML = '';
    (inv.items || []).forEach((item, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${item}</td><td class="num">${(inv.quantity || [])[i] ?? '—'}</td>`;
        tbody.appendChild(tr);
    });

    document.getElementById('invTotal').textContent = `₦${invoiceTotal(inv).toLocaleString()}`;
    document.getElementById('invPaid').textContent = `₦${(inv.amount_paid || 0).toLocaleString()}`;
    document.getElementById('invOwed').textContent = `₦${(inv.amount_owed || 0).toLocaleString()}`;
}

function downloadInvoice() {
    if (!currentInvoice) return;
    const inv = currentInvoice;
    const lines = [
        'VOIZGGER — VOICE-GENERATED INVOICE',
        `Invoice: ${inv.id}`,
        `Date: ${inv.date}`,
        '',
        inv.summary,
        '',
        ...(inv.items || []).map((item, i) => `${item}  x${(inv.quantity || [])[i] ?? '—'}`),
        '',
        `Total:        ₦${invoiceTotal(inv).toLocaleString()}`,
        `Paid:         ₦${(inv.amount_paid || 0).toLocaleString()}`,
        `Balance due:  ₦${(inv.amount_owed || 0).toLocaleString()}`,
        '',
        'Generated by Meta Muse Spark from a voice note.',
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${inv.id}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
}

/* ---------------- Language switching ---------------- */
async function switchLanguage(language) {
    state.lang = language;
    setActiveChip(language);

    if (!state.base) return;

    if (language === "English") {
        renderLedger(englishView());
        return;
    }

    if (state.translations[language]) {
        renderLedger(state.translations[language]);
        return;
    }

    setTranslating(true);
    try {
        const response = await fetch('/api/translate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...englishView(), language }),
        });
        const data = await response.json();

        if (data.error) {
            showError(data.error);
            if (state.lang === language) renderLedger(englishView());
            return;
        }

        state.translations[language] = data;
        if (state.lang === language) renderLedger(data);
    } catch (error) {
        showError("Translation failed: " + error.message);
    } finally {
        setTranslating(false);
    }
}

/* ---------------- Processing ---------------- */
async function processAudio() {
    const fileInput = document.getElementById('audioFile');
    const submitBtn = document.getElementById('submitBtn');

    if (!fileInput.files[0]) {
        alert("Please select an audio file first.");
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerText = "Processing...";
    hideError();

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', 'English');
    formData.append('deep_audit', document.getElementById('deepAudit').checked ? 'true' : 'false');

    try {
        const response = await fetch('/api/analyze_voice', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        displayData(data);
    } catch (error) {
        showError("Network Error: " + error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Process Transaction";
    }
}

/* ---------------- Demo ---------------- */
function loadDemoData() {
    displayData({
        transcript: "I sell three bags of rice and one bag of beans for twenty thousand Naira. The customer paid fifteen thousand, and he still owes five thousand.",
        summary: "Sold 3 bags of rice and 1 bag of beans for ₦20,000; customer paid ₦15,000 and still owes ₦5,000.",
        items: ["Rice (50kg)", "Beans (Olotu)"],
        quantity: [3, 1],
        amount_paid: 15000,
        amount_owed: 5000,
        follow_up_sms: "Hello! Just a quick reminder about the 5,000 Naira balance for the rice and beans. Please let me know when you can complete the payment. Thank you!",
        confidence: 92,
        item_confidence: [95, 74],
        language: "English",
    });
}

/* ---------------- Visual verification ---------------- */
function resetAudit() {
    const preview = document.getElementById('photoPreview');
    preview.src = "";
    preview.classList.add('hidden');
    document.getElementById('auditResult').classList.add('hidden');
    document.getElementById('stockPhoto').value = "";
    const btn = document.getElementById('auditBtn');
    btn.disabled = false;
    btn.textContent = "Audit stock";
}

function onPhotoPicked() {
    const input = document.getElementById('stockPhoto');
    const preview = document.getElementById('photoPreview');

    if (!input.files.length) return;

    state.photo = input.files[0];
    preview.src = URL.createObjectURL(state.photo);
    preview.classList.remove('hidden');
}

async function auditStock() {
    if (!state.base) return;
    if (!state.photo) {
        alert("Choose a shelf photo first.");
        return;
    }

    const btn = document.getElementById('auditBtn');
    const resultBox = document.getElementById('auditResult');
    btn.disabled = true;
    btn.textContent = "Auditing...";
    resultBox.className = "audit-result";
    resultBox.textContent = "Reading the shelf...";
    resultBox.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', state.photo);
    formData.append('items', JSON.stringify(state.base.items || []));
    formData.append('quantities', JSON.stringify(state.base.quantity || []));

    try {
        const response = await fetch('/api/verify_stock', { method: 'POST', body: formData });
        const data = await response.json();

        if (data.error) {
            resultBox.className = "audit-result bad";
            resultBox.textContent = data.error;
            return;
        }

        const tone = { consistent: 'good', review: 'bad', unknown: 'warn' }[data.verdict] || 'warn';
        resultBox.className = `audit-result ${tone}`;
        resultBox.textContent = data.message;

        if (Array.isArray(data.detected) && data.detected.length) {
            const list = document.createElement('ul');
            list.className = 'audit-list';
            data.detected.forEach((row) => {
                const li = document.createElement('li');
                li.textContent = `${row.count} × ${row.item}`;
                list.appendChild(li);
            });
            resultBox.appendChild(list);
        }
    } catch (error) {
        resultBox.className = "audit-result bad";
        resultBox.textContent = "Audit failed: " + error.message;
    } finally {
        btn.disabled = false;
        btn.textContent = "Audit stock";
    }
}

/* ---------------- Follow-up actions ---------------- */
function currentSMS() {
    return document.getElementById('smsText').textContent.replace(/^"|"$/g, '').trim();
}

function copySMS() {
    const text = currentSMS();
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => alert("Message copied to clipboard!"));
}

function sendWhatsApp() {
    const text = currentSMS();
    if (!text) return;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
}
