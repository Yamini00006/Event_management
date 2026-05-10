// ── API Client ────────────────────────────────────────────────
const API = {
  base: '/api',
  
  getToken() { return localStorage.getItem('ef_token'); },
  setToken(t) { localStorage.setItem('ef_token', t); },
  clearToken() { localStorage.removeItem('ef_token'); localStorage.removeItem('ef_user'); },
  getUser() { try { return JSON.parse(localStorage.getItem('ef_user')); } catch { return null; } },
  setUser(u) { localStorage.setItem('ef_user', JSON.stringify(u)); },
  
  async request(method, path, body = null, isForm = false) {
    const headers = {};
    const token = this.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (body && !isForm) headers['Content-Type'] = 'application/json';
    
    const opts = { method, headers };
    if (body) opts.body = isForm ? body : JSON.stringify(body);
    
    const res = await fetch(this.base + path, opts);
    const data = await res.json();
    
    if (!res.ok) {
      throw new Error(data.detail || 'Request failed');
    }
    return data;
  },
  
  get(path) { return this.request('GET', path); },
  post(path, body) { return this.request('POST', path, body); },
  put(path, body) { return this.request('PUT', path, body); },
  delete(path) { return this.request('DELETE', path); },
  
  async postForm(path, formData) {
    const token = this.getToken();
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    const res = await fetch(this.base + path, { method: 'POST', headers, body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');
    return data;
  },
  
  async loginForm(email, password) {
    const form = new FormData();
    form.append('username', email);
    form.append('password', password);
    const res = await fetch(this.base + '/auth/login', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    return data;
  }
};

// ── Auth helpers ──────────────────────────────────────────────
const Auth = {
  isLoggedIn() { return !!API.getToken(); },
  getUser() { return API.getUser(); },
  hasRole(...roles) { const u = this.getUser(); return u && roles.includes(u.role); },
  isAdmin() { return this.hasRole('admin'); },
  isOrganizer() { return this.hasRole('organizer', 'admin'); },
  
  async login(email, password) {
    const data = await API.loginForm(email, password);
    API.setToken(data.access_token);
    API.setUser(data.user);
    return data.user;
  },
  
  async register(payload) {
    const data = await API.post('/auth/register', payload);
    API.setToken(data.access_token);
    API.setUser(data.user);
    return data.user;
  },
  
  logout() {
    API.clearToken();
    window.location.href = '/';
  },
  
  require() {
    if (!this.isLoggedIn()) {
      window.location.href = '/login';
      return false;
    }
    return true;
  }
};

// ── Toast ─────────────────────────────────────────────────────
const Toast = {
  container: null,
  
  init() {
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    document.body.appendChild(this.container);
  },
  
  show(msg, type = 'info', duration = 4000) {
    if (!this.container) this.init();
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${icons[type] || icons.info}</span><span class="toast-msg">${msg}</span>`;
    this.container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateX(120%)'; el.style.transition = '0.3s'; setTimeout(() => el.remove(), 300); }, duration);
  },
  
  success(msg) { this.show(msg, 'success'); },
  error(msg) { this.show(msg, 'error'); },
  info(msg) { this.show(msg, 'info'); },
};

// ── Utils ─────────────────────────────────────────────────────
const Utils = {
  formatDate(dt) {
    const d = new Date(dt);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  },
  formatDateTime(dt) {
    const d = new Date(dt);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
  },
  formatPrice(price, currency = 'USD') {
    if (!price || price === 0) return '<span class="free">FREE</span>';
    return `<span class="paid">$${price.toFixed(2)}</span>`;
  },
  categoryEmoji(cat) {
    const map = { conference:'🎤', workshop:'🛠️', concert:'🎵', meetup:'☕', webinar:'💻', sports:'⚽', arts:'🎨', networking:'🤝', other:'📅' };
    return map[cat] || '📅';
  },
  statusColor(status) {
    return { draft:'badge-draft', published:'badge-published', cancelled:'badge-cancelled', completed:'badge-completed' }[status] || 'badge-draft';
  },
  
  eventCardHTML(event) {
    const emoji = this.categoryEmoji(event.category);
    const imgHTML = event.cover_image_url 
      ? `<img src="${event.cover_image_url}" alt="${event.title}" loading="lazy">`
      : `<div class="event-no-img">${emoji}</div>`;
    const price = event.min_price > 0 
      ? `<span class="event-price paid">$${event.min_price.toFixed(2)}</span>`
      : `<span class="event-price free">FREE</span>`;
    const loc = event.is_online ? 'Online' : [event.venue_city, event.venue_country].filter(Boolean).join(', ') || 'TBA';
    
    return `
      <a href="/event/${event.id}" class="event-card">
        <div class="event-card-img">${imgHTML}</div>
        <div class="event-card-body">
          <div class="event-card-badges">
            <span class="badge badge-category">${event.category}</span>
            ${event.is_online ? '<span class="badge badge-online">Online</span>' : ''}
            ${event.is_featured ? '<span class="badge badge-featured">Featured</span>' : ''}
          </div>
          <div class="event-card-title">${event.title}</div>
          <div class="event-card-meta">
            <div class="event-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              ${this.formatDateTime(event.start_datetime)}
            </div>
            <div class="event-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
              ${loc}
            </div>
          </div>
          <div class="event-card-footer">
            ${price}
            <span class="event-attendees">👥 ${event.total_registrations} attending</span>
          </div>
        </div>
      </a>`;
  },
  
  debounce(fn, delay) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
  },
  
  async copyText(text) {
    await navigator.clipboard.writeText(text);
    Toast.success('Copied!');
  }
};

// ── Navbar ─────────────────────────────────────────────────────
function initNavbar() {
  const user = Auth.getUser();
  const navRight = document.getElementById('nav-right');
  if (!navRight) return;
  
  if (user) {
    const avatar = user.avatar_url 
      ? `<img src="${user.avatar_url}" alt="${user.full_name}">` 
      : user.full_name.charAt(0).toUpperCase();
    
    navRight.innerHTML = `
      <div class="nav-menu">
        <div class="nav-avatar" id="nav-avatar-btn" style="position:relative">
          ${avatar}
          <span id="notif-count" class="notif-badge" style="display:none"></span>
        </div>
        <div class="nav-dropdown" id="nav-dropdown">
          <div style="padding:10px 12px 8px;border-bottom:1px solid var(--border);margin-bottom:6px">
            <div style="font-weight:600;font-size:14px">${user.full_name}</div>
            <div style="font-size:12px;color:var(--text-3)">${user.email}</div>
            <div style="margin-top:4px"><span class="badge badge-category">${user.role}</span></div>
          </div>
          <a href="/dashboard">📊 Dashboard</a>
          ${Auth.isOrganizer() ? '<a href="/create-event">➕ Create Event</a>' : ''}
          <a href="/profile">👤 Profile</a>
          <a href="/my-tickets">🎟️ My Tickets</a>
          ${Auth.isAdmin() ? '<a href="/admin">⚙️ Admin Panel</a>' : ''}
          <div class="divider"></div>
          <button onclick="Auth.logout()">🚪 Sign Out</button>
        </div>
      </div>`;
    
    document.getElementById('nav-avatar-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      document.getElementById('nav-dropdown').classList.toggle('open');
    });
    document.addEventListener('click', () => {
      const dd = document.getElementById('nav-dropdown');
      if (dd) dd.classList.remove('open');
    });
    
    loadNotifCount();
  } else {
    navRight.innerHTML = `
      <a href="/login" class="btn btn-ghost btn-sm">Sign In</a>
      <a href="/register" class="btn btn-primary btn-sm">Get Started</a>`;
  }
  
  // Active link
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.href === window.location.href) a.classList.add('active');
  });
}

async function loadNotifCount() {
  if (!Auth.isLoggedIn()) return;
  try {
    const notifs = await API.get('/notifications');
    const unread = notifs.filter(n => !n.is_read).length;
    const badge = document.getElementById('notif-count');
    if (badge) {
      if (unread > 0) { badge.textContent = unread; badge.style.display = 'flex'; }
      else badge.style.display = 'none';
    }
  } catch {}
}

// ── Modal helper ───────────────────────────────────────────────
function openModal(html, onClose) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal">${html}</div>`;
  document.body.appendChild(overlay);
  document.body.style.overflow = 'hidden';
  
  const close = () => {
    overlay.remove();
    document.body.style.overflow = '';
    if (onClose) onClose();
  };
  
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
  overlay.querySelector('.modal-close')?.addEventListener('click', close);
  return { overlay, close };
}

// Init on load
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  initNavbar();
});
