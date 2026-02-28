# from bson import ObjectId
# from loguru import logger
# from app.database import scan_logs_collection, violation_logs_collection, items_collection
# from app.connectors import mongo, minio

# async def get_scan_history(user_id):
#     try:
#         logger.info(f"Fetching scan history for user_id: {user_id}, {type(user_id)}")
        
#         # **FIX 1:** Cursor ko LIST mein convert karo for len()
#         user_items = list(mongo.items.find({"user_id": user_id}))
#         item_ids = [ObjectId(doc['_id']) for doc in user_items]
        
#         logger.debug(f"Found {len(item_ids)} items for user: {user_id}")
        
#         if not item_ids:
#             logger.warning(f"No items found for user: {user_id}")
#             return False, {
#                 "status": True, "status_code": 200,
#                 "message": "No scan history available", "data": []
#             }
        
#         # **FIX 2:** cursor.to_list() use karo - SYNC & works in async
#         logger.debug(f"Querying scan_logs for item_ids: {item_ids[:3]}{'...' if len(item_ids)>3 else ''}")
#         scans = []
#         scans_cursor = mongo.scan_logs.find({"item_id": {"$in": item_ids}}).sort("scanned_at", -1)
#         scans_docs = list(scans_cursor)  # Convert to list first
        
#         for doc in scans_docs:
#             scans.append({
#                 "item_id": str(doc["item_id"]),
#                 "message": doc.get("message"),
#                 "scanned_at": doc["scanned_at"]
#             })
        
#         logger.info(f"✅ Fetched {len(scans)} scan records")
#         return False, {
#             "status": True, "status_code": 200,
#             "message": "Scan history fetched", "data": scans
#         }
    
#     except Exception as e:
#         logger.exception(f"❌ Scan history error: {e}")
#         return True, {"status": False, "status_code": 500, "message": str(e), "data": []}


# async def get_violation_history(user_id):
#     try:
#         logger.info(f"Fetching violation history for user_id: {user_id}")
        
#         # **FIX 1:** Consistent - list() for items
#         user_items = list(mongo.items.find({"user_id": str(user_id)}))
#         item_ids = [ObjectId(doc['_id']) for doc in user_items]
        
#         logger.debug(f"Found {len(item_ids)} items for user: {user_id}")
        
#         if not item_ids:
#             logger.warning(f"No items found for user: {user_id}")
#             return False, {
#                 "status": True, "status_code": 200,
#                 "message": "No violation history available", "data": []
#             }
        
#         # **FIX 2:** Same fix for violations
#         logger.debug(f"Querying violations for item_ids: {item_ids[:3]}{'...' if len(item_ids)>3 else ''}")
#         violations_cursor = mongo.violations.find(
#             {"item_id": {"$in": item_ids}}
#         ).sort("reported_at", -1)
        
#         violations_docs = list(violations_cursor)  # ✅ This works!
#         violations = []
#         for doc in violations_docs:
#             violations.append({
#                 "item_id": str(doc["item_id"]),
#                 "type": doc["violation_type"],
#                 "message": doc.get("message"),
#                 "reported_at": doc["reported_at"]
#             })
        
#         logger.info(f"✅ Fetched {len(violations)} violation records")
#         return False, {
#             "status": True, "status_code": 200,
#             "message": "Violation history fetched", "data": violations
#         }
    
#     except Exception as e:
#         logger.exception(f"❌ Violation history error: {e}")
#         return True, {"status": False, "status_code": 500, "message": str(e), "data": []}


from bson import ObjectId
from typing import Optional
from loguru import logger
from app.database import scan_logs_collection, violation_logs_collection, items_collection
from app.connectors import mongo, minio


