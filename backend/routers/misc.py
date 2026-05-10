from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from backend.models import (
    get_db, User, Event, Registration, Comment, Notification,
    RegistrationStatus, EventStatus, UserRole
)
from backend.schemas import (
    UserOut, CommentCreate, CommentOut, NotificationOut,
    AdminDashboard, OrganizerDashboard, AttendeeDashboard,
    EventListOut, RegistrationOut
)
from backend.auth import get_current_user, require_admin
from backend.utils import save_upload
from backend.routers.registrations import _build_reg_out

# ── Users ─────────────────────────────────────────────────────────────────────
users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return db.query(User).all()

@users_router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@users_router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    url = await save_upload(file, "avatars")
    current_user.avatar_url = url
    db.commit()
    return {"avatar_url": url}

@users_router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: UserRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    return {"message": f"Role updated to {role}"}

@users_router.put("/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    return {"is_active": user.is_active}


# ── Dashboard ──────────────────────────────────────────────────────────────────
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@dashboard_router.get("/admin", response_model=AdminDashboard)
async def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_events = db.query(func.count(Event.id)).scalar() or 0
    total_registrations = db.query(func.count(Registration.id)).scalar() or 0
    
    revenue_result = db.query(func.sum(Registration.amount_paid)).filter(
        Registration.status == RegistrationStatus.confirmed
    ).scalar()
    total_revenue = float(revenue_result or 0)
    
    recent_events_db = db.query(Event).options(
        joinedload(Event.organizer), joinedload(Event.ticket_tiers)
    ).order_by(Event.created_at.desc()).limit(5).all()
    
    recent_events = []
    for e in recent_events_db:
        reg_count = db.query(func.count(Registration.id)).filter(Registration.event_id == e.id).scalar() or 0
        prices = [t.price for t in e.ticket_tiers if t.is_active]
        recent_events.append(EventListOut(
            id=e.id, title=e.title, slug=e.slug, short_description=e.short_description,
            category=e.category, status=e.status, is_public=e.is_public, is_online=e.is_online,
            is_featured=e.is_featured, cover_image_url=e.cover_image_url,
            start_datetime=e.start_datetime, end_datetime=e.end_datetime,
            venue_city=e.venue_city, venue_country=e.venue_country,
            organizer=e.organizer, total_registrations=reg_count,
            min_price=min(prices) if prices else 0.0
        ))
    
    # Registrations by day (last 7 days)
    reg_by_day = []
    for i in range(7):
        day = datetime.utcnow() - timedelta(days=6-i)
        count = db.query(func.count(Registration.id)).filter(
            func.date(Registration.created_at) == day.date()
        ).scalar() or 0
        reg_by_day.append({"date": day.strftime("%b %d"), "count": count})
    
    return AdminDashboard(
        total_users=total_users, total_events=total_events,
        total_registrations=total_registrations, total_revenue=total_revenue,
        recent_events=recent_events, registrations_by_day=reg_by_day
    )

@dashboard_router.get("/organizer", response_model=OrganizerDashboard)
async def organizer_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.organizer, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Organizer or admin only")
    
    events_db = db.query(Event).options(
        joinedload(Event.organizer), joinedload(Event.ticket_tiers)
    ).filter(Event.organizer_id == current_user.id).all()
    
    event_ids = [e.id for e in events_db]
    
    total_registrations = 0
    total_revenue = 0.0
    events_out = []
    
    for e in events_db:
        reg_count = db.query(func.count(Registration.id)).filter(Registration.event_id == e.id).scalar() or 0
        rev = db.query(func.sum(Registration.amount_paid)).filter(
            Registration.event_id == e.id,
            Registration.status == RegistrationStatus.confirmed
        ).scalar() or 0.0
        total_registrations += reg_count
        total_revenue += float(rev)
        prices = [t.price for t in e.ticket_tiers if t.is_active]
        events_out.append(EventListOut(
            id=e.id, title=e.title, slug=e.slug, short_description=e.short_description,
            category=e.category, status=e.status, is_public=e.is_public, is_online=e.is_online,
            is_featured=e.is_featured, cover_image_url=e.cover_image_url,
            start_datetime=e.start_datetime, end_datetime=e.end_datetime,
            venue_city=e.venue_city, venue_country=e.venue_country,
            organizer=e.organizer, total_registrations=reg_count,
            min_price=min(prices) if prices else 0.0
        ))
    
    return OrganizerDashboard(
        total_events=len(events_db),
        total_registrations=total_registrations,
        total_revenue=total_revenue,
        events=events_out
    )

@dashboard_router.get("/attendee", response_model=AttendeeDashboard)
async def attendee_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.utcnow()
    
    regs = db.query(Registration).options(
        joinedload(Registration.event).joinedload(Event.organizer),
        joinedload(Registration.event).joinedload(Event.ticket_tiers),
        joinedload(Registration.ticket_tier),
    ).filter(Registration.attendee_id == current_user.id).all()
    
    upcoming = [r for r in regs if r.event and r.event.start_datetime >= now and r.status != RegistrationStatus.cancelled]
    past = [r for r in regs if r.event and r.event.start_datetime < now]
    
    return AttendeeDashboard(
        upcoming_registrations=[_build_reg_out(r, db) for r in upcoming],
        past_registrations=[_build_reg_out(r, db) for r in past]
    )


# ── Comments ───────────────────────────────────────────────────────────────────
comments_router = APIRouter(prefix="/comments", tags=["Comments"])

@comments_router.get("/event/{event_id}", response_model=List[CommentOut])
async def get_event_comments(event_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).options(
        joinedload(Comment.author),
        joinedload(Comment.replies).joinedload(Comment.author)
    ).filter(
        Comment.event_id == event_id,
        Comment.parent_id == None
    ).order_by(Comment.created_at.desc()).all()
    return comments

@comments_router.post("/event/{event_id}", response_model=CommentOut, status_code=201)
async def post_comment(
    event_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    comment = Comment(
        event_id=event_id,
        author_id=current_user.id,
        content=data.content,
        is_question=data.is_question,
        parent_id=data.parent_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Reload with relationships
    comment = db.query(Comment).options(
        joinedload(Comment.author), joinedload(Comment.replies)
    ).filter(Comment.id == comment.id).first()
    return comment

@comments_router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


# ── Notifications ─────────────────────────────────────────────────────────────
notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notifications_router.get("", response_model=List[NotificationOut])
async def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(20).all()

@notifications_router.put("/{notif_id}/read")
async def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(
        Notification.id == notif_id,
        Notification.user_id == current_user.id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "Marked as read"}

@notifications_router.put("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All marked as read"}
