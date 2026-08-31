// ═══════════════════════════════════════════════════════════════════════════════
// LIBRA — Premium Library Management System JS
// ═══════════════════════════════════════════════════════════════════════════════

'use strict';

// ── Sidebar ──────────────────────────────────────────────────────────────────

const sidebar       = document.getElementById('sidebar');
const mainContent   = document.getElementById('mainContent');
const sidebarToggle = document.getElementById('sidebarToggle');
const mobileToggle  = document.getElementById('mobileToggle');
const sidebarOverlay= document.getElementById('sidebarOverlay');

let sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';

function applySidebar() {
  if (window.innerWidth <= 768) return;
  if (sidebarCollapsed) {
    sidebar?.classList.add('collapsed');
    mainContent?.classList.add('collapsed');
    if (sidebarToggle) sidebarToggle.textContent = '›';
  } else {
    sidebar?.classList.remove('collapsed');
    mainContent?.classList.remove('collapsed');
    if (sidebarToggle) sidebarToggle.textContent = '‹';
  }
}

sidebarToggle?.addEventListener('click', () => {
  sidebarCollapsed = !sidebarCollapsed;
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
  applySidebar();
});

mobileToggle?.addEventListener('click', () => {
  sidebar?.classList.toggle('mobile-open');
  sidebarOverlay?.classList.toggle('active');
  sidebarOverlay.style.display = sidebar?.classList.contains('mobile-open') ? 'block' : 'none';
});

sidebarOverlay?.addEventListener('click', () => {
  sidebar?.classList.remove('mobile-open');
  sidebarOverlay.style.display = 'none';
});

applySidebar();

// ── Toast System ─────────────────────────────────────────────────────────────