async def get_scan_history(
    user_id: str, 
    page: int = 1, 
    limit: int = 10
):
    try:
        logger.info(f"Fetching scan history for user_id: {user_id}, page: {page}, limit: {limit}")
        
        # Validate pagination params
        page = max(1, page)
        limit = max(1, min(100, limit))  # Max 100 per page
        
        skip = (page - 1) * limit
        
        # Get all user items once
        user_items = list(mongo.items.find({"user_id": user_id}))
        if not user_items:
            logger.warning(f"No items found for user: {user_id}")
            return False, {
                "status": True, "status_code": 200,
                "message": "No scan history available",
                "data": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": 0,
                    "total_items": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
        
        # Create lookup dictionary
        item_lookup = {ObjectId(doc['_id']): doc for doc in user_items}
        item_ids = list(item_lookup.keys())
        
        logger.debug(f"Found {len(item_ids)} items for user: {user_id}")
        
        # Get TOTAL count first for pagination
        total_scans = mongo.scan_logs.count_documents({"item_id": {"$in": item_ids}})
        total_pages = (total_scans + limit - 1) // limit
        
        if total_scans == 0:
            return False, {
                "status": True, "status_code": 200,
                "message": "No scan history available",
                "data": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": 0,
                    "total_items": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
        
        # Get paginated scan logs
        logger.debug(f"Querying scan_logs page {page}/{total_pages}")
        scans_cursor = mongo.scan_logs.find(
            {"item_id": {"$in": item_ids}}
        ).sort("scanned_at", -1).skip(skip).limit(limit)
        
        scans_docs = list(scans_cursor)
        
        # Combine with item details
        scans = []
        for doc in scans_docs:
            item_id = doc["item_id"]
            item_details = item_lookup.get(item_id, {})
            
            scans.append({
                "item_id": str(item_id),
                "item_name": item_details.get("name", "Unknown Item"),
                "item_type": item_details.get("item_type", "unknown"),
                "item_status": item_details.get("status", "UNKNOWN"),
                "qr_token": item_details.get("qr_token", ""),
                "message": doc.get("message", ""),
                "scanned_at": doc["scanned_at"],
                "location": doc.get("location", {})
            })
        
        logger.info(f"✅ Fetched {len(scans)} scan records (page {page}/{total_pages})")
        
        return False, {
            "status": True, "status_code": 200,
            "message": "Scan history fetched successfully",
            "data": scans,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_items": total_scans,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    except Exception as e:
        logger.exception(f"❌ Scan history error: {e}")
        return True, {
            "status": False, 
            "status_code": 500, 
            "message": str(e), 
            "data": [],
            "pagination": None
        }


async def get_violation_history(
    user_id: str, 
    page: int = 1, 
    limit: int = 10
):
    try:
        logger.info(f"Fetching violation history for user_id: {user_id}, page: {page}, limit: {limit}")
        
        # Validate pagination params
        page = max(1, page)
        limit = max(1, min(100, limit))
        skip = (page - 1) * limit
        
        # Get all user items once
        user_items = list(mongo.items.find({"user_id": str(user_id)}))
        if not user_items:
            logger.warning(f"No items found for user: {user_id}")
            return False, {
                "status": True, "status_code": 200,
                "message": "No violation history available",
                "data": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": 0,
                    "total_items": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
        
        # Create lookup dictionary
        item_lookup = {ObjectId(doc['_id']): doc for doc in user_items}
        item_ids = list(item_lookup.keys())
        
        logger.debug(f"Found {len(item_ids)} items for user: {user_id}")
        
        # Get TOTAL count first
        total_violations = mongo.violations.count_documents({"item_id": {"$in": item_ids}})
        total_pages = (total_violations + limit - 1) // limit
        
        if total_violations == 0:
            return False, {
                "status": True, "status_code": 200,
                "message": "No violation history available",
                "data": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_pages": 0,
                    "total_items": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
        
        # Get paginated violations
        logger.debug(f"Querying violations page {page}/{total_pages}")
        violations_cursor = mongo.violations.find(
            {"item_id": {"$in": item_ids}}
        ).sort("reported_at", -1).skip(skip).limit(limit)
        
        violations_docs = list(violations_cursor)
        
        # Combine with item details
        violations = []
        for doc in violations_docs:
            item_id = doc["item_id"]
            item_details = item_lookup.get(item_id, {})
            
            violations.append({
                "item_id": str(item_id),
                "item_name": item_details.get("name", "Unknown Item"),
                "item_type": item_details.get("item_type", "unknown"),
                "item_status": item_details.get("status", "UNKNOWN"),
                "qr_token": item_details.get("qr_token", ""),
                "violation_type": doc["violation_type"],
                "message": doc.get("message", ""),
                "reported_at": doc["reported_at"],
                "location": doc.get("location", {})
            })
        
        logger.info(f"✅ Fetched {len(violations)} violation records (page {page}/{total_pages})")
        
        return False, {
            "status": True, "status_code": 200,
            "message": "Violation history fetched successfully",
            "data": violations,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "total_items": total_violations,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    except Exception as e:
        logger.exception(f"❌ Violation history error: {e}")
        return True, {
            "status": False, 
            "status_code": 500, 
            "message": str(e), 
            "data": [],
            "pagination": None
        }
