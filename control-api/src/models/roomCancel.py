
from calendar import weekday
from datetime import datetime
from multiprocessing.connection import Client
from shlex import quote
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB

class RoomCancel_Base(BaseModel):
    uuid:str 
    request_user:str 
    room_no:str
    source_type:str='MIS Schedule' 
    created_date:datetime=datetime.now()


class RoomCancel_Controller():
    __tablename__ = 'cancel_rooms'

    def __init__(self):
        self.__tableName__ = 'cancel_rooms'


    def add(self, room_cancel):
        db = DB(self.__tableName__)
        result = db.create(room_cancel)
        del db
        return result
    