function showToast(type, title, message, duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    success: '✓',
    error:   '✕',
    warning: '⚠',
    info:    'ℹ'
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.style.position = 'relative';
  toast.innerHTML = `
    <div class="toast-icon">${icons[type] || 'ℹ'}</div>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-msg">${message}</div>` : ''}
    </div>
    <button onclick="dismissToast(this.parentElement)" style="
      background:none;border:none;color:var(--text-muted);font-size:16px;
      cursor:pointer;padding:4px;margin-left:8px;line-height:1;">✕</button>
    <div class="toast-progress"></div>
  `;

  container.appendChild(toast);

  setTimeout(() => dismissToast(toast), duration);
}

function dismissToast(el) {
  if (!el) return;
  el.classList.add('toast-out');
  setTimeout(() => el.remove(), 350);
}

// Auto-dismiss flashed toasts from Flask
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-toast]').forEach(el => {
    const type = el.dataset.type || 'info';
    const msg  = el.dataset.message || '';
    showToast(type, msg);
    el.remove();
  });
});

// ── ISBN Validator ────────────────────────────────────────────────────────────

const isbnInput = document.getElementById('isbn');
const isbnStatus = document.getElementById('isbnStatus');

if (isbnInput) {
  isbnInput.addEventListener('input', debounce(async () => {
    const val = isbnInput.value.replace(/[-\s]/g, '');
    if (!val) {
      isbnStatus.innerHTML = '';
      isbnInput.classList.remove('error', 'success');
      return;
    }
    try {
      const res = await fetch(`/api/validate_isbn/?isbn=${encodeURIComponent(val)}`);
      const data = await res.json();
      if (!data.valid) {
        isbnStatus.innerHTML = '<span class="isbn-status invalid">🔴 ISBN must contain exactly 13 digits</span>';
        isbnInput.classList.add('error'); isbnInput.classList.remove('success');
      } else if (!data.unique) {
        isbnStatus.innerHTML = '<span class="isbn-status invalid">🔴 This ISBN already exists in the library</span>';
        isbnInput.classList.add('error'); isbnInput.classList.remove('success');
      } else {
        isbnStatus.innerHTML = '<span class="isbn-status valid">🟢 Valid ISBN — Ready to add</span>';
        isbnInput.classList.add('success'); isbnInput.classList.remove('error');
      }
    } catch(e) {
      // silent fail
    }
  }, 400));
}

// ── Live Book Preview ─────────────────────────────────────────────────────────

function initLivePreview() {
  const fields = {
    title:  document.getElementById('title'),
    author: document.getElementById('author'),
    genre:  document.getElementById('genre'),
    isbn:   document.getElementById('isbn'),
    copies: document.getElementById('total_copies'),
  };

  const preview = {
    title:  document.getElementById('previewTitle'),
    author: document.getElementById('previewAuthor'),
    genre:  document.getElementById('previewGenre'),
    isbn:   document.getElementById('previewISBN'),
    copies: document.getElementById('previewCopies'),
    cover:  document.getElementById('previewCover'),
  };

  if (!fields.title || !preview.title) return;

  const coverColors = [
    'linear-gradient(135deg,#6366f1,#8b5cf6)',
    'linear-gradient(135deg,#3b82f6,#6366f1)',
    'linear-gradient(135deg,#10b981,#06b6d4)',
    'linear-gradient(135deg,#f59e0b,#f97316)',
    'linear-gradient(135deg,#ec4899,#8b5cf6)',
    'linear-gradient(135deg,#f43f5e,#ec4899)',
  ];

  function update() {
    const t = fields.title?.value || '';
    const a = fields.author?.value || '';
    const g = fields.genre?.value || '';
    const i = (fields.isbn?.value || '').replace(/[-\s]/g, '');
    const c = fields.copies?.value || '';

    preview.title.textContent  = t || 'Book Title';
    preview.author.textContent = a || 'Author Name';
    preview.genre.textContent  = g || '—';
    preview.isbn.textContent   = i ? `ISBN: ${i}` : 'ISBN: —';
    preview.copies.textContent = c ? `${c} ${c == 1 ? 'copy' : 'copies'}` : '—';
  }

  Object.values(fields).forEach(f => {
    if (f) {
      f.addEventListener('input', update);
      f.addEventListener('change', update);
    }
  });

  update();
}

document.addEventListener('DOMContentLoaded', initLivePreview);

// ── Issue Book Wizard ─────────────────────────────────────────────────────────

let currentStep = 1;

function initWizard() {
  const bookSelect = document.getElementById('bookSelect');
  const selectedBookCard = document.getElementById('selectedBookCard');
  const step2Btn = document.getElementById('toStep2Btn');
  const step3Btn = document.getElementById('toStep3Btn');
  const backBtn1 = document.getElementById('backToStep1');
  const backBtn2 = document.getElementById('backToStep2');

  if (!bookSelect) return;

  bookSelect?.addEventListener('change', async () => {
    const bookId = bookSelect.value;
    if (!bookId) {
      selectedBookCard.style.display = 'none';
      step2Btn.disabled = true;
      return;
    }
    try {
      const res = await fetch(`/api/book/${bookId}/`);
      const book = await res.json();
      document.getElementById('sbTitle').textContent    = book.title;
      document.getElementById('sbAuthor').textContent   = book.author;
      document.getElementById('sbISBN').textContent     = book.isbn;
      document.getElementById('sbAvail').textContent    = `${book.available_copies} of ${book.total_copies} copies`;
      document.getElementById('sbGenre').textContent    = book.genre;
      selectedBookCard.style.display = 'block';
      step2Btn.disabled = false;
    } catch(e) { /* silent */ }
  });

  step2Btn?.addEventListener('click', () => goToStep(2));
  step3Btn?.addEventListener('click', () => {
    const memberName = document.getElementById('memberName').value.trim();
    const memberId   = document.getElementById('memberId').value.trim();
    if (!memberName) { showToast('error', 'Member name is required'); return; }
    if (!memberId)   { showToast('error', 'Member ID is required'); return; }
    // Populate confirm step
    document.getElementById('confBook').textContent    = document.getElementById('sbTitle').textContent;
    document.getElementById('confMember').textContent  = memberName;
    document.getElementById('confMemberId').textContent= memberId;
    document.getElementById('confDue').textContent     = document.getElementById('dueDate').value || document.getElementById('defaultDue')?.textContent || '—';
    goToStep(3);
  });

  backBtn1?.addEventListener('click', () => goToStep(1));
  backBtn2?.addEventListener('click', () => goToStep(2));
}

function goToStep(n) {
  document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`step${n}Panel`)?.classList.add('active');

  document.querySelectorAll('.wizard-step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i + 1 < n) s.classList.add('done');
    else if (i + 1 === n) s.classList.add('active');
  });

  document.querySelectorAll('.wizard-connector').forEach((c, i) => {
    c.classList.toggle('done', i < n - 1);
  });

  currentStep = n;
}

document.addEventListener('DOMContentLoaded', initWizard);

// ── Return Book Search ────────────────────────────────────────────────────────

function initReturnSearch() {
  const input = document.getElementById('issueIdInput');
  if (!input) return;

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      document.getElementById('searchReturnBtn')?.click();
    }
  });
}

document.addEventListener('DOMContentLoaded', initReturnSearch);

// ── Delete Modal ──────────────────────────────────────────────────────────────

let pendingDeleteId = null;
let pendingDeleteTitle = null;

function openDeleteModal(bookId, bookTitle, available, total) {
  pendingDeleteId    = bookId;
  pendingDeleteTitle = bookTitle;

  const modal = document.getElementById('deleteModal');
  const blockedMsg  = document.getElementById('deleteBlockedMsg');
  const confirmForm = document.getElementById('deleteConfirmSection');
  const titleEl = document.getElementById('deleteBookTitle');

  if (titleEl) titleEl.textContent = bookTitle;

  if (available < total) {
    const issued = total - available;
    blockedMsg.style.display  = 'block';
    confirmForm.style.display = 'none';
    document.getElementById('issuedCount').textContent = issued;
  } else {
    blockedMsg.style.display  = 'none';
    confirmForm.style.display = 'block';
    const confirmInput = document.getElementById('deleteConfirmInput');
    if (confirmInput) confirmInput.value = '';
  }

  modal?.classList.add('open');
}

function closeDeleteModal() {
  document.getElementById('deleteModal')?.classList.remove('open');
  pendingDeleteId = null;
}

function submitDelete() {
  const input = document.getElementById('deleteConfirmInput');
  if (!input || input.value.trim().toUpperCase() !== 'YES') {
    showToast('error', 'Type YES exactly to confirm deletion');
    input?.focus();
    return;
  }
  // Use the pre-rendered form in base.html
  const form = document.getElementById('deleteForm');
  if (form) {
    form.action = `/delete_book/${pendingDeleteId}/`;
    document.getElementById('deleteConfirmHidden').value = 'YES';
    form.submit();
  } else {
    // Fallback: create form dynamically
    const f = document.createElement('form');
    f.method = 'POST';
    f.action = `/delete_book/${pendingDeleteId}/`;
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrf) f.appendChild(csrf.cloneNode());
    const field = document.createElement('input');
    field.type = 'hidden';
    field.name = 'confirm';
    field.value = 'YES';
    f.appendChild(field);
    document.body.appendChild(f);
    f.submit();
  }
}

// Validate YES typing
document.addEventListener('input', (e) => {
  if (e.target.id === 'deleteConfirmInput') {
    const btn = document.getElementById('confirmDeleteBtn');
    if (btn) btn.disabled = e.target.value.trim().toUpperCase() !== 'YES';
  }
});


// Close modal on overlay click
document.addEventListener('click', (e) => {
  if (e.target.id === 'deleteModal') closeDeleteModal();
});

// ESC key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeDeleteModal();
});

// ── Charts ────────────────────────────────────────────────────────────────────

let activityChart = null;
let genreChart     = null;

function initCharts() {
  initActivityChart();
  initDashboardGenreChart();
}

async function initActivityChart() {
  const canvas = document.getElementById('activityChart');
  if (!canvas) return;

  const res  = await fetch('/api/activity/?days=7');
  const data = await res.json();

  const ctx = canvas.getContext('2d');
  
  const gradientIssued = ctx.createLinearGradient(0, 0, 0, 300);
  gradientIssued.addColorStop(0, 'rgba(67, 24, 255, 0.4)');
  gradientIssued.addColorStop(1, 'rgba(67, 24, 255, 0.01)');
  
  const gradientReturned = ctx.createLinearGradient(0, 0, 0, 300);
  gradientReturned.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
  gradientReturned.addColorStop(1, 'rgba(16, 185, 129, 0.01)');

  activityChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels.map(d => {
        const dt = new Date(d);
        return dt.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
      }),
      datasets: [
        {
          label: 'Books Issued',
          data: data.issued,
          borderColor: '#4318FF',
          backgroundColor: gradientIssued,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#4318FF',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        {
          label: 'Books Returned',
          data: data.returned,
          borderColor: '#10b981',
          backgroundColor: gradientReturned,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#10b981',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#ffffff',
          borderColor: 'rgba(0,0,0,0.05)',
          borderWidth: 1,
          titleColor: '#1B254B',
          bodyColor: '#475569',
          padding: 12,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#475569', font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#475569', font: { size: 11 }, stepSize: 1 },
          beginAtZero: true,
        }
      }
    }
  });
}

async function switchChartRange(days, btn) {
  if (!activityChart) return;

  document.querySelectorAll('.chart-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const res  = await fetch(`/api/activity/?days=${days}`);
  const data = await res.json();

  activityChart.data.labels = data.labels.map(d => {
    const dt = new Date(d);
    if (days <= 7) return dt.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    if (days <= 30) return dt.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    return dt.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
  });
  activityChart.data.datasets[0].data = data.issued;
  activityChart.data.datasets[1].data = data.returned;
  activityChart.update('active');
}

function initDashboardGenreChart() {
  const canvas = document.getElementById('dashboardGenreChart');
  if (!canvas) return;

  const rawData = JSON.parse(canvas.dataset.genres || '{}');
  const labels  = Object.keys(rawData);
  const values  = Object.values(rawData);
  
  if (!labels.length) return;

  const colors = [
    '#6366f1','#8b5cf6','#3b82f6','#10b981',
    '#f59e0b','#ec4899','#06b6d4','#f43f5e',
    '#a855f7','#14b8a6'
  ];
  
  const total = values.reduce((a, b) => a + b, 0);

  // Generate Custom Legend
  const legendContainer = document.getElementById('dashboardGenreLegend');
  if (legendContainer) {
    let legendHtml = '';
    labels.forEach((label, i) => {
      const pct = Math.round((values[i] / total) * 100);
      legendHtml += `
        <div style="display:flex; align-items:center; font-size:12px; color:var(--text-secondary);">
          <div style="width:10px; height:10px; border-radius:2px; background:${colors[i]}; margin-right:8px; flex-shrink:0;"></div>
          <span style="flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${label}</span>
          <span style="font-weight:600; color:var(--text-primary); margin-left:4px;">${pct}%</span>
        </div>
      `;
    });
    legendContainer.innerHTML = legendHtml;
  }

  new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, labels.length),
        borderColor: '#ffffff',
        borderWidth: 2,
        hoverOffset: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#ffffff',
          borderColor: 'rgba(0,0,0,0.05)',
          borderWidth: 1,
          titleColor: '#1B254B',
          bodyColor: '#475569',
          padding: 12,
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed} books`
          }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', initCharts);

