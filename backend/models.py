from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime,
    ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

from backend.config import settings

Base = declarative_base()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# ENUMS
# =========================

class UserRole(str, enum.Enum):
    admin = "admin"
    organizer = "organizer"
    attendee = "attendee"


class EventStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"
    completed = "completed"


class EventCategory(str, enum.Enum):
    conference = "conference"
    workshop = "workshop"
    concert = "concert"
    meetup = "meetup"
    webinar = "webinar"
    sports = "sports"
    arts = "arts"
    networking = "networking"
    other = "other"


class TicketType(str, enum.Enum):
    free = "free"
    paid = "paid"


class RegistrationStatus(str, enum.Enum):
    confirmed = "confirmed"
    waitlisted = "waitlisted"
    cancelled = "cancelled"
    checked_in = "checked_in"


# =========================
# USER MODEL
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)

    hashed_password = Column(String(255), nullable=False)

    role = Column(Enum(UserRole), default=UserRole.attendee)

    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    reset_token = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships

    events_organized = relationship(
        "Event",
        back_populates="organizer",
        foreign_keys="Event.organizer_id"
    )

    registrations = relationship(
        "Registration",
        back_populates="attendee",
        foreign_keys="Registration.attendee_id"
    )

    checked_in_registrations = relationship(
        "Registration",
        foreign_keys="Registration.checked_in_by"
    )

    comments = relationship(
        "Comment",
        back_populates="author",
        foreign_keys="Comment.author_id"
    )


# =========================
# EVENT MODEL
# =========================

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(500), nullable=False, index=True)
    slug = Column(String(600), unique=True, index=True)

    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)

    category = Column(Enum(EventCategory), default=EventCategory.other)
    status = Column(Enum(EventStatus), default=EventStatus.draft)

    is_public = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)

    recurrence_rule = Column(String(255), nullable=True)

    cover_image_url = Column(String(500), nullable=True)

    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)

    timezone = Column(String(100), default="UTC")

    venue_name = Column(String(255), nullable=True)
    venue_address = Column(String(500), nullable=True)
    venue_city = Column(String(100), nullable=True)
    venue_country = Column(String(100), nullable=True)

    online_url = Column(String(500), nullable=True)

    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships

    organizer = relationship(
        "User",
        back_populates="events_organized",
        foreign_keys=[organizer_id]
    )

    ticket_types = relationship(
        "TicketTier",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    registrations = relationship(
        "Registration",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    comments = relationship(
        "Comment",
        back_populates="event",
        cascade="all, delete-orphan"
    )


# =========================
# TICKET TIER MODEL
# =========================

class TicketTier(Base):
    __tablename__ = "ticket_tiers"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    ticket_type = Column(Enum(TicketType), default=TicketType.free)

    price = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")

    capacity = Column(Integer, nullable=True)

    sold_count = Column(Integer, default=0)
    waitlist_count = Column(Integer, default=0)

    sale_start = Column(DateTime, nullable=True)
    sale_end = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships

    event = relationship(
        "Event",
        back_populates="ticket_types"
    )

    registrations = relationship(
        "Registration",
        back_populates="ticket_tier"
    )


# =========================
# REGISTRATION MODEL
# =========================

class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    attendee_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    ticket_tier_id = Column(Integer, ForeignKey("ticket_tiers.id"), nullable=False)

    status = Column(
        Enum(RegistrationStatus),
        default=RegistrationStatus.confirmed
    )

    qr_code_url = Column(String(500), nullable=True)

    ticket_number = Column(String(100), unique=True, nullable=False)

    amount_paid = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")

    custom_field_responses = Column(JSON, default=dict)

    checked_in_at = Column(DateTime, nullable=True)

    checked_in_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships

    event = relationship(
        "Event",
        back_populates="registrations"
    )

    attendee = relationship(
        "User",
        back_populates="registrations",
        foreign_keys=[attendee_id]
    )

    checked_in_user = relationship(
        "User",
        foreign_keys=[checked_in_by]
    )

    ticket_tier = relationship(
        "TicketTier",
        back_populates="registrations"
    )


# =========================
# COMMENT MODEL
# =========================

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)

    content = Column(Text, nullable=False)

    is_question = Column(Boolean, default=False)
    is_answered = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships

    event = relationship(
        "Event",
        back_populates="comments"
    )

    author = relationship(
        "User",
        back_populates="comments",
        foreign_keys=[author_id]
    )

    replies = relationship(
        "Comment",
        backref="parent",
        remote_side=[id]
    )


# =========================
# NOTIFICATION MODEL
# =========================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    notification_type = Column(String(50), default="info")

    is_read = Column(Boolean, default=False)

    related_event_id = Column(Integer, ForeignKey("events.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# =========================
# CREATE TABLES
# =========================

def create_tables():
    Base.metadata.create_all(bind=engine)