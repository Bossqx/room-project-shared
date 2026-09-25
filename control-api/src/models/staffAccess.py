
from datetime import datetime, timedelta
# from multiprocessing.connection import Client
# from shlex import quote
# from typing import List, Optional
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB
#from src.util.utility import Util


class StaffAccess_Base(BaseModel):
    user_name: str="staff"
    room_no: str
    created_date: str = datetime.now().strftime("%Y-%m-%d")
    start_time: str = datetime.now().strftime("%H:%M")
    finish_time: str = (datetime.now() + timedelta(hours=1)).strftime("%H:%M")
    status_active: int=1


class StaffAccess_Controller():
    __tablename__ = 'staff_access'

    def __init__(self):
        self.__tableName__ = 'staff_access'
    
    def add(self, staff_access):
        db = DB(self.__tableName__)
        result = db.create(staff_access)
        del db
        return result
    
    def update(self, staff_access,id: int):
        # Implementation for updating staff access
        db = DB(self.__tableName__)
        result = db.update(staff_access, id)
        del db
        return result
    
    def delete(self, id: int):
        # Implementation for deleting staff access
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result
    
    def increase_pin_count(self,user_code:str):
        db=DB()
        sql=f"""UPDATE useraccess SET pin_count=pin_count+1 WHERE user_name=%s"""
        result=db.set_specific_sql(sql,(user_code,))
        del db
        return result
    
    def check_pin_count(self,user_code:str):
        db=DB()
        sql="SELECT pin_count FROM useraccess WHERE user_name=%s"
        result=db.get_specific_sql(sql,None,(user_code,)) 
        del db
        if len(result)>0 : 
            return result[0]
        return {"pin_count":0} 
    
    def get_id(self,room_no: str):
        # Implementation for getting staff access by room number and user name
        db = DB(self.__tableName__)
        today = datetime.now().strftime("%Y-%m-%d")
        sql = f"""SELECT 
            id 
        FROM staff_access 
        WHERE room_no = %s AND
        created_date = %s AND
        status_active=1"""
        results = db.get_specific_sql(sql, None, (room_no, today))
        del db
        if results:
            return results[0]['id']
        return 0
    
    def update_status(self, room_no: str, status_active: int):
        # Implementation for updating status of staff access
        id=self.get_id(room_no)
        db = DB()
        sql = """UPDATE staff_access
                 SET status_active = %s
                 WHERE id = %s"""
        result = db.set_specific_sql(sql,  (status_active, id,))
        del db
        return result

    