// ── Report Charts ─────────────────────────────────────────────────────────────

function initReportGenreChart() {
  const canvas = document.getElementById('reportGenreChart');
  if (!canvas) return;

  const rawData = JSON.parse(canvas.dataset.genres || '{}');
  const labels  = Object.keys(rawData);
  const values  = Object.values(rawData);
  if (!labels.length) return;

  const colors = ['#6366f1','#8b5cf6','#3b82f6','#10b981','#f59e0b','#ec4899','#06b6d4','#f43f5e','#a855f7','#14b8a6'];

  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Books',
        data: values,
        backgroundColor: colors.slice(0, labels.length).map(c => c + '99'),
        borderColor: colors.slice(0, labels.length),
        borderWidth: 2,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(13,18,32,0.95)',
          borderColor: 'rgba(255,255,255,0.07)',
          borderWidth: 1,
          titleColor: '#f1f5f9',
          bodyColor: '#94a3b8',
        }
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#475569' } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#475569', stepSize: 1 }, beginAtZero: true }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', initReportGenreChart);

// ── Popularity bars animation ─────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const fill = entry.target;
        fill.style.width = fill.dataset.width;
        observer.unobserve(fill);
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll('.popularity-fill').forEach(el => {
    observer.observe(el);
  });
});

// ── Search live filter ────────────────────────────────────────────────────────

