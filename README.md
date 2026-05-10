# ⚡ EventFlow — Full-Stack Event Management Platform

A production-ready event management system built with **FastAPI** (Python) backend, **SQLite** database, and a polished **HTML/CSS/JS** frontend.

---

## 🚀 Quick Start

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
uvicorn main:app --reload --port 8000
```

### 3. Open in Browser
```
http://localhost:8000
```

---

## 📋 Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| 🔴 Admin | admin@eventflow.com | admin123 |
| 🟡 Organizer | organizer@eventflow.com | org123 |
| 🟢 Attendee | attendee@eventflow.com | att123 |

The database is auto-seeded with **8 sample events** on first run.

---

## 🗂️ Project Structure

```
eventflow/
├── main.py                     # FastAPI app entry point + seeding
├── requirements.txt            # Python dependencies
├── run.py                      # One-click start script
├── eventflow.db                # SQLite database (auto-created)
│
├── backend/
│   ├── config.py               # App settings
│   ├── models.py               # SQLAlchemy ORM models + DB setup
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth.py                 # JWT auth, password hashing, guards
│   ├── utils.py                # Slug, QR code, file upload helpers
│   └── routers/
│       ├── auth.py             # /api/auth/* — register, login, me
│       ├── events.py           # /api/events/* — full CRUD + search
│       ├── registrations.py    # /api/registrations/* — tickets, check-in
│       └── misc.py             # /api/users, /dashboard, /comments, /notifications
│
├── frontend/
│   ├── static/
│   │   ├── css/main.css        # Full design system (dark theme, Syne font)
│   │   └── js/app.js           # API client, Auth, Toast, Utils
│   └── templates/
│       ├── index.html          # Home: hero, featured events, search
│       ├── events.html         # Browse all events with filters
│       ├── event.html          # Event detail: tickets, comments, QR
│       ├── create-event.html   # Create/Edit event (shared template)
│       ├── dashboard.html      # Role-based dashboard (admin/org/attendee)
│       ├── my-tickets.html     # Attendee ticket wallet
│       ├── profile.html        # Profile & password management
│       ├── checkin.html        # Organizer check-in station
│       ├── login.html          # Login with demo account quick-fill
│       └── register.html       # Register with role selection
│
└── uploads/                    # Auto-created for uploaded files
    ├── avatars/
    ├── events/
    └── qrcodes/
```

---

## ✨ Feature Set

### User Management
- ✅ Register / Login with JWT authentication
- ✅ Roles: **Admin**, **Organizer**, **Attendee**
- ✅ Profile management + avatar upload
- ✅ Password change

### Event Management
- ✅ Create / Edit / Delete events
- ✅ 8 Categories (Conference, Workshop, Concert, Meetup, Webinar, Sports, Arts, Networking)
- ✅ Cover image upload
- ✅ Status: Draft → Published → Cancelled / Completed
- ✅ Public / Private events
- ✅ Recurring events support (field + recurrence rule)
- ✅ Featured events (admin toggleable)
- ✅ Tags and custom fields

### Registration & Ticketing
- ✅ Free & paid ticket tiers (multiple per event)
- ✅ Capacity limits with sold count tracking
- ✅ **QR code ticket generation** (PNG files)
- ✅ **Waitlist** when sold out (auto-assigned)
- ✅ Registration cancellation

### Dashboard & Analytics
- ✅ **Admin**: total users, events, registrations, revenue + 7-day chart
- ✅ **Organizer**: per-event stats, revenue, registration counts
- ✅ **Attendee**: upcoming tickets, past events, total spent

### Check-In System
- ✅ Manual check-in by ticket number
- ✅ QR data paste-and-process
- ✅ Real-time attendance count per event
- ✅ Check-in history log

### Search & Discovery
- ✅ Search by name, description, city
- ✅ Filter by category, format (online/in-person), price (free/paid)
- ✅ Featured events section
- ✅ Grid and list view modes
- ✅ Pagination

### Comments & Q&A
- ✅ Attendees post questions/comments on event pages
- ✅ Threaded replies
- ✅ Mark as question flag

### Notifications
- ✅ In-app notifications on registration
- ✅ Unread badge count in navbar

---

## 🔌 API Reference

Full interactive docs: **http://localhost:8000/api/docs**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| GET | `/api/auth/me` | Current user profile |
| GET | `/api/events` | List/search events |
| POST | `/api/events` | Create event |
| GET | `/api/events/{id}` | Event detail |
| PUT | `/api/events/{id}` | Update event |
| DELETE | `/api/events/{id}` | Delete event |
| POST | `/api/registrations` | Register for event |
| GET | `/api/registrations/my` | My tickets |
| POST | `/api/registrations/checkin` | Check in by ticket number |
| GET | `/api/dashboard/admin` | Admin stats |
| GET | `/api/dashboard/organizer` | Organizer stats |
| GET | `/api/dashboard/attendee` | Attendee dashboard |
| GET | `/api/comments/event/{id}` | Event comments |
| POST | `/api/comments/event/{id}` | Post comment |
| GET | `/api/notifications` | My notifications |

---

## 🗄️ Database Schema

**Users** → **Events** (one-to-many via organizer)  
**Events** → **TicketTiers** (one-to-many)  
**TicketTiers** → **Registrations** (one-to-many)  
**Users** → **Registrations** (one-to-many as attendee)  
**Events** → **Comments** (one-to-many, self-referencing for replies)  
**Users** → **Notifications** (one-to-many)

---

## ⚙️ Configuration

Edit `backend/config.py` or create a `.env` file:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./eventflow.db
BASE_URL=http://localhost:8000
SMTP_HOST=smtp.gmail.com
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | SQLite via SQLAlchemy ORM |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Fonts | Syne (display) + DM Sans (body) |
| QR Codes | qrcode[pil] library |
| Images | Pillow (resize + optimize) |
