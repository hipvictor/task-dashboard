const SUPABASE_URL = 'https://epdxkvohrclpqnlagkwv.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVwZHhrdm9ocmNscHFubGFna3d2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ3NTA3NDYsImV4cCI6MjA5MDMyNjc0Nn0.l9A8VlNFQw0kWgBLS0Cvo9CU6WEzHZS5OcLmBLz7CDI';

let sb;
try {
  sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
} catch (e) {
  document.getElementById('login-error').textContent = 'Supabase library failed to load: ' + e.message;
}

console.log('Dashboard v18 loaded — quick-tags + save fix');

let allTasks = [];
let openMenu = null;
let currentTheme = 'ember';
let currentFont = 'Inter';
let currentSizeStep = 0; // -2 to +3, where 0 = 100%
let searchQuery = '';
let isOffline = false;
let savingTask = false;

const SIZE_STEPS = [0.85, 0.925, 1, 1.075, 1.15, 1.25];
const SIZE_LABELS = ['85%', '93%', '100%', '108%', '115%', '125%'];
const SIZE_OFFSET = 2; // index of the 100% step

// DEBOUNCE UTILITY
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// TOAST/UNDO SYSTEM
function escapeHTML(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, c => map[c]);
}

function showToast(message, options = {}) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast' + (options.type ? ` ${options.type}` : '');
  let html = `<span>${escapeHTML(message)}</span>`;
  if (options.undo) {
    html += `<button class="toast-undo" onclick="this.parentElement._undoFn(); this.parentElement.remove()">Undo</button>`;
  }
  toast.innerHTML = html;
  if (options.undo) {
    toast._undoFn = options.undo;
  }
  container.appendChild(toast);
  const duration = options.duration || (options.undo ? 6000 : 3000);
  setTimeout(() => {
    toast.classList.add('dismissing');
    setTimeout(() => toast.remove(), 300);
  }, duration);
  return toast;
}

// ONLINE STATUS DETECTION
function updateOnlineStatus() {
  isOffline = !navigator.onLine;
  const banner = document.getElementById('offline-banner');
  if (banner) banner.classList.toggle('visible', isOffline);
}

window.addEventListener('online', () => {
  updateOnlineStatus();
  showToast('Back online', { type: 'success' });
  loadTasks();
  loadAgenda();
});

window.addEventListener('offline', () => {
  updateOnlineStatus();
  showToast("You're offline — changes may not save", { type: 'error', duration: 5000 });
});

document.addEventListener('DOMContentLoaded', updateOnlineStatus);

// KEYBOARD SHORTCUTS
let shortcutHelpVisible = false;

function toggleShortcutHelp() {
  shortcutHelpVisible = !shortcutHelpVisible;
  const overlay = document.getElementById('shortcut-help-overlay');
  if (overlay) {
    overlay.classList.toggle('visible', shortcutHelpVisible);
  }
}

function hideShortcutHelp() {
  shortcutHelpVisible = false;
  const overlay = document.getElementById('shortcut-help-overlay');
  if (overlay) {
    overlay.classList.remove('visible');
  }
}

function isInputElement(el) {
  return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT');
}

document.addEventListener('keydown', (e) => {
  const target = e.target;
  
  // Close modals/overlays on Escape
  if (e.key === 'Escape') {
    hideShortcutHelp();
    hideSearch();
    const dropdowns = document.querySelectorAll('[id$="-dropdown"].open');
    dropdowns.forEach(dd => dd.classList.remove('open'));
    return;
  }
  
  // Don't trigger shortcuts when typing in inputs
  if (isInputElement(target)) return;
  
  if (e.key === '?') {
    e.preventDefault();
    toggleShortcutHelp();
  } else if (e.key === 'n') {
    e.preventDefault();
    const quickAdd = document.getElementById('quick-add-input');
    if (quickAdd) quickAdd.focus();
  } else if (e.key === '/') {
    e.preventDefault();
    toggleSearch();
  } else if (e.key >= '1' && e.key <= '4') {
    e.preventDefault();
    const tabNum = parseInt(e.key) - 1;
    const tabBtns = document.querySelectorAll('[data-tab-id]');
    if (tabNum < tabBtns.length) {
      const tabId = tabBtns[tabNum].getAttribute('data-tab-id');
      switchTab(tabId);
    }
  }
});

// SEARCH/FILTER
function toggleSearch() {
  const bar = document.getElementById('search-bar');
  const input = document.getElementById('search-input');
  if (bar.classList.contains('visible')) {
    hideSearch();
  } else {
    bar.classList.add('visible');
    input.focus();
  }
}

function hideSearch() {
  document.getElementById('search-bar').classList.remove('visible');
  document.getElementById('search-input').value = '';
  searchQuery = '';
  renderTasks();
}

