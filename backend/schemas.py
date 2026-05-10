from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from backend.models import UserRole, EventStatus, EventCategory, TicketType, RegistrationStatus


# ── Auth ──────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    user: "UserOut"

class TokenData(BaseModel):
    user_id: Optional[int] = None


# ── User ──────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.attendee

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str
    role: UserRole
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


# ── Ticket Tier ───────────────────────────────────────────────────────────────
class TicketTierCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ticket_type: TicketType = TicketType.free
    price: float = 0.0
    currency: str = "USD"
    capacity: Optional[int] = None
    sale_start: Optional[datetime] = None
    sale_end: Optional[datetime] = None

class TicketTierOut(BaseModel):
    id: int
    event_id: int
    name: str
    description: Optional[str] = None
    ticket_type: TicketType
    price: float
    currency: str
    capacity: Optional[int] = None
    sold_count: int
    waitlist_count: int
    is_active: bool
    sale_start: Optional[datetime] = None
    sale_end: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ── Event ──────────────────────────────────────────────────────────────────────
class EventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: EventCategory = EventCategory.other
    status: EventStatus = EventStatus.draft
    is_public: bool = True
    is_online: bool = False
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    timezone: str = "UTC"
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    online_url: Optional[str] = None
    tags: List[str] = []
    custom_fields: List[Dict[str, Any]] = []
    ticket_tiers: List[TicketTierCreate] = []

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: Optional[EventCategory] = None
    status: Optional[EventStatus] = None
    is_public: Optional[bool] = None
    is_online: Optional[bool] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    online_url: Optional[str] = None
    tags: Optional[List[str]] = None

class EventOut(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: EventCategory
    status: EventStatus
    is_public: bool
    is_online: bool
    is_featured: bool
    is_recurring: bool
    cover_image_url: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    timezone: str
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    online_url: Optional[str] = None
    organizer_id: int
    organizer: Optional[UserOut] = None
    tags: List[str] = []
    ticket_tiers: List[TicketTierOut] = []
    created_at: datetime
    
    # Computed
    total_registrations: int = 0
    
    class Config:
        from_attributes = True

class EventListOut(BaseModel):
    id: int
    title: str
    slug: str
    short_description: Optional[str] = None
    category: EventCategory
    status: EventStatus
    is_public: bool
    is_online: bool
    is_featured: bool
    cover_image_url: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    venue_city: Optional[str] = None
    venue_country: Optional[str] = None
    organizer: Optional[UserOut] = None
    total_registrations: int = 0
    min_price: float = 0.0
    
    class Config:
        from_attributes = True


# ── Registration ───────────────────────────────────────────────────────────────
class RegistrationCreate(BaseModel):
    event_id: int
    ticket_tier_id: int
    custom_field_responses: Dict[str, Any] = {}

class RegistrationOut(BaseModel):
    id: int
    event_id: int
    attendee_id: int
    ticket_tier_id: int
    status: RegistrationStatus
    qr_code_url: Optional[str] = None
    ticket_number: str
    amount_paid: float
    currency: str
    checked_in_at: Optional[datetime] = None
    created_at: datetime
    event: Optional[EventListOut] = None
    ticket_tier: Optional[TicketTierOut] = None
    attendee: Optional[UserOut] = None
    
    class Config:
        from_attributes = True

class CheckInRequest(BaseModel):
    ticket_number: Optional[str] = None
    qr_data: Optional[str] = None


# ── Comment ────────────────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    is_question: bool = False
    parent_id: Optional[int] = None

class CommentOut(BaseModel):
    id: int
    event_id: int
    author_id: int
    parent_id: Optional[int] = None
    content: str
    is_question: bool
    is_answered: bool
    created_at: datetime
    author: Optional[UserOut] = None
    replies: List["CommentOut"] = []
    
    class Config:
        from_attributes = True

CommentOut.model_rebuild()


# ── Dashboard ──────────────────────────────────────────────────────────────────
class AdminDashboard(BaseModel):
    total_users: int
    total_events: int
    total_registrations: int
    total_revenue: float
    recent_events: List[EventListOut]
    registrations_by_day: List[Dict[str, Any]]

class OrganizerDashboard(BaseModel):
    total_events: int
    total_registrations: int
    total_revenue: float
    events: List[EventListOut]

class AttendeeDashboard(BaseModel):
    upcoming_registrations: List[RegistrationOut]
    past_registrations: List[RegistrationOut]


# ── Notification ───────────────────────────────────────────────────────────────
class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ── Pagination ─────────────────────────────────────────────────────────────────
class PaginatedEvents(BaseModel):
    items: List[EventListOut]
    total: int
    page: int
    per_page: int
    pages: int

Token.model_rebuild()
