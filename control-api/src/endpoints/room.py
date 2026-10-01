import os
import uuid
from pathlib import Path
from fastapi import APIRouter, File, UploadFile
from fastapi import  HTTPException
from fastapi.responses import FileResponse
from src.models.room import Room_Base,Room_Controller,Room_Image_Base,Room_Image_Controller

router = APIRouter(
    prefix="/room",
    tags=["room"],
    responses={404: {"description": "Not found"}},
)

PANO_UPLOAD_DIR = "PANO_IMAGES"
os.makedirs(PANO_UPLOAD_DIR, exist_ok=True)

ROOM_IMAGES_DIR = "ROOM_IMAGES"
os.makedirs(ROOM_IMAGES_DIR, exist_ok=True)


def _safe_upload_path(upload_dir: str, relative_path: str) -> Path:
    """Resolve an uploaded file path without allowing access outside its directory."""
    root = Path(upload_dir).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image path")
    if candidate == root:
        raise HTTPException(status_code=400, detail="Invalid image path")
    return candidate


@router.post("/add")
async def add_room(room: Room_Base):
    db = Room_Controller()
    result = db.add(room.dict())
    if not result:
        raise HTTPException(status_code=400, detail="Failed to add room")
    result["message"] = "Room added successfully"
    return result

@router.put("/update/{id}")
async def update_room(id: int, room: Room_Base):    
    db = Room_Controller()
    result = db.update(room.dict(), id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to update room")
    result["message"]="Room updated successfully"    
    return result

@router.delete("/delete/{id}")
async def delete_room(id: int):
    db = Room_Controller()
    result = db.delete(id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to delete room")
    result["message"]="Room deleted successfully"    
    return result   

@router.get("/get_room/{room_no}")
async def get_room(room_no:str):
    db = Room_Controller()
    result = db.get_by_room(room_no)
    if not result:
        raise HTTPException(status_code=404, detail="Room not found")
    return result

@router.get("/get_power_usage")
async def get_power_usage(url_power: str):
    db = Room_Controller()
    result = db.get_power_usage(url_power)
    if not result:
        raise HTTPException(status_code=404, detail="Power usage data not found")
    return result

@router.get("/get_all_rooms")
async def get_all_rooms():
    db = Room_Controller()
    results = db.get_all()
    if not results:
        raise HTTPException(status_code=404, detail="No rooms found")
    return results   

@router.get("/get_room_image/{image_path:path}")
async def get_room_image(image_path: str):
    file_path = os.path.join(ROOM_IMAGES_DIR, image_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path=file_path)

@router.get("/get_panorama/{room_no}")
async def get_panorama(room_no: str):
    db = Room_Controller()
    result = db.get_by_room(room_no)
    if not result or not result.get("panorama"):
        raise HTTPException(status_code=404, detail="Panorama not found")

    file_path = os.path.join(PANO_UPLOAD_DIR, result["panorama"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Panorama file not found")

    return FileResponse(path=file_path)


@router.delete("/delete_image/{image_path:path}")
async def delete_room_image(image_path: str):
    db = Room_Image_Controller()
    image = db.get_by_image(image_path)
    if not image:
        raise HTTPException(status_code=404, detail="Room image not found")

    file_path = _safe_upload_path(ROOM_IMAGES_DIR, image_path)
    try:
        if file_path.is_file():
            file_path.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete image file: {exc}")

    result = db.delete_by_image(image_path)
    if not result or not result.get("Flag"):
        raise HTTPException(status_code=500, detail="Failed to delete image record")

    # Remove the now-empty room directory, but never fail the request for it.
    try:
        file_path.parent.rmdir()
    except OSError:
        pass

    return {
        "message": "Room image deleted successfully",
        "image": image_path,
    }


@router.delete("/delete_panorama/{room_no}")
async def delete_panorama(room_no: str):
    db = Room_Controller()
    room = db.get_panorama(room_no)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    panorama = room.get("panorama")
    if not panorama:
        raise HTTPException(status_code=404, detail="Panorama not found")

    file_path = _safe_upload_path(PANO_UPLOAD_DIR, panorama)
    try:
        if file_path.is_file():
            file_path.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete panorama file: {exc}")

    result = db.clear_panorama(room_no)
    if not result or not result.get("Flag"):
        raise HTTPException(status_code=500, detail="Failed to clear panorama record")

    return {
        "message": "Panorama deleted successfully",
        "room_no": room_no,
        "panorama": panorama,
    }

@router.post("/upload_panorama/{room_no}")
async def upload_panorama(room_no: str, file: UploadFile = File(...)):
    if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG and JPG are allowed.")

    file_extension = os.path.splitext(file.filename)[1].lower()
    filename = f"{room_no}{file_extension}"
    file_location = os.path.join(PANO_UPLOAD_DIR, filename)

    try:
        contents = await file.read()
        with open(file_location, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving panorama: {str(e)}")

    db = Room_Controller()
    result = db.upload_panorama(room_no, filename)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to save panorama record")
    result["filename"] = filename
    result["message"] = "Panorama uploaded successfully"
    return result

@router.post("/upload_image/{room_no}")
async def upload_room_image(room_no: str, file: UploadFile = File(...)):
    if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG and JPG are allowed.")

    room_dir = os.path.join(ROOM_IMAGES_DIR, room_no)
    os.makedirs(room_dir, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex}{file_extension}"
    file_location = os.path.join(room_dir, filename)

    try:
        contents = await file.read()
        with open(file_location, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving image: {str(e)}")

    image_path = f"{room_no}/{filename}"
    db = Room_Image_Controller()
    result = db.add(Room_Image_Base(room_no=room_no, image=image_path).dict())
    if not result:
        raise HTTPException(status_code=400, detail="Failed to save image record")
    result["filename"] = filename
    result["image"] = image_path
    result["message"] = "Image uploaded successfully"
    return result

@router.post("/upload_images/{room_no}")
async def upload_room_images(room_no: str, files: list[UploadFile] = File(...)):
    room_dir = os.path.join(ROOM_IMAGES_DIR, room_no)
    os.makedirs(room_dir, exist_ok=True)

    db = Room_Image_Controller()
    uploaded = []
    for file in files:
        if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}. Only PNG and JPG are allowed.")

        file_extension = os.path.splitext(file.filename)[1].lower()
        filename = f"{uuid.uuid4().hex}{file_extension}"
        file_location = os.path.join(room_dir, filename)

        try:
            contents = await file.read()
            with open(file_location, "wb") as buffer:
                buffer.write(contents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving image {file.filename}: {str(e)}")

        image_path = f"{room_no}/{filename}"
        result = db.add(Room_Image_Base(room_no=room_no, image=image_path).dict())
        if not result:
            raise HTTPException(status_code=400, detail=f"Failed to save image record for {file.filename}")
        uploaded.append({"filename": filename, "image": image_path})

    return {"message": "Images uploaded successfully", "count": len(uploaded), "images": uploaded}