const handleSearchInput = debounce((value) => {
  searchQuery = value.toLowerCase().trim();
  renderTasks();
}, 200);

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    currentTheme = theme;
    document.querySelectorAll('.theme-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.theme-btn.${theme}`)?.classList.add('active');
    try { localStorage.setItem('dash-theme', theme); } catch(e) {}
  }

  function setFont(font) {
    const fallback = font.includes('Serif') || font.includes('Baskerville') ? ', serif' : ', -apple-system, system-ui, sans-serif';
    document.documentElement.style.setProperty('--font', `'${font}'${fallback}`);
    currentFont = font;
    document.querySelectorAll('.font-option').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.font === font);
    });
    try { localStorage.setItem('dash-font', font); } catch(e) {}
  }

  function adjustSize(direction) {
    const idx = currentSizeStep + SIZE_OFFSET + direction;
    if (idx < 0 || idx >= SIZE_STEPS.length) return;
    currentSizeStep += direction;
    applySizeScale();
    try { localStorage.setItem('dash-size-step', currentSizeStep); } catch(e) {}
  }

  function applySizeScale() {
    const idx = currentSizeStep + SIZE_OFFSET;
    document.documentElement.style.setProperty('--size-scale', SIZE_STEPS[idx]);
    const label = document.getElementById('size-label');
    if (label) label.textContent = SIZE_LABELS[idx];
  }

  // Restore saved preferences on load
  (function restorePrefs() {
    try {
      const savedTheme = localStorage.getItem('dash-theme');
      if (savedTheme) setTheme(savedTheme);
      const savedFont = localStorage.getItem('dash-font');
      if (savedFont) setFont(savedFont);
      const savedSize = localStorage.getItem('dash-size-step');
      if (savedSize !== null) {
        currentSizeStep = parseInt(savedSize, 10) || 0;
        applySizeScale();
      }
    } catch(e) {}
  })();

  function toggleSettings(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('settings-dropdown');
    dropdown.classList.toggle('open');
  }

  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('settings-dropdown');
    if (dropdown && !e.target.closest('.settings-wrap')) {
      dropdown.classList.remove('open');
    }
  });

  async function checkAuth() {
    if (!sb) {
      document.getElementById('login-screen').style.display = 'flex';
      return;
    }
    try {
      const { data: { session } } = await sb.auth.getSession();
      if (session) {
        showDashboard();
      } else {
        document.getElementById('login-screen').style.display = 'flex';
      }
    } catch (e) {
      document.getElementById('login-screen').style.display = 'flex';
      document.getElementById('login-error').textContent = 'Auth check failed: ' + e.message;
    }
  }

  async function handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');

    if (!sb) {
      errorEl.textContent = 'Supabase not loaded. Refresh the page.';
      return;
    }
    errorEl.textContent = 'Signing in...';

    try {
      const { data, error } = await sb.auth.signInWithPassword({ email, password });
      if (error) {
        errorEl.textContent = error.message;
      } else if (data && data.session) {
        showDashboard();
      } else {
        errorEl.textContent = 'No session returned. Check Supabase config.';
      }
    } catch (e) {
      errorEl.textContent = 'Error: ' + e.message;
    }
  }

  async function handleLogout() {
    await sb.auth.signOut();
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('login-screen').style.display = 'flex';
  }

  async function showDashboard() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('dashboard').style.display = 'block';

    const now = new Date();
    const opts = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' };
    document.getElementById('header-date').textContent = now.toLocaleDateString('en-US', opts);

    await surfaceDeferredTasks();
    await loadTasks();
    await loadAgenda();
    renderCoachingCard();
  }

  // ── View Switching ──
  function switchView(viewName) {
    // Hide all views
    document.getElementById('tasks-view').classList.remove('active');
    document.getElementById('people-view').classList.remove('active');
    document.getElementById('threads-view').classList.remove('active');
    document.getElementById('briefing-view').classList.remove('active');

    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    // Show selected view and activate tab
    if (viewName === 'tasks') {
      document.getElementById('tasks-view').classList.add('active');
      document.querySelectorAll('.tab-btn')[0].classList.add('active');
    } else if (viewName === 'people') {
      document.getElementById('people-view').classList.add('active');
      document.querySelectorAll('.tab-btn')[1].classList.add('active');
      loadPeople();
    } else if (viewName === 'threads') {
      document.getElementById('threads-view').classList.add('active');
      document.querySelectorAll('.tab-btn')[2].classList.add('active');
      loadThreads();
    } else if (viewName === 'briefing') {
      document.getElementById('briefing-view').classList.add('active');
      document.querySelectorAll('.tab-btn')[3].classList.add('active');
      loadBriefing();
    }
  }

  // ── People View ──
  let peopleCache = null;
  let interactionsCache = null;

  async function loadPeople() {
    if (peopleCache && interactionsCache) {
      renderPeople();
      return;
    }

    try {
      // Load people
      const { data: people, error: peopleErr } = await sb.from('people').select('*').order('canonical_name');
      if (peopleErr) throw peopleErr;

      // Load interactions from last 30 days
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      const { data: interactions, error: interErr } = await sb
        .from('interactions')
        .select('person_id, interaction_date, summary, signal_weight')
        .gte('interaction_date', thirtyDaysAgo.toISOString());
      if (interErr) throw interErr;

      peopleCache = people || [];
      interactionsCache = interactions || [];
      renderPeople();
    } catch (e) {
      console.error('Error loading people:', e);
      document.getElementById('people-list').innerHTML = '<div class="thread-empty">Error loading people</div>';
    }
  }

  function renderPeople() {
    const filter = document.getElementById('people-role-filter').value;
    const container = document.getElementById('people-list');

    // Aggregate interactions by person
    const interactionsByPerson = {};
    (interactionsCache || []).forEach(inter => {
      if (!interactionsByPerson[inter.person_id]) {
        interactionsByPerson[inter.person_id] = { count: 0, recent: [] };
      }
      interactionsByPerson[inter.person_id].count++;
      if (interactionsByPerson[inter.person_id].recent.length < 2) {
        interactionsByPerson[inter.person_id].recent.push(inter.summary);
      }
    });

    // Filter and sort people
    let filteredPeople = (peopleCache || []).filter(p => {
      if (filter === 'all') return true;
      return p.role === filter;
    });

    filteredPeople.sort((a, b) => {
      const aCount = interactionsByPerson[a.id]?.count || 0;
      const bCount = interactionsByPerson[b.id]?.count || 0;
      if (bCount !== aCount) return bCount - aCount;
      return a.canonical_name.localeCompare(b.canonical_name);
    });

    if (filteredPeople.length === 0) {
      container.innerHTML = '<div class="thread-empty">No people found</div>';
      return;
    }

    container.innerHTML = filteredPeople.map(person => {
      const interData = interactionsByPerson[person.id];
      const count = interData?.count || 0;
      const recentSummaries = (interData?.recent || []).filter(Boolean);

      return `
        <div class="people-card">
          <div class="person-header">
            <div class="person-name">${escapeHTML(person.name || person.canonical_name)}</div>
            <span class="person-star ${person.starred ? 'starred' : ''}" onclick="togglePersonStar('${person.id}')">⭐</span>
          </div>
          <span class="role-badge ${person.role}">${escapeHTML(person.role)}</span>
          ${person.email ? `<div class="person-contact"><a href="mailto:${escapeHTML(person.email)}">${escapeHTML(person.email)}</a></div>` : ''}
          ${person.phone ? `<div class="person-contact">${escapeHTML(person.phone)}</div>` : ''}
          <div class="person-stats">
            <span>${count} interactions (30d)</span>
          </div>
          ${recentSummaries.length > 0 ? `<div class="person-interactions"><strong>Recent:</strong> ${recentSummaries.map(s => escapeHTML(s)).join(', ')}</div>` : ''}
        </div>
      `;
    }).join('');
  }

  function togglePersonStar(personId) {
    // Update UI
    const cards = document.querySelectorAll('.people-card');
    cards.forEach(card => {
      if (card.querySelector('.person-star').onclick.toString().includes(personId)) {
        const star = card.querySelector('.person-star');
        star.classList.toggle('starred');
      }
    });

    // Update DB
    const person = peopleCache.find(p => p.id === personId);
    if (person) {
      person.starred = !person.starred;
      sb.from('people').update({ starred: person.starred }).eq('id', personId).catch(e => console.error('Error updating star:', e));
    }
  }

  // ── Threads View ──
  let threadsCache = null;

  async function loadThreads() {
    if (threadsCache) {
      renderThreads();
      return;
    }

    try {
      const { data, error } = await sb.rpc('thread_health');
      if (error) throw error;
      threadsCache = data || [];
      renderThreads();
    } catch (e) {
      console.error('Error loading threads:', e);
      document.getElementById('threads-grid').innerHTML = '<div class="thread-empty">Error loading threads</div>';
    }
  }

  function renderThreads() {
    const threads = threadsCache || [];

    // Count health statuses
    const active = threads.filter(t => t.health === 'active').length;
    const cooling = threads.filter(t => t.health === 'cooling').length;
    const cold = threads.filter(t => t.health === 'cold').length;

    document.getElementById('threads-summary').innerHTML = `
      <div class="threads-summary-item">
        <span class="status-dot active"></span>
        <span>${active} Active</span>
      </div>
      <div class="threads-summary-item">
        <span class="status-dot cooling"></span>
        <span>${cooling} Cooling</span>
      </div>
      <div class="threads-summary-item">
        <span class="status-dot cold"></span>
        <span>${cold} Cold</span>
      </div>
    `;

    // Sort: starred first, then by health, then by last activity
    const healthOrder = { active: 0, cooling: 1, cold: 2 };
    threads.sort((a, b) => {
      if (b.starred !== a.starred) return b.starred ? 1 : -1;
      if (healthOrder[a.health] !== healthOrder[b.health]) {
        return healthOrder[a.health] - healthOrder[b.health];
      }
      return new Date(b.last_activity || 0) - new Date(a.last_activity || 0);
    });

    const container = document.getElementById('threads-grid');
    if (threads.length === 0) {
      container.innerHTML = '<div class="thread-empty">No threads found</div>';
      return;
    }

    container.innerHTML = threads.map(thread => {
      const daysSince = thread.last_activity
        ? Math.floor((Date.now() - new Date(thread.last_activity)) / (1000 * 60 * 60 * 24))
        : null;
      const daysLabel = daysSince === null ? 'No activity' : `${daysSince} day${daysSince !== 1 ? 's' : ''} ago`;

      return `
        <div class="thread-card">
          <div class="thread-header">
            <div class="thread-name">${escapeHTML(thread.display_name)}</div>
            <span class="thread-star ${thread.starred ? 'starred' : ''}" onclick="toggleThreadStar('${thread.id}')">⭐</span>
          </div>
          <div class="thread-health">
            <span class="status-dot ${thread.health}"></span>
            <span>${thread.health}</span>
          </div>
          <div class="thread-stats">
            <span>${thread.interaction_count_30d} interactions (30d)</span>
            <span>${daysLabel}</span>
          </div>
        </div>
      `;
    }).join('');
  }

  function toggleThreadStar(threadId) {
    // Update UI
    const cards = document.querySelectorAll('.thread-card');
    cards.forEach(card => {
      if (card.querySelector('.thread-star').onclick.toString().includes(threadId)) {
        const star = card.querySelector('.thread-star');
        star.classList.toggle('starred');
      }
    });

    // Update DB
    const thread = threadsCache.find(t => t.id === threadId);
    if (thread) {
      thread.starred = !thread.starred;
      sb.from('threads').update({ starred: thread.starred }).eq('id', threadId).catch(e => console.error('Error updating star:', e));
    }
  }


  let briefingCache = null;

  async function loadBriefing() {
    const content = document.getElementById('briefing-content');

    if (briefingCache) {
      content.innerHTML = briefingCache;
      return;
    }

    content.innerHTML = '<div class="briefing-loading">Loading briefing...</div>';

    try {
      // Fetch the latest briefing HTML from the briefings table
      const todayStr = new Date().toISOString().split('T')[0];

      // Try today first, then fall back to most recent briefing
      let { data: briefing, error } = await sb.from('briefings')
        .select('html_content, briefing_date')
        .eq('briefing_date', todayStr)
        .single();

      if (error || !briefing) {
        // Fall back to most recent briefing
        const { data: recent, error: recentErr } = await sb.from('briefings')
          .select('html_content, briefing_date')
          .order('briefing_date', { ascending: false })
          .limit(1)
          .single();

        if (recentErr || !recent) throw new Error('No briefings found');
        briefing = recent;
      }

      // Set the date header
      const bDate = new Date(briefing.briefing_date + 'T12:00:00');
      const dateOpts = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' };
      document.getElementById('briefing-date').textContent = bDate.toLocaleDateString('en-US', dateOpts);

      // If viewing a past briefing, show a notice
      let staleNotice = '';
      if (briefing.briefing_date !== todayStr) {
        staleNotice = `<div style="background: var(--surface); border-left: 3px solid var(--accent); padding: 0.75rem 1rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--text-muted); border-radius: 4px;">Showing briefing from ${bDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}. Today's briefing hasn't been generated yet.</div>`;
      }

      briefingCache = staleNotice + briefing.html_content;
      content.innerHTML = briefingCache;
    } catch (e) {
      console.error('Error loading briefing:', e);
      content.innerHTML = '<div class="briefing-loading" style="color: var(--danger);">No briefing available yet. The morning briefing will appear here once generated.</div>';
    }
  }

  // renderBriefing removed — briefing HTML is pre-built and stored in briefings table

  async function surfaceDeferredTasks() {
    try {
      await sb.rpc('surface_deferred_tasks');
    } catch (e) {
      console.log('Surfacing check:', e);
    }
  }

  async function loadTasks() {
    const { data, error } = await sb
      .from('tasks')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      console.error('Error loading tasks:', error);
      return;
    }

    allTasks = data || [];
    populateProjectFilter();
    renderTasks();
    renderAlerts();
  }

  function populateProjectFilter() {
    const select = document.getElementById('filter-project');
    const projects = [...new Set(allTasks.filter(t => t.project).map(t => t.project))].sort();
    select.innerHTML = '<option value="all">All projects</option>';
    projects.forEach(p => {
      select.innerHTML += `<option value="${p}">${p}</option>`;
    });

    const tagSelect = document.getElementById('filter-tag');
    const tags = [...new Set(allTasks.filter(t => t.tags && t.tags.length).flatMap(t => t.tags))].sort();
    tagSelect.innerHTML = '<option value="all">All tags</option>';
    tags.forEach(tag => {
      tagSelect.innerHTML += `<option value="${tag}">${tag}</option>`;
    });
  }

  function getFilteredTasks(status) {
    const domain = document.getElementById('filter-domain').value;
    const project = document.getElementById('filter-project').value;
    const tag = document.getElementById('filter-tag').value;

    return allTasks.filter(t => {
      if (t.status !== status) return false;
      if (domain !== 'all' && t.domain !== domain) return false;
      if (project !== 'all' && t.project !== project) return false;
      if (tag !== 'all' && (!t.tags || !t.tags.includes(tag))) return false;

      // Search filtering
      if (searchQuery) {
        const q = searchQuery;
        const matchesName = t.name && t.name.toLowerCase().includes(q);
        const matchesTags = t.tags && t.tags.some(tag => tag.toLowerCase().includes(q));
        const matchesProject = t.project && t.project.toLowerCase().includes(q);
        const matchesNotes = t.capture_notes && t.capture_notes.toLowerCase().includes(q);
        const matchesDelegated = t.delegated_to && t.delegated_to.toLowerCase().includes(q);
        if (!matchesName && !matchesTags && !matchesProject && !matchesNotes && !matchesDelegated) return false;
      }

      return true;
    });
  }

  let delegateTagFilter = null;

  function renderTasks() {
    const bench = getFilteredTasks('bench');
    const inbox = getFilteredTasks('inbox');
    const shelf = getFilteredTasks('shelf');
    const someday = getFilteredTasks('someday');
    let delegate = getFilteredTasks('delegate');
    const deferred = getFilteredTasks('deferred')
      .sort((a, b) => {
        if (!a.defer_date) return 1;
        if (!b.defer_date) return -1;
        return new Date(a.defer_date) - new Date(b.defer_date);
      });
    const done = allTasks
      .filter(t => t.status === 'done' && t.completed_at)
      .sort((a, b) => new Date(b.completed_at) - new Date(a.completed_at))
      .slice(0, 5);

    // Delegate tag filter bar
    renderDelegateFilterBar(delegate);
    if (delegateTagFilter) {
      delegate = delegate.filter(t => {
        const taskTags = (t.tags || []).map(tag => tag.toLowerCase());
        const delegatedTo = (t.delegated_to || '').toLowerCase();
        const filterLower = delegateTagFilter.toLowerCase();
        return taskTags.includes(filterLower) || delegatedTo === filterLower;
      });
    }

    document.getElementById('bench-tasks').innerHTML = bench.map(t => taskHTML(t)).join('');
    document.getElementById('inbox-tasks').innerHTML = inbox.map(t => taskHTML(t)).join('');
    document.getElementById('shelf-tasks').innerHTML = shelf.map(t => taskHTML(t)).join('');
    document.getElementById('someday-tasks').innerHTML = someday.map(t => taskHTML(t)).join('');
    document.getElementById('delegate-tasks').innerHTML = delegate.map(t => taskHTML(t)).join('');
    document.getElementById('deferred-tasks').innerHTML = deferred.map(t => taskHTML(t)).join('');
    document.getElementById('done-tasks').innerHTML = done.map(t => taskHTML(t, true)).join('');

    document.getElementById('bench-count').textContent = bench.length;
    document.getElementById('inbox-count').textContent = inbox.length;
    document.getElementById('shelf-count').textContent = shelf.length;
    document.getElementById('someday-count').textContent = someday.length;
    document.getElementById('delegate-count').textContent = delegate.length + (delegateTagFilter ? '/' + getFilteredTasks('delegate').length : '');
    document.getElementById('deferred-count').textContent = deferred.length;
  }

  function renderDelegateFilterBar(delegateTasks) {
    const bar = document.getElementById('delegate-filter-bar');
    if (!bar) return;

    // Collect all unique tags/people from delegate tasks
    const tagSet = new Set();
    delegateTasks.forEach(t => {
      if (t.delegated_to) tagSet.add(t.delegated_to);
      (t.tags || []).forEach(tag => tagSet.add(tag));
    });

    if (tagSet.size === 0) { bar.innerHTML = ''; return; }

    const sortedTags = [...tagSet].sort();
    let html = `<button class="delegate-tag-btn ${!delegateTagFilter ? 'active' : ''}" onclick="setDelegateFilter(null)">All</button>`;
    sortedTags.forEach(tag => {
      const isActive = delegateTagFilter && delegateTagFilter.toLowerCase() === tag.toLowerCase();
      html += `<button class="delegate-tag-btn ${isActive ? 'active' : ''}" onclick="setDelegateFilter('${escapeHTML(tag)}')">${escapeHTML(tag)}</button>`;
    });
    bar.innerHTML = html;
  }

  function setDelegateFilter(tag) {
    delegateTagFilter = (delegateTagFilter === tag) ? null : tag;
    renderTasks();
  }

  function taskHTML(task, isDone = false) {
    const checked = isDone ? 'checked' : '';
    const completedClass = isDone ? 'completed' : '';
    const tags = [];

    if (task.project) tags.push(`<span class="tag project">${task.project}</span>`);
    if (task.domain === 'home') tags.push('<span class="tag home">home</span>');
    if (task.tags && task.tags.length) {
      task.tags.forEach(t => tags.push(`<span class="tag">${t}</span>`));
    }
    if (task.due_date) {
      const days = daysUntil(task.due_date);
      if (days < 0) tags.push(`<span class="tag overdue">overdue ${Math.abs(days)}d</span>`);
      else if (days <= 3) tags.push(`<span class="tag due">due in ${days}d</span>`);
      else tags.push(`<span class="tag due">due ${formatDate(task.due_date)}</span>`);
    }
    if (task.status === 'deferred' && task.defer_date) {
      const dDays = daysUntil(task.defer_date);
      if (dDays <= 0) tags.push(`<span class="tag overdue">surfaces today</span>`);
      else if (dDays === 1) tags.push(`<span class="tag">surfaces tomorrow</span>`);
      else tags.push(`<span class="tag">surfaces in ${dDays}d</span>`);
    }

    const moveOptions = isDone ? '' : `
      <div class="task-actions-wrap">
        <button class="task-action-btn" onclick="toggleMoveMenu(event, '${task.id}')">⋯</button>
        <div class="move-menu" id="menu-${task.id}" style="display:none">
          ${task.status !== 'bench' ? `<button onclick="moveTask('${task.id}','bench')">→ Bench</button>` : ''}
          ${task.status !== 'shelf' ? `<button onclick="moveTask('${task.id}','shelf')">→ Shelf</button>` : ''}
          ${task.status !== 'delegate' ? `<button onclick="moveTask('${task.id}','delegate')">→ Delegate</button>` : ''}
          ${task.status !== 'deferred' ? `<button onclick="moveTask('${task.id}','deferred')">→ Deferred</button>` : `<button onclick="rescheduleTask('${task.id}')">Reschedule</button>`}
          ${task.status !== 'someday' ? `<button onclick="moveTask('${task.id}','someday')">→ Someday</button>` : ''}
          <button onclick="deleteTask('${task.id}')" style="color:var(--danger)">Delete</button>
        </div>
      </div>
    `;

    const dragAttrs = isDone ? '' : `draggable="true" ondragstart="onDragStart(event, '${task.id}', '${task.status}')" ondragend="onDragEnd(event)"`;
    const dragHandle = isDone ? '' : `<div class="drag-handle" title="Drag to move" ontouchstart="onTouchDragStart(event, '${task.id}', '${task.status}')" ontouchmove="onTouchDragMove(event)" ontouchend="onTouchDragEnd(event)">⠿</div>`;

    // Notes preview (capture_notes)
    const notesPreview = task.capture_notes && task.capture_notes !== task.name
      ? `<div class="task-notes" onclick="openTaskEditor('${task.id}', event)" title="Click to edit notes">${escapeHTML(task.capture_notes.substring(0, 120))}${task.capture_notes.length > 120 ? '…' : ''}</div>`
      : '';

    // Delegated-to badge
    const delegatedBadge = task.delegated_to
      ? `<span class="tag delegated">→ ${escapeHTML(task.delegated_to)}</span>`
      : '';

    return `
      <div class="task" data-id="${task.id}" ${dragAttrs} onclick="toggleTaskSelection(event, '${task.id}')">
        ${dragHandle}
        <div class="task-checkbox ${checked}" onclick="if(!selectMode){event.stopPropagation();toggleComplete('${task.id}', ${isDone})}"></div>
        <div class="task-content">
          <div class="task-name ${completedClass}" ${isDone ? '' : `onclick="openTaskEditor('${task.id}', event)"`} style="${isDone ? '' : 'cursor:pointer'}" title="${isDone ? '' : 'Click to edit'}">${escapeHTML(task.name)}</div>
          ${tags.length || delegatedBadge ? `<div class="task-meta">${delegatedBadge}${tags.join('')}</div>` : ''}
          ${notesPreview}
        </div>
        ${moveOptions}
      </div>
    `;
  }

  function getDismissedAlerts() {
    try {
      const stored = localStorage.getItem('dismissed-alerts');
      if (!stored) return {};
      const parsed = JSON.parse(stored);
      const today = new Date().toISOString().split('T')[0];
      // Only keep dismissals from today — everything else reappears
      const filtered = {};
      for (const [key, date] of Object.entries(parsed)) {
        if (date === today) filtered[key] = date;
      }
      return filtered;
    } catch { return {}; }
  }

  function dismissAlert(key, el) {
    el.classList.add('dismissing');
    const dismissed = getDismissedAlerts();
    dismissed[key] = new Date().toISOString().split('T')[0];
    localStorage.setItem('dismissed-alerts', JSON.stringify(dismissed));
    setTimeout(() => el.remove(), 300);
  }

  function renderAlerts() {
    const bar = document.getElementById('alerts-bar');
    const alerts = [];
    const dismissed = getDismissedAlerts();

    allTasks.forEach(t => {
      if (t.status === 'done') return;
      if (t.due_date) {
        const days = daysUntil(t.due_date);
        if (days < 0) {
          alerts.push({ type: 'overdue', key: `overdue-${t.id}`, text: `Overdue: ${t.name} (${Math.abs(days)} days ago)` });
        } else if (days <= 3) {
          alerts.push({ type: 'due-soon', key: `due-${t.id}`, text: `Due ${days === 0 ? 'today' : `in ${days} day${days > 1 ? 's' : ''}`}: ${t.name}` });
        }
      }
      if (t.status === 'shelf' && t.defer_date) {
        const deferDays = daysUntil(t.defer_date);
        if (deferDays >= -1 && deferDays <= 7) {
          alerts.push({ type: 'surfaced', key: `deferred-${t.id}`, text: deferDays > 0
            ? `${t.name} begins in ${deferDays} day${deferDays > 1 ? 's' : ''}`
            : `${t.name} starts today. Move to bench?` });
        }
      }
      // Approaching: deferred tasks with lead_time_days > 0 where defer_date - lead_time_days <= today
      if (t.status === 'deferred' && t.defer_date && t.lead_time_days > 0) {
        const deferDays = daysUntil(t.defer_date);
        if (deferDays > 0 && deferDays <= t.lead_time_days) {
          alerts.push({ type: 'approaching', key: `approaching-${t.id}`, text: `${t.name} starts in ${deferDays} day${deferDays !== 1 ? 's' : ''}` });
        }
      }
    });

    const visible = alerts.filter(a => !dismissed[a.key]);

    const alertEmoji = { overdue: '🔴', 'due-soon': '🟡', surfaced: '🔵', approaching: '🟦' };
    bar.innerHTML = visible.map(a =>
      `<div class="alert alert-${a.type}">
        <span>${alertEmoji[a.type] || '🔵'} ${escapeHTML(a.text)}</span>
        <button class="alert-dismiss" onclick="dismissAlert('${a.key}', this.closest('.alert'))" title="Dismiss for today">✕</button>
      </div>`
    ).join('');
  }

  async function toggleComplete(id, wasDone) {
    const newStatus = wasDone ? 'shelf' : 'done';
    const task = allTasks.find(t => t.id === id);
    if (!task) return;

    // Store previous state for undo
    const previousTasks = JSON.parse(JSON.stringify(allTasks));

    // Optimistic UI: update immediately
    const idx = allTasks.findIndex(t => t.id === id);
    if (idx !== -1) {
      allTasks[idx].status = newStatus;
    }
    renderTasks();

    const action = newStatus === 'done' ? 'completed' : 'uncompleted';
    const oldStatus = task.status === newStatus ? (wasDone ? 'done' : 'shelf') : task.status;
    showToast(`Task ${action}`, {
      undo: async () => {
        allTasks = previousTasks;
        renderTasks();
        await sb.from('tasks').update({ status: oldStatus, completed_at: null }).eq('id', id);
      }
    });

    try {
      const { error } = await sb
        .from('tasks')
        .update({ status: newStatus, ...(newStatus === 'done' ? { completed_at: new Date().toISOString() } : {}) })
        .eq('id', id);

      if (error) {
        allTasks = previousTasks;
        renderTasks();
        showToast(`Error: ${error.message}`, { type: 'error' });
      }
    } catch (e) {
      allTasks = previousTasks;
      renderTasks();
      showToast(`Error: ${e.message}`, { type: 'error' });
    }
  }

  let pendingDeferTaskId = null;
  let selectMode = false;
  let selectedTaskIds = new Set();
  let pendingBatchDefer = false;

  async function moveTask(id, newStatus) {
    closeAllMenus();
    if (newStatus === 'deferred') {
      pendingDeferTaskId = id;
      showDeferModal();
      return;
    }
    
    const task = allTasks.find(t => t.id === id);
    if (!task) return;
    const previousTasks = JSON.parse(JSON.stringify(allTasks));
    
    // Optimistic UI: update immediately
    const idx = allTasks.findIndex(t => t.id === id);
    if (idx !== -1) {
      allTasks[idx].status = newStatus;
      if (newStatus !== 'deferred') {
        allTasks[idx].defer_date = null;
      }
    }
    renderTasks();

    const oldStatus = task.status;
    const oldDeferDate = task.defer_date;
    showToast(`Task moved to ${newStatus}`, {
      undo: async () => {
        allTasks = previousTasks;
        renderTasks();
        await sb.from('tasks').update({ status: oldStatus, defer_date: oldDeferDate }).eq('id', id);
      }
    });

    try {
      const update = { status: newStatus };
      if (newStatus !== 'deferred') update.defer_date = null;
      const { error } = await sb
        .from('tasks')
        .update(update)
        .eq('id', id);

      if (error) {
        allTasks = previousTasks;
        renderTasks();
        showToast(`Error: ${error.message}`, { type: 'error' });
      }
    } catch (e) {
      allTasks = previousTasks;
      renderTasks();
      showToast(`Error: ${e.message}`, { type: 'error' });
    }
  }

  function showDeferModal() {
    const modal = document.getElementById('defer-modal-overlay');
    const input = document.getElementById('defer-date-input');
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    input.value = tomorrow.toISOString().split('T')[0];
    input.min = new Date().toISOString().split('T')[0];
    modal.classList.add('active');
  }

  function closeDeferModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('defer-modal-overlay').classList.remove('active');
    pendingDeferTaskId = null;
    pendingBatchDefer = false;
  }

  function setDeferDate(shortcut) {
    const input = document.getElementById('defer-date-input');
    const d = new Date();
    switch (shortcut) {
      case 'tomorrow': d.setDate(d.getDate() + 1); break;
      case 'next-week': d.setDate(d.getDate() + (9 - d.getDay()) % 7 || 7); break;
      case '2-weeks': d.setDate(d.getDate() + 14); break;
      case 'next-month': d.setMonth(d.getMonth() + 1); d.setDate(1); break;
    }
    input.value = d.toISOString().split('T')[0];
  }

  function rescheduleTask(id) {
    closeAllMenus();
    pendingDeferTaskId = id;
    const task = allTasks.find(t => t.id === id);
    const modal = document.getElementById('defer-modal-overlay');
    const input = document.getElementById('defer-date-input');
    if (task && task.defer_date) {
      input.value = task.defer_date;
    } else {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      input.value = tomorrow.toISOString().split('T')[0];
    }
    input.min = new Date().toISOString().split('T')[0];
    modal.classList.add('active');
  }

  async function confirmDefer() {
    const deferDate = document.getElementById('defer-date-input').value;
    if (!deferDate) return;

    // Batch defer mode
    if (pendingDeferTaskId === '__batch__' && selectedTaskIds.size > 0) {
      const ids = [...selectedTaskIds];
      const { error } = await sb
        .from('tasks')
        .update({ status: 'deferred', defer_date: deferDate })
        .in('id', ids);

      document.getElementById('defer-modal-overlay').classList.remove('active');
      pendingDeferTaskId = null;
      pendingBatchDefer = false;
      if (!error) {
        toggleSelectMode();
        await loadTasks();
      }
      return;
    }

    // Single task defer
    if (!pendingDeferTaskId) return;
    const { error } = await sb
      .from('tasks')
      .update({ status: 'deferred', defer_date: deferDate })
      .eq('id', pendingDeferTaskId);

    document.getElementById('defer-modal-overlay').classList.remove('active');
    pendingDeferTaskId = null;
    if (!error) await loadTasks();
  }

  // — Multi-select / Batch mode —
  function toggleSelectMode() {
    selectMode = !selectMode;
    selectedTaskIds.clear();
    pendingBatchDefer = false;
    document.body.classList.toggle('select-mode', selectMode);
    document.getElementById('select-toggle').classList.toggle('active', selectMode);
    document.getElementById('select-toggle').textContent = selectMode ? 'Selecting...' : 'Select';
    updateBatchBar();
    // Remove all selected highlights
    document.querySelectorAll('.task.selected').forEach(el => el.classList.remove('selected'));
  }

  function toggleTaskSelection(event, id) {
    if (!selectMode) return;
    event.stopPropagation();
    const taskEl = event.currentTarget;
    if (selectedTaskIds.has(id)) {
      selectedTaskIds.delete(id);
      taskEl.classList.remove('selected');
    } else {
      selectedTaskIds.add(id);
      taskEl.classList.add('selected');
    }
    updateBatchBar();
  }

  function updateBatchBar() {
    const bar = document.getElementById('batch-bar');
    const count = document.getElementById('batch-count');
    if (selectMode && selectedTaskIds.size > 0) {
      bar.classList.add('active');
      count.textContent = `${selectedTaskIds.size} selected`;
    } else {
      bar.classList.remove('active');
    }
  }

  async function batchMove(targetStatus) {
    if (selectedTaskIds.size === 0) return;

    if (targetStatus === 'deferred') {
      pendingBatchDefer = true;
      pendingDeferTaskId = '__batch__';
      showDeferModal();
      return;
    }

    const ids = [...selectedTaskIds];
    const update = { status: targetStatus };
    if (targetStatus === 'done') update.completed_at = new Date().toISOString();

    const { error } = await sb
      .from('tasks')
      .update(update)
      .in('id', ids);

    if (!error) {
      toggleSelectMode();
      await loadTasks();
    }
  }

  async function deleteTask(id) {
    closeAllMenus();
    const task = allTasks.find(t => t.id === id);
    if (!task) return;

    // Store previous state for undo
    const previousTasks = JSON.parse(JSON.stringify(allTasks));

    // Optimistic UI: remove immediately
    allTasks = allTasks.filter(t => t.id !== id);
    renderTasks();

    const taskCopy = JSON.parse(JSON.stringify(task));
    showToast('Task deleted', {
      undo: async () => {
        allTasks = previousTasks;
        renderTasks();
        // Re-insert into server
        const { id: _, ...insertData } = taskCopy;
        await sb.from('tasks').insert({ ...insertData, id: taskCopy.id });
      }
    });

    try {
      const { error } = await sb
        .from('tasks')
        .delete()
        .eq('id', id);

      if (error) {
        allTasks = previousTasks;
        renderTasks();
        showToast(`Error: ${error.message}`, { type: 'error' });
      }
    } catch (e) {
      allTasks = previousTasks;
      renderTasks();
      showToast(`Error: ${e.message}`, { type: 'error' });
    }
  }

  // — Inline task editing —
  let editingTaskId = null;

  // Quick-tag system — builds clickable tag buttons from common tags + staff names
  const STAFF_TAGS = ['Cathy', 'Judy', 'Aaron', 'Jenny', 'Rebecca', 'Terri', 'Dylan'];
  const AREA_TAGS = ['worship', 'finance', 'pastoral', 'operations', 'staff', 'lb', 'gff', 'congregation', 'tech', 'sermon'];

  function getCommonTags() {
    // Gather all tags used across tasks, count frequency
    const freq = {};
    allTasks.forEach(t => {
      if (t.tags && t.tags.length) {
        t.tags.forEach(tag => {
          const key = tag.trim();
          if (key) freq[key] = (freq[key] || 0) + 1;
        });
      }
    });
    // Merge staff + area defaults (ensure they're always shown), then add any frequent ones
    const defaults = new Set([...STAFF_TAGS, ...AREA_TAGS]);
    // Add any tag used 3+ times that isn't already in defaults
    Object.entries(freq).forEach(([tag, count]) => {
      if (count >= 3) defaults.add(tag);
    });
    // Sort: staff first, then areas, then others alphabetically
    const staffSet = new Set(STAFF_TAGS.map(s => s.toLowerCase()));
    const areaSet = new Set(AREA_TAGS);
    const result = [];
    STAFF_TAGS.forEach(s => { if (defaults.has(s)) result.push(s); });
    AREA_TAGS.forEach(a => { if (defaults.has(a)) result.push(a); });
    defaults.forEach(tag => {
      if (!result.includes(tag) && !staffSet.has(tag.toLowerCase()) && !areaSet.has(tag)) {
        result.push(tag);
      }
    });
    return result;
  }

  function buildQuickTags(currentTags) {
    const currentLower = (currentTags || []).map(t => t.toLowerCase());
    return getCommonTags().map(tag => {
      const active = currentLower.includes(tag.toLowerCase()) ? ' active' : '';
      return `<button type="button" class="quick-tag-btn${active}" onclick="toggleQuickTag(this, '${escapeHTML(tag)}')">${escapeHTML(tag)}</button>`;
    }).join('');
  }

  function toggleQuickTag(btn, tag) {
    // Find the tags input in the same editor form
    const form = btn.closest('.task-edit-form');
    const input = form.querySelector('input[id^="edit-tags-"]');
    let tags = input.value ? input.value.split(',').map(t => t.trim()).filter(Boolean) : [];

    const idx = tags.findIndex(t => t.toLowerCase() === tag.toLowerCase());
    if (idx >= 0) {
      tags.splice(idx, 1);
      btn.classList.remove('active');
    } else {
      tags.push(tag);
      btn.classList.add('active');
    }
    input.value = tags.join(', ');
  }

  function openTaskEditor(id, event) {
    if (selectMode) return;
    event.stopPropagation();
    const task = allTasks.find(t => t.id === id);
    if (!task || task.status === 'done') return;

    // Close any existing editor
    if (editingTaskId) closeTaskEditor();
    editingTaskId = id;

    const taskEl = document.querySelector(`.task[data-id="${id}"]`);
    if (!taskEl) return;

    const projects = [...new Set(allTasks.filter(t => t.project).map(t => t.project))].sort();
    const projectOptions = projects.map(p => `<option value="${p}" ${task.project === p ? 'selected' : ''}>${p}</option>`).join('');

    const form = document.createElement('div');
    form.className = 'task-edit-form';
    form.id = `edit-form-${id}`;
    form.onclick = (e) => e.stopPropagation();
    form.innerHTML = `
      <div class="edit-field">
        <label>Task</label>
        <input type="text" id="edit-name-${id}" value="${escapeHTML(task.name)}">
      </div>
      <div class="edit-row">
        <div class="edit-field">
          <label>Project</label>
          <select id="edit-project-${id}">
            <option value="">None</option>
            ${projectOptions}
          </select>
        </div>
        <div class="edit-field">
          <label>Domain</label>
          <select id="edit-domain-${id}">
            <option value="work" ${task.domain === 'work' ? 'selected' : ''}>Work</option>
            <option value="home" ${task.domain === 'home' ? 'selected' : ''}>Home</option>
          </select>
        </div>
      </div>
      <div class="edit-row">
        <div class="edit-field">
          <label>Due date</label>
          <input type="date" id="edit-due-${id}" value="${task.due_date || ''}">
        </div>
        <div class="edit-field">
          <label>Defer date</label>
          <input type="date" id="edit-defer-${id}" value="${task.defer_date || ''}">
        </div>
      </div>
      <div class="edit-field">
        <label>Tags</label>
        <div class="quick-tags" id="quick-tags-${id}">${buildQuickTags(task.tags || [])}</div>
        <input type="text" id="edit-tags-${id}" value="${(task.tags || []).join(', ')}" placeholder="Or type custom tags, comma-separated">
      </div>
      <div class="edit-field">
        <label>Notes</label>
        <textarea id="edit-notes-${id}" rows="3" style="width:100%;padding:0.4rem 0.5rem;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:var(--font);font-size:0.8125rem;resize:vertical;">${escapeHTML(task.capture_notes || '')}</textarea>
      </div>
      <div class="edit-actions">
        <button class="cancel-edit-btn" onclick="closeTaskEditor()">Cancel</button>
        <button class="save-btn" onclick="saveTaskEdit('${id}')">Save</button>
      </div>
    `;

    taskEl.style.display = 'none';
    taskEl.parentNode.insertBefore(form, taskEl.nextSibling);

    document.getElementById(`edit-name-${id}`).focus();
    document.getElementById(`edit-name-${id}`).addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveTaskEdit(id);
      if (e.key === 'Escape') closeTaskEditor();
    });
  }

  function closeTaskEditor() {
    if (!editingTaskId) return;
    const form = document.getElementById(`edit-form-${editingTaskId}`);
    const taskEl = document.querySelector(`.task[data-id="${editingTaskId}"]`);
    if (form) form.remove();
    if (taskEl) taskEl.style.display = '';
    editingTaskId = null;
  }

  async function saveTaskEdit(id) {
    if (savingTask) return;
    savingTask = true;
    try {
      const name = document.getElementById(`edit-name-${id}`).value.trim();
      if (!name) return;

      const project = document.getElementById(`edit-project-${id}`).value || null;
      const domain = document.getElementById(`edit-domain-${id}`).value;
      const due_date = document.getElementById(`edit-due-${id}`).value || null;
      const defer_date = document.getElementById(`edit-defer-${id}`).value || null;
      const tagsRaw = document.getElementById(`edit-tags-${id}`).value;
      const tags = tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : null;
      const capture_notes = document.getElementById(`edit-notes-${id}`).value.trim() || null;

      const update = { name, project, domain, due_date, defer_date, tags, capture_notes };

      // If defer_date was set and task isn't already deferred, move it
      const task = allTasks.find(t => t.id === id);
      if (defer_date && task && task.status !== 'deferred') {
        update.status = 'deferred';
      }
      // If defer_date was cleared and task is deferred, move to inbox
      if (!defer_date && task && task.status === 'deferred') {
        update.status = 'inbox';
      }

      const { error } = await sb
        .from('tasks')
        .update(update)
        .eq('id', id);

      editingTaskId = null;
      if (error) {
        showToast('Save failed: ' + error.message, 'error');
      } else {
        await loadTasks();
      }
    } catch (err) {
      showToast('Save failed: ' + err.message, 'error');
    } finally {
      savingTask = false;
    }
  }

  async function handleQuickAdd() {
    const input = document.getElementById('quick-add-input');
    const pool = document.getElementById('quick-add-pool').value;
    const name = input.value.trim();
    if (!name) return;

    // Create optimistic task
    const tempTask = {
      id: 'temp-' + Date.now(),
      name: name,
      status: pool,
      domain: 'work',
      capture_notes: name,
      done: false,
      created_at: new Date().toISOString()
    };

    const previousTasks = JSON.parse(JSON.stringify(allTasks));
    allTasks.push(tempTask);
    renderTasks();

    input.value = '';
    showToast('Task added');

    try {
      const { error, data } = await sb
        .from('tasks')
        .insert({
          name: name,
          status: pool,
          domain: 'work',
          capture_notes: name
        });

      if (error) {
        // Revert on error
        allTasks = previousTasks;
        renderTasks();
        showToast(`Error: ${error.message}`, { type: 'error' });
      } else {
        // Reload to sync with server state
        await loadTasks();
      }
    } catch (e) {
      allTasks = previousTasks;
      renderTasks();
      showToast(`Error: ${e.message}`, { type: 'error' });
    }
  }

  function toggleCollapsible(id) {
    const body = document.getElementById(`${id}-body`);
    const arrow = document.getElementById(`${id}-arrow`);
    const header = arrow.closest('.collapsible-header');
    body.classList.toggle('open');
    header.classList.toggle('open');
  }

  function toggleMoveMenu(event, id) {
    event.stopPropagation();
    const menu = document.getElementById(`menu-${id}`);
    const wasOpen = menu.style.display === 'block';
    closeAllMenus();
    if (!wasOpen) menu.style.display = 'block';
  }

  function closeAllMenus() {
    document.querySelectorAll('.move-menu').forEach(m => m.style.display = 'none');
  }

  document.addEventListener('click', closeAllMenus);

  // — Drag and Drop (Safari-compatible + touch support) —
  let draggedTaskId = null;
  let draggedFromPool = null;
  const dragEnterCounters = new Map(); // counter per drop zone to fix Safari flicker

  function onDragStart(event, taskId, fromPool) {
    draggedTaskId = taskId;
    draggedFromPool = fromPool;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', taskId);
    // Reset all counters
    dragEnterCounters.clear();
    // Delay so the dragging class doesn't flash before ghost image forms
    requestAnimationFrame(() => {
      event.target.closest('.task').classList.add('dragging');
    });
    // Expand collapsed sections so they can receive drops
    document.querySelectorAll('.collapsible-body').forEach(body => {
      body.classList.add('open');
      const section = body.closest('.section');
      const header = section.querySelector('.collapsible-header');
      if (header) header.classList.add('open');
    });
  }

  function onDragEnd(event) {
    event.target.closest('.task')?.classList.remove('dragging');
    document.querySelectorAll('.drop-zone').forEach(z => z.classList.remove('drag-over'));
    dragEnterCounters.clear();
    draggedTaskId = null;
    draggedFromPool = null;
  }

  function onDragEnter(event) {
    event.preventDefault();
    const zone = event.currentTarget;
    const pool = zone.dataset.pool;
    const count = (dragEnterCounters.get(pool) || 0) + 1;
    dragEnterCounters.set(pool, count);
    if (pool !== draggedFromPool) {
      zone.classList.add('drag-over');
    }
  }

  function onDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }

  function onDragLeave(event) {
    const zone = event.currentTarget;
    const pool = zone.dataset.pool;
    const count = (dragEnterCounters.get(pool) || 1) - 1;
    dragEnterCounters.set(pool, count);
    // Only remove highlight when we've truly left (counter back to 0)
    if (count <= 0) {
      zone.classList.remove('drag-over');
      dragEnterCounters.set(pool, 0);
    }
  }

  async function onDrop(event, targetPool) {
    event.preventDefault();
    event.stopPropagation();
    const zone = event.currentTarget;
    zone.classList.remove('drag-over');
    dragEnterCounters.set(targetPool, 0);

    if (!draggedTaskId || targetPool === draggedFromPool) return;

    await moveTask(draggedTaskId, targetPool);
    draggedTaskId = null;
    draggedFromPool = null;
  }

  // — Touch drag support (iOS Safari) —
  let touchDragEl = null;
  let touchClone = null;
  let touchStartY = 0;
  let touchMoved = false;

  function onTouchDragStart(event, taskId, fromPool) {
    const touch = event.touches[0];
    touchStartY = touch.clientY;
    touchMoved = false;
    touchDragEl = event.target.closest('.task');
    draggedTaskId = taskId;
    draggedFromPool = fromPool;

    // Long press detection — 300ms
    touchDragEl._touchTimer = setTimeout(() => {
      touchMoved = true;
      touchDragEl.classList.add('dragging');
      // Create a floating clone
      touchClone = touchDragEl.cloneNode(true);
      touchClone.style.cssText = `position:fixed;top:${touch.clientY - 20}px;left:${touch.clientX - 20}px;width:${touchDragEl.offsetWidth}px;opacity:0.85;z-index:9999;pointer-events:none;transform:rotate(2deg);box-shadow:0 8px 24px rgba(0,0,0,0.3);`;
      document.body.appendChild(touchClone);
      // Expand collapsed sections
      document.querySelectorAll('.collapsible-body').forEach(body => {
        body.classList.add('open');
        const section = body.closest('.section');
        const header = section.querySelector('.collapsible-header');
        if (header) header.classList.add('open');
      });
    }, 300);
  }

  function onTouchDragMove(event) {
    if (!touchMoved || !touchClone) {
      // Check if finger moved enough to cancel (if not yet in drag mode)
      if (!touchMoved && touchDragEl) {
        const touch = event.touches[0];
        if (Math.abs(touch.clientY - touchStartY) > 10) {
          clearTimeout(touchDragEl._touchTimer);
          cleanupTouch();
        }
      }
      return;
    }
    event.preventDefault();
    const touch = event.touches[0];
    touchClone.style.top = (touch.clientY - 20) + 'px';
    touchClone.style.left = (touch.clientX - 20) + 'px';

    // Highlight drop zone under finger
    document.querySelectorAll('.drop-zone').forEach(z => z.classList.remove('drag-over'));
    const el = document.elementFromPoint(touch.clientX, touch.clientY);
    if (el) {
      const zone = el.closest('.drop-zone');
      if (zone && zone.dataset.pool !== draggedFromPool) {
        zone.classList.add('drag-over');
      }
    }
  }

  async function onTouchDragEnd(event) {
    if (touchDragEl) clearTimeout(touchDragEl._touchTimer);
    if (!touchMoved || !touchClone) { cleanupTouch(); return; }

    const touch = event.changedTouches[0];
    const el = document.elementFromPoint(touch.clientX, touch.clientY);
    const zone = el?.closest('.drop-zone');

    document.querySelectorAll('.drop-zone').forEach(z => z.classList.remove('drag-over'));

    if (zone && zone.dataset.pool !== draggedFromPool && draggedTaskId) {
      await moveTask(draggedTaskId, zone.dataset.pool);
    }

    cleanupTouch();
  }

  function cleanupTouch() {
    if (touchClone) { touchClone.remove(); touchClone = null; }
    if (touchDragEl) { touchDragEl.classList.remove('dragging'); touchDragEl = null; }
    draggedTaskId = null;
    draggedFromPool = null;
    touchMoved = false;
  }

  function daysUntil(dateStr) {
    const target = new Date(dateStr + 'T00:00:00');
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return Math.floor((target - now) / (1000 * 60 * 60 * 24));
  }

  function formatDate(dateStr) {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  async function loadAgenda() {
    const container = document.getElementById('agenda-container');
    const now = new Date();
    const todayStr = now.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });

    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });

    const startOfToday = new Date(now);
    startOfToday.setHours(0, 0, 0, 0);
    const endOfTomorrow = new Date(tomorrow);
    endOfTomorrow.setHours(23, 59, 59, 999);

    const { data: events, error } = await sb
      .from('calendar_events')
      .select('*')
      .gte('start_time', startOfToday.toISOString())
      .lte('start_time', endOfTomorrow.toISOString())
      .neq('status', 'cancelled')
      .order('start_time', { ascending: true });

    if (error) {
      console.log('Agenda load:', error);
      container.innerHTML = '<div class="agenda-empty">Calendar not synced yet</div>';
      return;
    }

    if (!events || events.length === 0) {
      container.innerHTML = '<div class="agenda-empty">No events synced yet — run calendar sync to populate</div>';
      return;
    }

    const tomorrowStart = new Date(tomorrow);
    tomorrowStart.setHours(0, 0, 0, 0);
    const tomorrowStartMs = tomorrowStart.getTime();

    const todayEvents = events.filter(e => new Date(e.start_time).getTime() < tomorrowStartMs);
    const tomorrowEvents = events.filter(e => new Date(e.start_time).getTime() >= tomorrowStartMs);

    let html = '';

    html += `<div class="agenda-day-label">Today — ${todayStr}</div>`;

    if (todayEvents.length > 0) {
      let nowMarkerInserted = false;

      todayEvents.forEach((e, i) => {
        const evStart = new Date(e.start_time);
        const evEnd = new Date(e.end_time);
        const status = getEventTimeStatus(evStart, evEnd, now);

        if (!nowMarkerInserted && (status === 'current' || status === 'upcoming')) {
          html += nowMarkerHTML(now);
          nowMarkerInserted = true;
        }

        html += agendaEventHTML(e, status);
      });

      if (!nowMarkerInserted) {
        html += nowMarkerHTML(now);
      }
    } else {
      html += '<div class="agenda-empty">Clear day</div>';
    }

    if (tomorrowEvents.length > 0) {
      html += `<div class="agenda-day-label">Tomorrow — ${tomorrowStr}</div>`;
      html += tomorrowEvents.map(e => agendaEventHTML(e, 'upcoming')).join('');
    }

    container.innerHTML = html;

    setTimeout(() => {
      const marker = container.querySelector('.agenda-now-marker');
      if (marker) {
        marker.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }, 100);
  }

  function getEventTimeStatus(start, end, now) {
    if (now >= end) return 'past';
    if (now >= start && now < end) return 'current';
    return 'upcoming';
  }

  function nowMarkerHTML(now) {
    const timeStr = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase();
    return `
      <div class="agenda-now-marker">
        <span class="agenda-now-time">${timeStr}</span>
      </div>
    `;
  }

  function agendaEventHTML(event, status) {
    const start = new Date(event.start_time);
    let timeStr;

    if (event.all_day) {
      timeStr = 'all day';
    } else {
      timeStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase();
    }

    const dotColor = event.color || '#c4956a';
    const locationHtml = event.location
      ? `<div class="event-location">${escapeHTML(event.location)}</div>`
      : '';

    return `
      <div class="agenda-event ${status}">
        <span class="agenda-time">${timeStr}</span>
        <span class="agenda-dot" style="background:${dotColor}"></span>
        <div class="agenda-summary">
          <div class="event-title">${escapeHTML(event.summary)}</div>
          ${locationHtml}
        </div>
      </div>
    `;
  }

  setInterval(() => { loadAgenda(); }, 5 * 60 * 1000);

  const COACHING_ITEMS = [
    { text: "Driven and peaceful. Strategic and compassionate. Ambitious and humble. The balance itself is the gift.", source: "integration" },
    { text: "Pursue excellence without perfectionism. Seek peace without avoiding hard things.", source: "integration" },
    { text: "The goal isn't to be more driven or more peaceful — it's to hold both without letting one win.", source: "integration" },
    { text: "Authenticity over performance. Be real rather than impressive.", source: "growth edge" },
    { text: "Presence over productivity. The point of finishing work by Friday isn't to finish everything — it's to be free for sabbath.", source: "growth edge" },
    { text: "Care for others without losing yourself. The discipline is extending grace to yourself.", source: "growth edge" },
    { text: "A husband, dad, and pastor whose superpower is integration — holding drive and peace, ambition and humility, strength and gentleness together.", source: "identity" },
    { text: "The family doesn't need a busier pastor — it needs a more present dad and husband.", source: "family" },
    { text: "When you're off-balance, you've collapsed into one pole. The correction isn't to abandon the drive — it's to make room for the other half again.", source: "awareness" },
    { text: "Level 1 isn't 'better achievement.' It's the drive and the peace fully integrated, no longer in competition.", source: "Enneagram 3" },
    { text: "Name what you need rather than quietly carrying it.", source: "growth edge" },
    { text: "The humor turns fully self-deprecating — not as a defense, but from real ease with imperfection. The heart opens completely.", source: "the summit" },
    { text: "Friday evening. Sermon done. Family together. Nothing urgent pulling. The yard looking good. That's the target.", source: "what peace looks like" },
    { text: "Visionary and grounded. Justice-oriented and grace-filled. Strong and gentle. This is not inconsistency. It is integration.", source: "integration" },
    { text: "The gap between where you are and Level 1 isn't about doing more. It's about needing less.", source: "Enneagram 3" },
    { text: "When we honestly ask ourselves which person in our lives means the most to us, we often find that it is those who, instead of giving advice, solutions, or cures, have chosen rather to share our pain.", source: "Henri Nouwen" },
    { text: "Vocation does not come from willfulness. It comes from listening. I must listen to my life and try to understand what it is truly about.", source: "Parker Palmer" },
    { text: "Here is the world. Beautiful and terrible things will happen. Don't be afraid.", source: "Frederick Buechner" },
    { text: "Vulnerability is not winning or losing; it's having the courage to show up and be seen when we have no control over the outcome.", source: "Brené Brown" },
    { text: "Don't ask what the world needs. Ask what makes you come alive, and go do it. Because what the world needs is people who have come alive.", source: "Howard Thurman" },
    { text: "We do not find the meaning of life by ourselves alone — we find it with another.", source: "Thomas Merton" },
    { text: "The mind that is not baffled is not employed. The impeded stream is the one that sings.", source: "Wendell Berry" },
    { text: "We do not think ourselves into new ways of living. We live ourselves into new ways of thinking.", source: "Richard Rohr" },
    { text: "If you can't fly then run, if you can't run then walk, if you can't walk then crawl, but whatever you do you have to keep moving forward.", source: "Martin Luther King Jr." },
    { text: "In the middle of difficulty lies opportunity.", source: "Albert Einstein" },
    { text: "The place God calls you to is the place where your deep gladness and the world's deep hunger meet.", source: "Frederick Buechner" },
    { text: "Grace means that all of your mistakes now serve a purpose instead of serving shame.", source: "Brené Brown" },
  ];

  function renderCoachingCard() {
    const card = document.getElementById('coaching-card');
    const item = COACHING_ITEMS[Math.floor(Math.random() * COACHING_ITEMS.length)];
    card.innerHTML = `
      <div class="coaching-text">"${escapeHTML(item.text)}"</div>
      <div class="coaching-source">— ${escapeHTML(item.source)}</div>
    `;
  }

  checkAuth();

  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') handleLogin();
  });