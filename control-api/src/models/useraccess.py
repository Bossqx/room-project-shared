
from datetime import datetime
from shlex import quote
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB

class UserAccess_Base(BaseModel):
    user_name: str
    pwd: str="123456"
    pin_count:int=0
    created_date: datetime=datetime.now()

class UserAccess_Controller():
    __tablename__ = 'useraccess'

    def __init__(self):
        self.__tableName__ = 'useraccess'
    
    def add(self, user_access):
        if self.is_exist(user_access['user_name']):
            return {"Flag": False, "message": "User already exists"}
        db = DB(self.__tableName__)
        result = db.create(user_access)
        del db
        return result
    
    def update(self, user_access,id: int):
        # Implementation for updating user access
        db = DB(self.__tableName__)
        result = db.update(user_access, id)
        del db
        return result
    
    def delete(self, id: int):
        # Implementation for deleting user access
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result
    
    def is_change_valid_pin(self, user_name: str, pin: str):
        db = DB(self.__tableName__)
        sql = """SELECT 
                    pin_count, pwd 
                FROM useraccess 
                WHERE user_name = %s AND pwd = %s"""
        results = db.get_specific_sql(sql, None, (user_name, pin))
        del db
        if len(results)>0:
            return False
        return True 
          
      
    
    def change_pin(self, user_name: str, new_pin: str):
        if not self.is_change_valid_pin(user_name, new_pin):
            return {"Flag": False, "message": "New PIN must be different from your current PIN. Please choose another one."}
        db=DB()
        sql="UPDATE useraccess SET pwd=%s, pin_count=0 WHERE user_name=%s"
        result=db.set_specific_sql(sql, (new_pin, user_name))
        del db
        return result 
    
    def is_exist(self, user_name: str):
        db = DB(self.__tableName__)
        sql = """SELECT 
                    COUNT(*) as count 
                FROM useraccess 
                WHERE user_name = %s"""
        results = db.get_specific_sql(sql, None, (user_name,))
        del db
        if results and results[0]['count'] > 0:
            return True
        return False
    
    def get_id(self,user_name: str):
        # Implementation for getting user access by user name
        db = DB(self.__tableName__)
        today = datetime.now().strftime("%Y-%m-%d")
        sql = f"""SELECT 
            id 
        FROM useraccess 
        WHERE user_name = %s AND
        created_date = %s"""
        results = db.get_specific_sql(sql, None, (user_name, today))
        del db
        if results:
            return results[0]['id']
        return 0