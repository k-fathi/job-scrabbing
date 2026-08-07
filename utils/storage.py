"""
Storage utilities for JSON-based data persistence.
Handles applications tracking and CV metadata management.
"""

import json
import os
import uuid
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_BASE_DIR, "data")
UPLOADS_DIR = os.path.join(_BASE_DIR, "uploads", "cvs")
APPLICATIONS_FILE = os.path.join(DATA_DIR, "applications.json")
CV_METADATA_FILE = os.path.join(DATA_DIR, "cv_metadata.json")


def ensure_dirs():
    """Create necessary directories if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)


# ── Applications CRUD ──────────────────────────────────────────

def load_applications():
    """Load all applications from JSON file."""
    ensure_dirs()
    if os.path.exists(APPLICATIONS_FILE):
        try:
            with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_applications(applications):
    """Save all applications to JSON file."""
    ensure_dirs()
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, ensure_ascii=False, indent=2)


def add_application(app_data):
    """Add a new application entry and return it with generated id."""
    apps = load_applications()
    app_data["id"] = str(uuid.uuid4())
    app_data["created_at"] = datetime.now().isoformat()
    app_data["updated_at"] = datetime.now().isoformat()
    apps.append(app_data)
    save_applications(apps)
    return app_data


def update_application(app_id, updated_fields):
    """Update an existing application by ID."""
    apps = load_applications()
    for i, app in enumerate(apps):
        if app["id"] == app_id:
            apps[i].update(updated_fields)
            apps[i]["updated_at"] = datetime.now().isoformat()
            break
    save_applications(apps)


def delete_application(app_id):
    """Delete an application by ID."""
    apps = load_applications()
    apps = [a for a in apps if a["id"] != app_id]
    save_applications(apps)


# ── CV Metadata CRUD ───────────────────────────────────────────

def load_cv_metadata():
    """Load CV metadata from JSON file."""
    ensure_dirs()
    if os.path.exists(CV_METADATA_FILE):
        try:
            with open(CV_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"active_cv_id": None, "versions": []}


def save_cv_metadata(metadata):
    """Save CV metadata to JSON file."""
    ensure_dirs()
    with open(CV_METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def add_cv_version(label, filename, file_type, file_size_kb, notes="", drive_link=""):
    """Add a new CV version and set it as active."""
    metadata = load_cv_metadata()
    cv_id = str(uuid.uuid4())

    # Deactivate all existing versions
    for v in metadata["versions"]:
        v["is_active"] = False

    new_version = {
        "id": cv_id,
        "label": label,
        "filename": filename,
        "upload_date": datetime.now().isoformat(),
        "file_type": file_type,
        "file_size_kb": round(file_size_kb, 1),
        "is_active": True,
        "notes": notes,
        "drive_link": drive_link,
    }

    metadata["versions"].append(new_version)
    metadata["active_cv_id"] = cv_id
    save_cv_metadata(metadata)
    return new_version


def set_active_cv(cv_id):
    """Set a specific CV version as active."""
    metadata = load_cv_metadata()
    for v in metadata["versions"]:
        v["is_active"] = (v["id"] == cv_id)
    metadata["active_cv_id"] = cv_id
    save_cv_metadata(metadata)


def delete_cv_version(cv_id):
    """Delete a CV version and its file."""
    metadata = load_cv_metadata()
    # Find and remove the file
    for v in metadata["versions"]:
        if v["id"] == cv_id:
            fpath = os.path.join(UPLOADS_DIR, v["filename"])
            if os.path.exists(fpath):
                os.remove(fpath)
            break

    metadata["versions"] = [v for v in metadata["versions"] if v["id"] != cv_id]

    # If deleted the active one, set the latest as active
    if metadata["active_cv_id"] == cv_id:
        if metadata["versions"]:
            metadata["versions"][-1]["is_active"] = True
            metadata["active_cv_id"] = metadata["versions"][-1]["id"]
        else:
            metadata["active_cv_id"] = None

    save_cv_metadata(metadata)


def get_active_cv():
    """Get the currently active CV version dict, or None."""
    metadata = load_cv_metadata()
    for v in metadata["versions"]:
        if v.get("is_active"):
            return v
    return None


def get_cv_filepath(filename):
    """Get the full filepath for a stored CV file."""
    ensure_dirs()
    return os.path.join(UPLOADS_DIR, filename)


# ── Export / Import ────────────────────────────────────────────

def export_all_data():
    """Export all data as a single JSON dict (for backup)."""
    return {
        "applications": load_applications(),
        "cv_metadata": load_cv_metadata(),
        "exported_at": datetime.now().isoformat(),
    }


def import_all_data(data):
    """Import data from a previously exported JSON dict."""
    if "applications" in data:
        save_applications(data["applications"])
    if "cv_metadata" in data:
        save_cv_metadata(data["cv_metadata"])
