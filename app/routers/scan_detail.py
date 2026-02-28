from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
from loguru import logger

from app.connectors import mongo, minio

from app.utils.auth import get_current_user

router = APIRouter(
    prefix="/items",
    tags=["Item Detail"]
)


def _fmt(doc: dict) -> dict:
    """Convert ObjectId fields to strings."""
    doc["id"] = str(doc.pop("_id", ""))
    for key in ["item_id", "user_id"]:
        if key in doc and doc[key]:
            doc[key] = str(doc[key])
    return doc


def _fmt_dt(dt) -> str | None:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


@router.get("/{item_id}/scan-detail")
async def get_scan_detail(item_id: str, current_user=Depends(get_current_user)):
    """
    Full scan detail for an item:
    - item info
    - all scan logs with location + message
    - violation history
    - summary stats
    """
    try:
        # ── 1. Fetch item (must belong to current user) ──
        item = mongo.items.find_one({
            "_id": ObjectId(item_id),
            "user_id": str(current_user["_id"])
        })
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # ── 2. Scan logs (latest 100) ──
        raw_scans = list(
            mongo.scan_logs
            .find({"item_id": ObjectId(item_id)})
            .sort("scanned_at", -1)
            .limit(100)
        )

        scans = []
        for s in raw_scans:
            scans.append({
                "id":         str(s["_id"]),
                "scanned_at": _fmt_dt(s.get("scanned_at")),
                "message":    s.get("message"),
                "location": {
                    "lat": s.get("location", {}).get("lat"),
                    "lng": s.get("location", {}).get("lng"),
                } if s.get("location") else None,
            })

        # ── 3. Violations ──
        raw_violations = list(
            mongo.violations
            .find({"item_id": ObjectId(item_id)})
            .sort("reported_at", -1)
        )
        print(f"length of violation docs found :{len(raw_violations)}")
        violations = []
        for v in raw_violations:
            violations.append({
                "id":          str(v["_id"]),
                "type":        v.get("violation_type"),
                "message":     v.get("message"),
                "reported_at": _fmt_dt(v.get("reported_at")),
            })

        # ── 4. Stats ──
        total_scans     = mongo.scan_logs.count_documents({"item_id": ObjectId(item_id)})
        total_violations = mongo.violations.count_documents({"item_id": ObjectId(item_id)})

        # Scans with location (for map)
        scans_with_location = [s for s in scans if s["location"] and s["location"]["lat"]]

        # Last scan time
        last_scan = scans[0]["scanned_at"] if scans else None

        # Unique scan days
        scan_days = set()
        for s in scans:
            if s["scanned_at"]:
                scan_days.add(s["scanned_at"][:10])

        return {
            "status": True,
            "data": {
                "item": {
                    "id":          str(item["_id"]),
                    "name":        item["name"],
                    "description": item.get("description"),
                    "status":      item["status"],
                    "image":       item.get("image"),
                    "image_url": minio.uploads.safe_presigned_get(item.get("image")),
                    "qr_token":    item.get("qr_token"),
                    "qr_url": minio.qr_codes.safe_presigned_get(f"{item['qr_token']}.png"),
                    "created_at":  _fmt_dt(item.get("created_at")),
                },
                "scans":       scans,
                "violations":  violations,
                "stats": {
                    "total_scans":          total_scans,
                    "total_violations":     total_violations,
                    "scans_with_location":  len(scans_with_location),
                    "unique_scan_days":     len(scan_days),
                    "last_scan":            last_scan,
                    "latest_location":      scans_with_location[0]["location"] if scans_with_location else None,
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"scan_detail error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scan detail")