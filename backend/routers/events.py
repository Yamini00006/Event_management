from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime

from backend.models import get_db, User, Event, TicketTier, Registration, EventStatus, EventCategory, UserRole
from backend.schemas import EventCreate, EventUpdate, EventOut, EventListOut, PaginatedEvents, TicketTierCreate
from backend.auth import get_current_user, get_current_user_optional, require_organizer_or_admin
from backend.utils import generate_unique_slug, save_upload

router = APIRouter(prefix="/events", tags=["Events"])


def event_to_list_out(event: Event, db: Session) -> dict:
    reg_count = db.query(func.count(Registration.id)).filter(
        Registration.event_id == event.id
    ).scalar() or 0
    
    min_price = 0.0
    if event.ticket_types:
        prices = [t.price for t in event.ticket_types if t.is_active]
        min_price = min(prices) if prices else 0.0
    
    return {
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        "organizer": event.organizer,
        "total_registrations": reg_count,
        "min_price": min_price,
    }


@router.get("", response_model=PaginatedEvents)
async def list_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    search: Optional[str] = None,
    category: Optional[EventCategory] = None,
    status: Optional[EventStatus] = None,
    is_online: Optional[bool] = None,
    is_free: Optional[bool] = None,
    city: Optional[str] = None,
    featured: Optional[bool] = None,
    start_after: Optional[datetime] = None,
    start_before: Optional[datetime] = None,
    organizer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = db.query(Event).options(
        joinedload(Event.organizer),
        joinedload(Event.ticket_types)
    )
    
    # By default only show public published events to non-admins
    if not current_user or current_user.role == UserRole.attendee:
        query = query.filter(Event.is_public == True, Event.status == EventStatus.published)
    elif current_user.role == UserRole.organizer:
        query = query.filter(
            or_(Event.organizer_id == current_user.id, 
                and_(Event.is_public == True, Event.status == EventStatus.published))
        )
    
    if search:
        query = query.filter(
            or_(
                Event.title.ilike(f"%{search}%"),
                Event.description.ilike(f"%{search}%"),
                Event.venue_city.ilike(f"%{search}%"),
            )
        )
    if category:
        query = query.filter(Event.category == category)
    if status:
        query = query.filter(Event.status == status)
    if is_online is not None:
        query = query.filter(Event.is_online == is_online)
    if city:
        query = query.filter(Event.venue_city.ilike(f"%{city}%"))
    if featured:
        query = query.filter(Event.is_featured == True)
    if start_after:
        query = query.filter(Event.start_datetime >= start_after)
    if start_before:
        query = query.filter(Event.start_datetime <= start_before)
    if organizer_id:
        query = query.filter(Event.organizer_id == organizer_id)
    if is_free is not None:
        if is_free:
            query = query.join(TicketTier).filter(TicketTier.price == 0)
        else:
            query = query.join(TicketTier).filter(TicketTier.price > 0)
    
    total = query.count()
    events = query.order_by(Event.start_datetime.asc()).offset((page - 1) * per_page).limit(per_page).all()
    
    items = []
    for event in events:
        reg_count = db.query(func.count(Registration.id)).filter(Registration.event_id == event.id).scalar() or 0
        prices = [t.price for t in event.ticket_types if t.is_active]
        item = EventListOut(
            id=event.id, title=event.title, slug=event.slug,
            short_description=event.short_description, category=event.category,
            status=event.status, is_public=event.is_public, is_online=event.is_online,
            is_featured=event.is_featured, cover_image_url=event.cover_image_url,
            start_datetime=event.start_datetime, end_datetime=event.end_datetime,
            venue_city=event.venue_city, venue_country=event.venue_country,
            organizer=event.organizer, total_registrations=reg_count,
            min_price=min(prices) if prices else 0.0
        )
        items.append(item)
    
    return PaginatedEvents(
        items=items, total=total, page=page, per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_organizer_or_admin)
):
    slug = generate_unique_slug(event_data.title, db, Event)
    
    event = Event(
        title=event_data.title,
        slug=slug,
        description=event_data.description,
        short_description=event_data.short_description,
        category=event_data.category,
        status=event_data.status,
        is_public=event_data.is_public,
        is_online=event_data.is_online,
        is_recurring=event_data.is_recurring,
        recurrence_rule=event_data.recurrence_rule,
        start_datetime=event_data.start_datetime,
        end_datetime=event_data.end_datetime,
        timezone=event_data.timezone,
        venue_name=event_data.venue_name,
        venue_address=event_data.venue_address,
        venue_city=event_data.venue_city,
        venue_country=event_data.venue_country,
        online_url=event_data.online_url,
        organizer_id=current_user.id,
        tags=event_data.tags,
        custom_fields=event_data.custom_fields,
    )
    db.add(event)
    db.flush()
    
    for tier_data in event_data.ticket_tiers:
        tier = TicketTier(
            event_id=event.id,
            name=tier_data.name,
            description=tier_data.description,
            ticket_type=tier_data.ticket_type,
            price=tier_data.price,
            currency=tier_data.currency,
            capacity=tier_data.capacity,
            sale_start=tier_data.sale_start,
            sale_end=tier_data.sale_end,
        )
        db.add(tier)
    
    db.commit()
    db.refresh(event)
    
    reg_count = 0
    return _build_event_out(event, reg_count)


