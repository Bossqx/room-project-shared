
from datetime import datetime, timedelta
import requests
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB
from datetime import datetime, timedelta


class Accessory_Base(BaseModel):
    code:str
    accessory:str
    icon:str

class Accessory_Child(BaseModel):
    room_no:str
    accessory:str


class Accessory_Controller():
    __tablename__ = 'accessory_trans'

    def __init__(self):
        self.__tableName__ = 'accessory_trans' 
        
    def set(self, accessory_trans: Accessory_Child):
        db = DB(self.__tableName__)
        result = db.create(accessory_trans.dict())
        del db
        return result
    
    def unset(self, room_no:str,accessory:str):
        db = DB(self.__tableName__)
        sql="""DELETE FROM accessory_trans WHERE room_no=%s AND accessory=%s"""
        params=(room_no, accessory)
        result = db.set_specific_sql(sql, params)
        del db
        return result
    
    def check_usage(self, room_no:str, accessory:str):
        db = DB(self.__tableName__)
        sql="""SELECT id FROM accessory_trans WHERE room_no=%s AND accessory=%s"""
        params=(room_no, accessory)
        result = db.get_specific_sql(sql,None,params)
        del db
        return len(result)>0

    def get_list_accessories(self,room_no:str=None):
        db=DB()
        sql=f"""SELECT 
            code,
            accessory,
            icon 
        FROM accessories     
        ORDER BY code """
        results=db.get_specific_sql(sql)
        del db
        
        for result in results:
            result['usage']=self.check_usage(room_no=room_no, accessory=result['code'])
        
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
     
    