function initSearchPage() {
  const form = document.getElementById('searchForm');
  const input = document.getElementById('searchInput');
  if (!form || !input) return;

  let timer = null;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => form.submit(), 500);
  });
}

document.addEventListener('DOMContentLoaded', initSearchPage);

// ── Print / Export ────────────────────────────────────────────────────────────

function printReport() {
  window.print();
}

function exportReport() {
  const content = document.getElementById('reportContent');
  if (!content) return;
  const text = content.innerText;
  const blob = new Blob([text], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `Library_Report_${new Date().toISOString().slice(0,10)}.txt`;
  a.click();
  URL.revokeObjectURL(a.href);
  showToast('success', 'Report exported', 'Report saved as .txt file');
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

// Animate numbers on dashboard
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.stat-value[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    if (isNaN(target)) return;
    let current = 0;
    const step = Math.max(1, Math.ceil(target / 40));
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      const prefix = el.dataset.prefix || '';
      const suffix = el.dataset.suffix || '';
      el.textContent = prefix + current.toLocaleString('en-IN') + suffix;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
});

// Date auto-fill
document.addEventListener('DOMContentLoaded', () => {
  const today = new Date();
  const dateStr = today.toISOString().slice(0, 10);
  document.querySelectorAll('input[type="date"][data-today]').forEach(el => {
    if (!el.value) el.value = dateStr;
  });
  document.querySelectorAll('input[type="date"][data-due]').forEach(el => {
    if (!el.value) {
      const due = new Date(today);
      due.setDate(due.getDate() + 14);
      el.value = due.toISOString().slice(0, 10);
    }
  });
});

// Renew confirmation
function confirmRenew(issueId, title) {
  if (confirm(`Renew "${title}"? This will extend the due date by 7 days.`)) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/renew/${issueId}/`;
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrf) form.appendChild(csrf.cloneNode());
    document.body.appendChild(form);
    form.submit();
  }
}
