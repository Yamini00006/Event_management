from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from backend.config import settings
from backend.models import create_tables
from backend.routers.auth import router as auth_router
from backend.routers.events import router as events_router
from backend.routers.registrations import router as registrations_router
from backend.routers.misc import (
    users_router, dashboard_router, comments_router, notifications_router
)

app = FastAPI(
    title="EventFlow API",
    description="Full-featured Event Management Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables
create_tables()

# Create upload dirs
Path("uploads/avatars").mkdir(parents=True, exist_ok=True)
Path("uploads/events").mkdir(parents=True, exist_ok=True)
Path("uploads/qrcodes").mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(registrations_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")


# Seed demo data
@app.on_event("startup")
async def seed_data():
    from backend.models import SessionLocal, User, Event, TicketTier, UserRole, EventStatus, EventCategory, TicketType
    from backend.auth import hash_password
    from backend.utils import generate_unique_slug
    from datetime import datetime, timedelta
    import random
    
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        
        # Create users
        admin = User(
            email="admin@eventflow.com", username="admin",
            full_name="Admin User", hashed_password=hash_password("admin123"),
            role=UserRole.admin, is_active=True, is_verified=True
        )
        organizer = User(
            email="organizer@eventflow.com", username="organizer",
            full_name="Jane Organizer", hashed_password=hash_password("org123"),
            role=UserRole.organizer, is_active=True, is_verified=True,
            bio="Experienced event organizer with 10+ years in the industry."
        )
        attendee = User(
            email="attendee@eventflow.com", username="attendee",
            full_name="John Doe", hashed_password=hash_password("att123"),
            role=UserRole.attendee, is_active=True, is_verified=True
        )
        db.add_all([admin, organizer, attendee])
        db.flush()
        
        # Create events
        categories = [EventCategory.conference, EventCategory.workshop, EventCategory.meetup, EventCategory.webinar, EventCategory.concert]
        events_data = [
            ("Tech Summit 2026", "The biggest tech conference of the year featuring industry leaders, workshops, and networking opportunities.", "Annual technology conference", EventCategory.conference, True, False, "Convention Center", "San Francisco", "USA", 500, 199.0),
            ("AI & Machine Learning Workshop", "Hands-on workshop covering the latest in AI and ML. Bring your laptop!", "Intensive ML workshop", EventCategory.workshop, True, True, None, None, None, 30, 49.0),
            ("Startup Networking Night", "Connect with fellow entrepreneurs, investors, and startup enthusiasts.", "Monthly startup meetup", EventCategory.meetup, False, False, "The Hub", "New York", "USA", 100, 0.0),
            ("Web Dev Conference 2026", "Two-day conference covering modern web development, DevOps, and cloud technologies.", "Web development summit", EventCategory.conference, True, False, "Grand Ballroom", "Austin", "USA", 300, 129.0),
            ("Music Festival Live", "Three days of amazing live music from top artists across multiple stages.", "Annual music festival", EventCategory.concert, False, False, "City Park", "Los Angeles", "USA", 5000, 89.0),
            ("Python Bootcamp", "Intensive 1-day Python bootcamp for beginners and intermediate programmers.", "Python learning event", EventCategory.workshop, True, True, None, None, None, 50, 29.0),
            ("Product Design Summit", "Discover the future of UX/UI design with leading designers.", "Design conference", EventCategory.conference, False, False, "Design Hub", "Chicago", "USA", 200, 79.0),
            ("Blockchain & Web3 Meetup", "Monthly meetup for blockchain enthusiasts and Web3 developers.", "Web3 community meetup", EventCategory.meetup, False, True, None, None, None, 80, 0.0),
        ]
        
        for i, (title, desc, short_desc, cat, is_featured, is_online, venue, city, country, capacity, price) in enumerate(events_data):
            days_ahead = random.randint(5, 90)
            start = datetime.utcnow() + timedelta(days=days_ahead)
            end = start + timedelta(hours=random.randint(2, 8))
            slug = generate_unique_slug(title, db, Event)
            
            event = Event(
                title=title, slug=slug, description=desc, short_description=short_desc,
                category=cat, status=EventStatus.published, is_public=True,
                is_online=is_online, is_featured=is_featured,
                start_datetime=start, end_datetime=end, timezone="UTC",
                venue_name=venue, venue_city=city, venue_country=country,
                organizer_id=organizer.id, tags=["2026", cat.value],
            )
            db.add(event)
            db.flush()
            
            # Free tier
            if price > 0:
                db.add(TicketTier(
                    event_id=event.id, name="General Admission",
                    ticket_type=TicketType.paid, price=price, currency="USD",
                    capacity=capacity, sold_count=random.randint(0, capacity // 3)
                ))
                db.add(TicketTier(
                    event_id=event.id, name="VIP",
                    ticket_type=TicketType.paid, price=price * 2.5, currency="USD",
                    capacity=20, sold_count=random.randint(0, 5)
                ))
            else:
                db.add(TicketTier(
                    event_id=event.id, name="Free Registration",
                    ticket_type=TicketType.free, price=0.0, currency="USD",
                    capacity=capacity, sold_count=random.randint(0, capacity // 2)
                ))
        
        db.commit()
        print("✅ Demo data seeded successfully!")
        print("📧 Admin: admin@eventflow.com / admin123")
        print("📧 Organizer: organizer@eventflow.com / org123")
        print("📧 Attendee: attendee@eventflow.com / att123")
    
    except Exception as e:
        print(f"Seed error: {e}")
        db.rollback()
    finally:
        db.close()


# Serve frontend
@app.get("/")
async def root():
    return FileResponse("frontend/templates/index.html")

@app.get("/{path:path}")
async def catch_all(path: str):
    # Handle /edit-event/{id} -> edit-event.html
    if path.startswith("edit-event/"):
        return FileResponse("frontend/templates/create-event.html")
    # Handle /event/{id} -> event.html
    if path.startswith("event/"):
        return FileResponse("frontend/templates/event.html")
    
    html_file = Path(f"frontend/templates/{path}.html")
    if html_file.exists():
        return FileResponse(str(html_file))
    return FileResponse("frontend/templates/index.html")
