from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from datetime import datetime

from backend.models import (
    get_db, User, Event, TicketTier, Registration, Notification,
    RegistrationStatus, EventStatus, UserRole
)
from backend.schemas import RegistrationCreate, RegistrationOut, CheckInRequest
from backend.auth import get_current_user
from backend.utils import generate_ticket_number, generate_qr_code

router = APIRouter(prefix="/registrations", tags=["Registrations"])


@router.post("", response_model=RegistrationOut, status_code=201)
async def register_for_event(
    reg_data: RegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == reg_data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status != EventStatus.published:
        raise HTTPException(status_code=400, detail="Event is not accepting registrations")
    
    tier = db.query(TicketTier).filter(
        TicketTier.id == reg_data.ticket_tier_id,
        TicketTier.event_id == reg_data.event_id,
        TicketTier.is_active == True
    ).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Ticket tier not found")
    
    # Check already registered
    existing = db.query(Registration).filter(
        Registration.event_id == reg_data.event_id,
        Registration.attendee_id == current_user.id,
        Registration.status.in_([RegistrationStatus.confirmed, RegistrationStatus.waitlisted])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this event")
    
    # Check capacity
    status = RegistrationStatus.confirmed
    if tier.capacity is not None and tier.sold_count >= tier.capacity:
        status = RegistrationStatus.waitlisted
        tier.waitlist_count += 1
    else:
        tier.sold_count += 1
    
    ticket_number = generate_ticket_number()
    qr_url = generate_qr_code(
        data=f"TICKET:{ticket_number}:EVENT:{reg_data.event_id}",
        filename=ticket_number
    )
    
    registration = Registration(
        event_id=reg_data.event_id,
        attendee_id=current_user.id,
        ticket_tier_id=reg_data.ticket_tier_id,
        status=status,
        qr_code_url=qr_url,
        ticket_number=ticket_number,
        amount_paid=tier.price if status == RegistrationStatus.confirmed else 0.0,
        currency=tier.currency,
        custom_field_responses=reg_data.custom_field_responses,
    )
    db.add(registration)
    
    # Notification
    msg = "confirmed" if status == RegistrationStatus.confirmed else "waitlisted"
    notif = Notification(
        user_id=current_user.id,
        title=f"Registration {msg}",
        message=f"Your registration for '{event.title}' has been {msg}. Ticket: {ticket_number}",
        notification_type="success" if status == RegistrationStatus.confirmed else "info",
        related_event_id=event.id,
    )
    db.add(notif)
    db.commit()
    db.refresh(registration)
    
    return _build_reg_out(registration, db)


@router.get("/my", response_model=List[RegistrationOut])
async def my_registrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    regs = db.query(Registration).options(
        joinedload(Registration.event).joinedload(Event.organizer),
        joinedload(Registration.ticket_tier),
    ).filter(Registration.attendee_id == current_user.id).order_by(
        Registration.created_at.desc()
    ).all()
    
    return [_build_reg_out(r, db) for r in regs]


@router.get("/event/{event_id}", response_model=List[RegistrationOut])
async def event_registrations(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    regs = db.query(Registration).options(
        joinedload(Registration.attendee),
        joinedload(Registration.ticket_tier),
    ).filter(Registration.event_id == event_id).all()
    
    return [_build_reg_out(r, db) for r in regs]


@router.post("/checkin", response_model=RegistrationOut)
async def check_in(
    data: CheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.attendee:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    ticket_number = data.ticket_number
    if data.qr_data and not ticket_number:
        parts = data.qr_data.split(":")
        if len(parts) >= 2:
            ticket_number = parts[1]
    
    if not ticket_number:
        raise HTTPException(status_code=400, detail="Ticket number required")
    
    reg = db.query(Registration).options(
        joinedload(Registration.attendee),
        joinedload(Registration.ticket_tier),
        joinedload(Registration.event),
    ).filter(Registration.ticket_number == ticket_number).first()
    
    if not reg:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if reg.status == RegistrationStatus.checked_in:
        raise HTTPException(status_code=400, detail="Already checked in")
    
    if reg.status != RegistrationStatus.confirmed:
        raise HTTPException(status_code=400, detail="Registration not confirmed")
    
    reg.status = RegistrationStatus.checked_in
    reg.checked_in_at = datetime.utcnow()
    reg.checked_in_by = current_user.id
    db.commit()
    db.refresh(reg)
    
    return _build_reg_out(reg, db)


@router.delete("/{registration_id}")
async def cancel_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    if reg.attendee_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if reg.status == RegistrationStatus.checked_in:
        raise HTTPException(status_code=400, detail="Cannot cancel after check-in")
    
    # Free up capacity
    tier = db.query(TicketTier).filter(TicketTier.id == reg.ticket_tier_id).first()
    if tier and reg.status == RegistrationStatus.confirmed:
        tier.sold_count = max(0, tier.sold_count - 1)
    elif tier and reg.status == RegistrationStatus.waitlisted:
        tier.waitlist_count = max(0, tier.waitlist_count - 1)
    
    reg.status = RegistrationStatus.cancelled
    db.commit()
    return {"message": "Registration cancelled"}


def _build_reg_out(reg: Registration, db) -> RegistrationOut:
    from backend.schemas import EventListOut, TicketTierOut, UserOut
    
    event_out = None
    if reg.event:
        e = reg.event
        prices = [t.price for t in e.ticket_tiers] if hasattr(e, 'ticket_tiers') and e.ticket_tiers else []
        event_out = EventListOut(
            id=e.id, title=e.title, slug=e.slug, short_description=e.short_description,
            category=e.category, status=e.status, is_public=e.is_public, is_online=e.is_online,
            is_featured=e.is_featured, cover_image_url=e.cover_image_url,
            start_datetime=e.start_datetime, end_datetime=e.end_datetime,
            venue_city=e.venue_city, venue_country=e.venue_country,
            organizer=e.organizer if hasattr(e, 'organizer') else None,
            total_registrations=0, min_price=min(prices) if prices else 0.0
        )
    
    return RegistrationOut(
        id=reg.id, event_id=reg.event_id, attendee_id=reg.attendee_id,
        ticket_tier_id=reg.ticket_tier_id, status=reg.status,
        qr_code_url=reg.qr_code_url, ticket_number=reg.ticket_number,
        amount_paid=reg.amount_paid, currency=reg.currency,
        checked_in_at=reg.checked_in_at, created_at=reg.created_at,
        event=event_out,
        ticket_tier=reg.ticket_tier,
        attendee=reg.attendee,
    )
