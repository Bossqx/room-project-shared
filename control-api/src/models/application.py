
from datetime import datetime, timedelta
import requests
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB
from datetime import datetime, timedelta


class Application_Base(BaseModel):
    code:str
    application:str
    icon:str

class Application_Child(BaseModel):
    room_no:str
    application:str


class Application_Controller():
    __tablename__ = 'application_trans'

    def __init__(self):
        self.__tableName__ = 'application_trans' 
        
    def set(self, application_trans: Application_Child):
        db = DB(self.__tableName__)
        result = db.create(application_trans.dict())
        del db
        return result
    
    def unset(self, room_no:str,application:str):
        db = DB(self.__tableName__)
        sql="""DELETE FROM application_trans WHERE room_no=%s AND application=%s"""
        params=(room_no, application)
        result = db.set_specific_sql(sql, params)
        del db
        return result
    
    def check_usage(self, room_no:str, application:str):
        db = DB(self.__tableName__)
        sql="""SELECT id FROM application_trans WHERE room_no=%s AND application=%s"""
        params=(room_no, application)
        result = db.get_specific_sql(sql,None,params)
        del db
        return len(result)>0

    def get_list_application(self,room_no:str=None):
        db=DB()
        sql=f"""SELECT 
            code,
            application,
            icon 
        FROM applications 
        ORDER BY application """
        results=db.get_specific_sql(sql)
        del db
        
        for result in results:
            result['usage']=self.check_usage(room_no=room_no, application=result['code'])
        
        return results
       

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
     
    
