"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    message: str
    start_date: Optional[str] = None
    expiration_date: str
    username: str  # For authentication


class AnnouncementUpdate(BaseModel):
    message: Optional[str] = None
    start_date: Optional[str] = None
    expiration_date: Optional[str] = None
    username: str  # For authentication


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (current date is between start_date and expiration_date)"""
    now = datetime.now().isoformat()
    
    # Find announcements where current time is before expiration and after start (if set)
    announcements = list(announcements_collection.find({}))
    
    active_announcements = []
    for announcement in announcements:
        # Check if expired
        if announcement.get("expiration_date") and announcement["expiration_date"] < now:
            continue
        
        # Check if started (if start_date is set)
        if announcement.get("start_date") and announcement["start_date"] > now:
            continue
        
        # Convert ObjectId to string for JSON serialization
        announcement["_id"] = str(announcement["_id"])
        active_announcements.append(announcement)
    
    return active_announcements


@router.get("/all")
def get_all_announcements() -> List[Dict[str, Any]]:
    """Get all announcements (for management interface)"""
    announcements = list(announcements_collection.find({}))
    
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.post("/")
def create_announcement(announcement: AnnouncementCreate) -> Dict[str, Any]:
    """Create a new announcement (authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": announcement.username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Create announcement
    new_announcement = {
        "message": announcement.message,
        "start_date": announcement.start_date,
        "expiration_date": announcement.expiration_date,
        "created_by": announcement.username,
        "created_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(new_announcement)
    new_announcement["_id"] = str(result.inserted_id)
    
    return new_announcement


@router.put("/{announcement_id}")
def update_announcement(announcement_id: str, announcement: AnnouncementUpdate) -> Dict[str, Any]:
    """Update an announcement (authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": announcement.username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Build update data
    update_data = {}
    if announcement.message is not None:
        update_data["message"] = announcement.message
    if announcement.start_date is not None:
        update_data["start_date"] = announcement.start_date
    if announcement.expiration_date is not None:
        update_data["expiration_date"] = announcement.expiration_date
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Update announcement
    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    updated["_id"] = str(updated["_id"])
    
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (authenticated users only)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Delete announcement
    result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
