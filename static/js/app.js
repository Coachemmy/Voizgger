const state = {
    base: null,
    lang: "English",
    translations: {},
    photo: null,
};

let invoiceCache = [];
let currentInvoice = null;

function switchView(name, event) {
    if (event) event.preventDefault();
    document.querySelectorAll('.nav-item').forEach((el) => {
        el.classList.toggle('active', el.dataset.view === name);
    });
    document.querySelectorAll('.view').forEach((el) => el.classList.add('hidden'));
    const target = document.getElementById(`view-${name}`);
    if (target) target.classList.remove('hidden');
    if (name === 'invoices') renderInvoiceList();
    history.replaceState(null, '', `#${name}`);
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
        btn.setAttribute('aria-label', btn.title);
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

// Restore the tab the user was on before a refresh
const initialView = (location.hash || '').replace('#', '');
if (['dashboard', 'invoices', 'customers'].includes(initialView)) {
    switchView(initialView);
}

loadInvoices();

// Splash screen: hold for 4s, then fade out
setTimeout(() => {
    const splash = document.getElementById('splash');
    if (splash) splash.classList.add('hide');
}, 4000);

/* ---------------- Helpers ---------------- */
function updateFileName() {
    const input = document.getElementById('audioFile');
    const label = document.getElementById('fileName');
    const hasFile = input.files.length > 0;
    label.textContent = hasFile ? input.files[0].name : "No file selected";
    document.getElementById('fileRemove').classList.toggle('hidden', !hasFile);
    if (hasFile) showAudioPreview(input.files[0]); else hideAudioPreview();
}

/* ---------------- Audio preview ---------------- */
let audioPreviewUrl = null;

function showAudioPreview(blob) {
    const player = document.getElementById('audioPreview');
    if (audioPreviewUrl) URL.revokeObjectURL(audioPreviewUrl);
    audioPreviewUrl = URL.createObjectURL(blob);
    player.src = audioPreviewUrl;
    player.classList.remove('hidden');
}

function hideAudioPreview() {
    const player = document.getElementById('audioPreview');
    player.pause();
    player.removeAttribute('src');
    player.classList.add('hidden');
    if (audioPreviewUrl) {
        URL.revokeObjectURL(audioPreviewUrl);
        audioPreviewUrl = null;
    }
}

function openAudioPicker() {
    document.getElementById('audioFile').click();
}

function clearAudioFile(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('audioFile').value = "";
    updateFileName();
}

/* ---------------- In-browser recording ---------------- */
let mediaRecorder = null;
let recChunks = [];
let recStartTs = 0;
let recTimerInt = null;

async function toggleRecording(event) {
    event.preventDefault();
    event.stopPropagation();

    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        return;
    }

    if (!navigator.mediaDevices || !window.MediaRecorder) {
        alert("In-browser recording is not supported by this browser — please upload a file instead.");
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recChunks = [];
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size) recChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            stream.getTracks().forEach((t) => t.stop());
            clearInterval(recTimerInt);

            const type = mediaRecorder.mimeType || 'audio/webm';
            const ext = type.includes('ogg') ? 'ogg' : type.includes('mp4') ? 'm4a' : 'webm';
            const file = new File([new Blob(recChunks, { type })], `voice-note.${ext}`, { type });

            const dt = new DataTransfer();
            dt.items.add(file);
            document.getElementById('audioFile').files = dt.files;
            updateFileName();
            setRecUI(false);
        };

        mediaRecorder.start();
        recStartTs = Date.now();
        recTimerInt = setInterval(() => {
            const s = Math.floor((Date.now() - recStartTs) / 1000);
            document.getElementById('recTimer').textContent =
                `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
        }, 500);
        setRecUI(true);
    } catch (err) {
        alert("Microphone unavailable: " + err.message);
    }
}

function setRecUI(recording) {
    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordBtnText');
    const timer = document.getElementById('recTimer');
    btn.classList.toggle('recording', recording);
    btn.setAttribute('aria-pressed', recording ? 'true' : 'false');
    text.textContent = recording ? 'Stop recording' : 'Record voice note';
    timer.classList.toggle('hidden', !recording);
    if (!recording) timer.textContent = '0:00';
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
        const active = chip.dataset.lang === language;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', active ? 'true' : 'false');
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
async function loadInvoices() {
    try {
        const res = await fetch('/api/invoices');
        invoiceCache = await res.json();
    } catch {
        invoiceCache = [];
    }
    renderInvoiceList();
}

async function saveInvoice(data) {
    if (!data || data.error) return;
    const entry = {
        id: `VG-${String(Date.now()).slice(-6)}`,
        date: new Date().toLocaleString(),
        summary: data.summary || '',
        items: data.items || [],
        quantity: data.quantity || [],
        amount_paid: data.amount_paid || 0,
        amount_owed: data.amount_owed || 0,
    };
    try {
        const res = await fetch('/api/invoices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(entry),
        });
        invoiceCache = await res.json();
        renderInvoiceList();
    } catch {
        /* invoice stays visible in the ledger even if saving fails */
    }
}

async function clearInvoices() {
    currentInvoice = null;
    document.getElementById('invoicePaper').classList.add('hidden');
    document.getElementById('invoicePlaceholder').classList.remove('hidden');
    try {
        await fetch('/api/invoices', { method: 'DELETE' });
    } catch { /* ignore */ }
    invoiceCache = [];
    renderInvoiceList();
}

function invoiceTotal(inv) {
    return (inv.amount_paid || 0) + (inv.amount_owed || 0);
}

function renderInvoiceList() {
    const list = document.getElementById('invoiceList');
    const empty = document.getElementById('invoiceEmpty');
    const invoices = invoiceCache;

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

function showInvoice(id) {
    const inv = invoiceCache.find((i) => i.id === id);
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

/* ---------------- Visual verification ---------------- */
function resetAudit() {
    document.getElementById('photoWrap').classList.add('hidden');
    document.getElementById('photoPreview').src = "";
    document.getElementById('auditResult').classList.add('hidden');
    document.getElementById('stockPhoto').value = "";
    state.photo = null;
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
    document.getElementById('photoWrap').classList.remove('hidden');
    document.getElementById('auditResult').classList.add('hidden');
}

function clearPhoto() {
    resetAudit();
}

async function auditStock() {
    if (!state.base) return;
    if (!state.photo) {
        alert("Choose a photo of the goods first.");
        return;
    }

    const btn = document.getElementById('auditBtn');
    const resultBox = document.getElementById('auditResult');
    btn.disabled = true;
    btn.textContent = "Auditing...";
    resultBox.className = "audit-result";
    resultBox.textContent = "Reading your photo...";
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
        renderAudit(data, resultBox);
    } catch (error) {
        resultBox.className = "audit-result bad";
        resultBox.textContent = "Audit failed: " + error.message;
    } finally {
        btn.disabled = false;
        btn.textContent = "Audit stock";
    }
}

function auditBadge(verdict) {
    return {
        consistent: { text: "Verified against photo", cls: "good" },
        review: { text: "Needs a second look", cls: "bad" },
    }[verdict] || { text: "Couldn't read the photo", cls: "warn" };
}

function auditMark(check) {
    if (check.status === "match") return "✓";
    if (check.status === "short") return `−${check.recorded - check.detected}`;
    return `${check.recorded_spec || "?"} → ${check.seen_spec || "?"}`;
}

function renderAudit(data, resultBox) {
    resultBox.innerHTML = "";

    const badge = auditBadge(data.verdict);
    const head = document.createElement('div');
    head.className = 'audit-head';

    const tag = document.createElement('span');
    tag.className = 'audit-badge';
    tag.textContent = badge.text;
    head.appendChild(tag);

    if (data.confidence !== null && data.confidence !== undefined) {
        const conf = document.createElement('span');
        conf.className = 'audit-conf';
        conf.textContent = `${data.confidence}% confidence`;
        head.appendChild(conf);
    }
    resultBox.appendChild(head);

    if (data.message) {
        const msg = document.createElement('p');
        msg.className = 'audit-msg';
        msg.textContent = data.message;
        resultBox.appendChild(msg);
    }

    if (Array.isArray(data.checks) && data.checks.length) {
        const rows = document.createElement('div');
        rows.className = 'audit-rows';

        data.checks.forEach((check) => {
            const row = document.createElement('div');
            row.className = `audit-row ${check.status === 'match' ? 'ok' : 'warn'}`;

            const name = document.createElement('span');
            name.className = 'ar-item';
            name.textContent = check.item;

            const nums = document.createElement('span');
            nums.className = 'ar-nums';
            nums.textContent = `${check.recorded} recorded · ${check.detected} in photo`;

            const mark = document.createElement('span');
            mark.className = 'ar-mark';
            mark.textContent = auditMark(check);

            row.appendChild(name);
            row.appendChild(nums);
            row.appendChild(mark);
            rows.appendChild(row);
        });
        resultBox.appendChild(rows);
    } else if (Array.isArray(data.detected) && data.detected.length) {
        // Fallback for older responses that carry no per-item checks.
        const list = document.createElement('ul');
        list.className = 'audit-list';
        data.detected.forEach((row) => {
            const li = document.createElement('li');
            li.textContent = `${row.count} × ${row.item}`;
            list.appendChild(li);
        });
        resultBox.appendChild(list);
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