@router.get("/featured", response_model=List[EventListOut])
async def get_featured_events(db: Session = Depends(get_db)):
    events = db.query(Event).options(
        joinedload(Event.organizer), joinedload(Event.ticket_types)
    ).filter(
        Event.is_featured == True,
        Event.status == EventStatus.published,
        Event.is_public == True
    ).limit(6).all()
    
    result = []
    for event in events:
        reg_count = db.query(func.count(Registration.id)).filter(Registration.event_id == event.id).scalar() or 0
        prices = [t.price for t in event.ticket_types if t.is_active]
        result.append(EventListOut(
            id=event.id, title=event.title, slug=event.slug,
            short_description=event.short_description, category=event.category,
            status=event.status, is_public=event.is_public, is_online=event.is_online,
            is_featured=event.is_featured, cover_image_url=event.cover_image_url,
            start_datetime=event.start_datetime, end_datetime=event.end_datetime,
            venue_city=event.venue_city, venue_country=event.venue_country,
            organizer=event.organizer, total_registrations=reg_count,
            min_price=min(prices) if prices else 0.0
        ))
    return result


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    event = db.query(Event).options(
        joinedload(Event.organizer),
        joinedload(Event.ticket_types),
    ).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Access control
    if not event.is_public:
        if not current_user:
            raise HTTPException(status_code=403, detail="Private event")
        if current_user.role == UserRole.attendee and event.organizer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Private event")
    
    reg_count = db.query(func.count(Registration.id)).filter(Registration.event_id == event.id).scalar() or 0
    return _build_event_out(event, reg_count)


@router.put("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_dict = event_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(event, key, value)
    
    db.commit()
    db.refresh(event)
    
    reg_count = db.query(func.count(Registration.id)).filter(Registration.event_id == event.id).scalar() or 0
    return _build_event_out(event, reg_count)


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}


@router.post("/{event_id}/cover-image")
async def upload_cover_image(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    url = await save_upload(file, "events")
    event.cover_image_url = url
    db.commit()
    return {"cover_image_url": url}


@router.put("/{event_id}/feature")
async def toggle_featured(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.is_featured = not event.is_featured
    db.commit()
    return {"is_featured": event.is_featured}


def _build_event_out(event: Event, reg_count: int) -> EventOut:
    return EventOut(
        id=event.id, title=event.title, slug=event.slug,
        description=event.description, short_description=event.short_description,
        category=event.category, status=event.status, is_public=event.is_public,
        is_online=event.is_online, is_featured=event.is_featured,
        is_recurring=event.is_recurring, cover_image_url=event.cover_image_url,
        start_datetime=event.start_datetime, end_datetime=event.end_datetime,
        timezone=event.timezone, venue_name=event.venue_name,
        venue_address=event.venue_address, venue_city=event.venue_city,
        venue_country=event.venue_country, online_url=event.online_url,
        organizer_id=event.organizer_id, organizer=event.organizer,
        tags=event.tags or [], ticket_tiers=event.ticket_types,
        created_at=event.created_at, total_registrations=reg_count
    )
