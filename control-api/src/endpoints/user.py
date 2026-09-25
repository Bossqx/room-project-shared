from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from fastapi import  HTTPException
from src.models.user import User_Base, User_Controller,Credential_Base
import os 
import urllib.parse
from PIL import Image
import io

router = APIRouter(
    prefix="/user",
    tags=["user"],
    responses={404: {"description": "Not found"}},
)

UPLOAD_DIR = "Profiles_Images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/get_user_type/{user_name}")
async def get_user_type(user_name: str):
    db = User_Controller()
    user_type = db.get_user_type(user_name)
    if user_type is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_type": user_type}

@router.get("/set_user_type/{user_name}/{user_type}")
async def set_user_type(user_name: str, user_type: str):
    db = User_Controller()
    result = db.set_user_type(user_name, user_type)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User type updated successfully"}

@router.put("/set_user_type/{user_name}/{user_type}")
async def set_user_type(user_name: str, user_type: str):
    db = User_Controller()
    result = db.set_user_type(user_name, user_type)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User type updated successfully"}


@router.get("/get_picture/{user_name}")
async def get_picture(user_name: str):
    db = User_Controller()
    result = db.get_picture(user_name)
    return result

@router.get("/check_image_exists/{uri}")
async def check_image_exist(url: str):
    encoded_url = urllib.parse.quote(url, safe=':/?&=')
    db= User_Controller()
    result = db.check_image_exists(encoded_url)
    return {"exists": result}

# @router.post("/upload_profile_image/{userName}")
# async def upload_profile_image(userName:str,file: UploadFile = File(...)):
#     if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
#         raise HTTPException(status_code=400, detail="Invalid file type. Only PNG and JPG are allowed.")
#     file_location = f"{userName}_{file.filename}"
#     with open(file_location, "wb") as buffer:
#         buffer.write(await file.read())
#     return {"filename": file.filename, "file_location": file_location}

@router.post("/upload_profile_image/{userName}")
async def upload_profile_image(userName: str, file: UploadFile = File(...)):
    if not file.filename.endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Invalid file type. Only PNG and JPG are allowed.")
    
    # Create the upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize if larger than 2000px (2K) on any dimension
        max_size = 2000
        if image.width > max_size or image.height > max_size:
            # Calculate new dimensions maintaining aspect ratio
            if image.width > image.height:
                new_width = max_size
                new_height = int((max_size / image.width) * image.height)
            else:
                new_height = max_size
                new_width = int((max_size / image.height) * image.width)
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save the resized image
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.jpg', '.jpeg']:
            file_extension = '.jpg'
        
        filename = f"{userName}_profile{file_extension}"
        file_location = os.path.join(UPLOAD_DIR, filename)
        
        # Save with quality optimization
        image.save(file_location, 'JPEG', quality=85, optimize=True)
        
        return {
            "filename": filename, 
            "file_location": filename,
            "dimensions": f"{image.width}x{image.height}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@router.get("/get_profile_image_by_filename/{filename}")
async def get_profile_image_by_filename(filename: str):

    try:
        # Construct the file path
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Check if the file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Profile image not found")
        
        # Return the file
        return FileResponse(
            path=file_path,
            media_type="image/jpeg"  # You might want to detect this based on file extension
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error retrieving profile image: {str(e)}")

@router.post("/add/")
async def add(user: User_Base):
    db_control = User_Controller()
    result = db_control.add(user.dict())
    return result

@router.put("/update/{id}")
async def update(user: User_Base, id: int):
    db_control = User_Controller()
    result = db_control.update(user.dict(), id)
    return result

@router.delete("/delete/{id}")
async def delete(id: int):
    db_control = User_Controller()
    result = db_control.delete(id)
    return result

@router.get("/get_data/{id}")
async def get_data(id: int):
    db_control = User_Controller()
    result = db_control.get_data(id)
    return result

@router.get("/get_id_by_username/{userName}")
async def get_id_by_username(userName: str):
    db_control = User_Controller()
    result = db_control.get_id_by_username(userName)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.get("/is_exist/{userName}")
async def is_exist(userName: str):
    db_control = User_Controller()
    result = db_control.is_exist(userName)
    return {"exists": result} 

@router.get("/authen/{userName}/{password}")
async def authen(userName: str, password: str):
    db_control = User_Controller()
    result = db_control.get_user(userName, password)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    else:
        if result["Flag"]:
            return result
        else:
            result = User_Controller().get_nrru_authen(userName, password)
            return result  
        
@router.post("/get_cos_credentials/")
async def get_cos_credentials(credential: Credential_Base):

    db_control = User_Controller()
    result = db_control.authenticate_nrru_sync(credential.user_name, credential.password)
    return result

@router.post("/nrru_authen/{userName}/{password}")
async def nrru_authen(userName: str, password: str):
    result = User_Controller().get_nrru_authen(userName, password)
    return result

@router.get("/get_user/{userName}/{password}")
async def get_user(userName: str, password: str):
    db_control = User_Controller()
    result = db_control.get_user(userName, password)
    return result
    # if not result:
    #     raise HTTPException(status_code=404, detail="User not found")
    # return result   

@router.get("/get_md5_hash/{text}")
async def get_md5_hash(text: str):
    from src.util.utility import Util
    hash_value = Util.hash_password(text)
    return {"hash": hash_value} 



