
import requests
from datetime import datetime
from multiprocessing.connection import Client
from shlex import quote
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB


class Room_Base(BaseModel):
    room_no:str 
    panorama:str 
    room_type:str 
    floor_no:int
    building:str
    computer_no:int
    seat_no:int 
    created_at:datetime=None
    updated_at:datetime=datetime.now()
    
class Room_Image_Base(BaseModel):
    room_no:str
    image:str
    created_at:datetime=None
    updated_at:datetime=datetime.now()



class Room_Controller():
    __tablename__ = 'rooms'

    def __init__(self):
        self.__tableName__ = 'rooms'

    
    def add(self, room):
        db = DB(self.__tableName__)
        result = db.create(room)
        del db
        return result
    

        
    def update(self, room,id):
        db = DB(self.__tableName__)
        result = db.update(room, id)
        del db
        return result
    
    def delete(self, id):
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result
    
    def get_all(self):
        db=DB()
        sql=f"""SELECT
            id,
            room_no,
            panorama,
            room_type,
            floor_no,
            building,
            computer_no,
            seat_no
        FROM rooms"""
        results=db.get_specific_sql(sql)
        del db
        return results
    
    
    def get_room_images(self,room_no):
        db=DB()
        sql=f"""SELECT 
            image
        FROM room_images WHERE room_no=%s"""
        params=(room_no,)
        results=db.get_specific_sql(sql,None,params)
        del db
        return results
    
    def upload_panorama(self, room_no, panorama):
        db = DB(self.__tableName__)
        sql="UPDATE rooms SET panorama=%s WHERE room_no=%s"
        params=(panorama, room_no,)
        result = db.set_specific_sql(sql, params)
        del db
        return result
    
    def get_list_application_usage(self,room_no:str):
            db=DB()
            sql=f"""SELECT 
                A.code,
                A.application,
                A.icon 
            FROM applications A INNER JOIN 
            application_trans AT 
            ON A.code=AT.application 
            WHERE AT.room_no=%s 
            ORDER BY A.application """
            params=(room_no,)
            results=db.get_specific_sql(sql,None ,params)
            del db
            return results 
        
        
    def get_list_accessory_usage(self,room_no:str):
            db=DB()
            sql=f"""SELECT 
                A.code,
                A.accessory,
                A.icon 
            FROM accessories A INNER JOIN 
            accessory_trans AT 
            ON A.code=AT.accessory 
            WHERE AT.room_no=%s 
            ORDER BY A.code """
            params=(room_no,)
            results=db.get_specific_sql(sql,None ,params)
            del db
            return results 
    
    
    def get_power_usage(self,url_power:str):
        try:
            response = requests.get(url_power, verify=False, timeout=10)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Power usage fetch failed: {e}")
            return None
        except ValueError:
            return None

        if not result.get("success"):
            return None

        data = result.get("data") or {}
        return {
            "now_meter": data.get("NowMeter"),
            "date_consum": data.get("DateConsum"),
            "start_meter": data.get("StartMeter"),
            "timestamp": result.get("timestamp"),
        }


    def get_by_room(self,room_no):
        db=DB()
        sql=f"""SELECT 
            room_no,
            panorama,
            room_type,
            floor_no,
            building,
            computer_no,
            seat_no,
            power_monitor
        FROM rooms WHERE room_no=%s"""
        params=(room_no,)
        results=db.get_specific_sql(sql,None,params)
        result=results[0] if results else None
        result["images"]=self.get_room_images(room_no) if result else []
        result["application_usage"]=self.get_list_application_usage(room_no) if result else []
        result["accessory_usage"]=self.get_list_accessory_usage(room_no) if result else []
        result["power_usage"]=self.get_power_usage(result["power_monitor"]) if result else {}  
        del db
        return result




class Room_Image_Controller():
    __tablename__ = 'room_images'

    def __init__(self):
        self.__tableName__ = 'room_images'

    
    def add(self, room_image):
        db = DB(self.__tableName__)
        result = db.create(room_image)
        del db
        return result
    

        
    def update(self, room_image,id):
        db = DB(self.__tableName__)
        result = db.update(room_image, id)
        del db
        return result
    
    def delete(self, id):
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result
    

    def get_by_room(self,room_no):
        db=DB()
        sql=f"""SELECT 
            room_no,
            image
        FROM room_images WHERE room_no=%s"""
        params=(room_no,)
        results=db.get_specific_sql(sql,None,params)
        del db 
        return results