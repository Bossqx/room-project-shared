
from datetime import datetime
from multiprocessing.connection import Client
from shlex import quote
from pydantic import BaseModel
import requests
import urllib3
from src.util.dbcontroller import DBController as DB
from src.util.utility import Util
import os


# Configuration
VERIFY_SSL = os.getenv('VERIFY_SSL', 'false').lower() == 'true'

if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Credential_Base(BaseModel):
    user_name: str
    password: str

class User_Base(BaseModel):
    user_name: str
    name: str
    password: str
    description: str
    picture: str
    user_type:str="user"
    created_date: datetime=datetime.now()

class User_Controller():
    __tablename__ = 'users'

    def __init__(self):
        self.__tableName__ = 'users'
    
    def get_user_type(self,user_name):
        db = DB(self.__tableName__)
        sql = """SELECT
                    user_type
                FROM users
                WHERE user_name = %s
        """
        results = db.get_specific_sql(sql, None, (user_name,))
        del db
        if results:
            return results[0]['user_type']
        return None
    
    def get_picture(self,user_name):
        db = DB(self.__tableName__)
        sql = """SELECT
                    picture
                FROM users
                WHERE user_name = %s
        """
        results = db.get_specific_sql(sql, None, (user_name,))
        del db
        if results:
            return results[0]
        return None
    
    def set_user_type(self,user_name, user_type):
        db = DB(self.__tableName__)
        sql = """UPDATE users
                SET user_type = %s
                WHERE user_name = %s
        """
        result = db.set_specific_sql(sql, None, (user_type, user_name))
        del db
        return result
    
    
    def add(self, user):
        db = DB(self.__tableName__)
        user["password"] = Util.hash_password(user["password"])
        result = db.create(user)
        del db
        return result

    def update(self, user, id):
        db = DB(self.__tableName__)
        user["password"] = Util.hash_password(user["password"])   
        result = db.update(user, id)
        del db
        return result
    
    def delete(self, id):
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result
    
    def is_exist(self, userName):
        db = DB(self.__tableName__)
        sql = """SELECT
                    id
                FROM users
                WHERE user_name = %s
        """
        results = db.get_specific_sql(sql, None, (userName,))
        del db
        if results:
            return True
        return False
    
    def get_user_id(self,username):
        db = DB(self.__tableName__)
        sql = f"""SELECT
                    id
                FROM users
                WHERE user_name = '{username}'
        """
        results = db.get_specific_sql(sql)
        del db
        if results:
            return results[0]['id']
        return 0
    
    def get_data(self, id):
        db = DB(self.__tableName__)
        fields = [
            "id",
            "user_name",
            "name",
            "description",
            "picture"
        ]
        result = db.get_data(fields,id)
        del db
        return result
    
    def check_image_exists(self, url):
       # print("Checking if image exists at URL:", url)
        return Util.check_image_exists(url)

    def  get_is_exist(self,user_name:str):
        db=DB()
        sql="SELECT id FROM users WHERE user_name=%s"
        params=(user_name,)
        results=db.get_specific_sql(sql,None,params)
        del db 
        return {"flag":len(results)>0}
        #pass
    
    def get_user(self, user_name,password):
        db = DB()
        password = Util.hash_password(password)
        #print("Hashed password for comparison:", password)
        sql="""SELECT
                    id,
                    user_name,
                    name,
                    picture,
                    description,
                    user_type
                FROM users
                WHERE user_name = %s AND password = %s    
        """
        results = db.get_specific_sql(sql, None,(user_name, password))
        del db
        if results:
            result = results[0]
            return result
        else:
            return None 
        

    def get_id_by_username(self, user_name):
        db = DB()
        sql = """SELECT
                    id
                FROM users
                WHERE user_name = %s
        """
        results = db.get_specific_sql(sql, None, (user_name,))
        del db
        if results:
            return {"id": results[0]['id']}
        return 0

    def get_list_users(self):
        db = DB()
        sql = """SELECT
                    id,
                    user_name,
                    name,
                    picture,
                    description
                FROM users
        """
        results = db.get_specific_sql(sql)
        del db
        return results
    
    def get_md5_hash(self, password):
       encrypted_password = Util.hash_password(password)
       return encrypted_password
    

    
    def authenticate_nrru_sync(self,user_name, password): 
        """
        Synchronous version of NRRU authentication.
        """
        try:
            # Encode the parameters properly for URL
            encoded_user_name = quote(user_name)
            encoded_password = quote(password)
            
            # Construct the URL with parameters
            url = f"https://cos.nrru.ac.th/NRRUCredential/NRRUCredential1.php?userName={encoded_user_name}&password={encoded_password}"
            
            print(url)
            # Make HTTP request
            response = requests.get(url)
            
            # Check if response is ok
            if not response.ok:
                print(f"HTTP error! Status: {response.status_code}")
                #show_error_alert_sync("ชื่อผู้ใช้หรือรหัสผ่านของท่านไม่ถูกต้องกรุณาทดลองใหม่")
                return None
            
            # Parse JSON response
            data = response.json()
            
            # Check authentication status
            if data and len(data) > 0 and data[0].get('status', 0) > 0:
                obj_data = data[0]
                
                # Populate user profile
                user_profile = {
                    'username': obj_data.get('username'),
                    'fullname': f"{obj_data.get('prefixname')}  {obj_data.get('firstname')}  {obj_data.get('lastname')}",
                    'department_code1': obj_data.get('departmentcode1'),
                    'department_code2': obj_data.get('departmentcode2'),
                    'user_type': obj_data.get('usertype'),
                    'picture': obj_data.get('picture')
                }
                
                # Save user session
                #save_user_session_sync(user_profile)
                
                return user_profile
            else:
                #show_error_alert_sync("ชื่อผู้ใช้หรือรหัสผ่านของท่านไม่ถูกต้องกรุณาทดลองใหม่")
                return None
        
        except Exception as error:
            print(f'Authentication error: {error}')
            raise
        
    def get_nrru_authen(self,user_name: str, password: str):
        """
        Synchronous SOAP call function to be run in thread pool
        """
       # try:
            # Create SOAP client
        wsdl_url = "http://entrance.nrru.ac.th/nrruwebservice/nrruWebService_userLogin.php?wsdl"
        client = Client(wsdl_url)
        
        # Prepare parameters
        params = {
            'userlogin': user_name,
            'password': password
        }
        
        # Call the SOAP method
        result = client.service.getUserLogin(**params)
        return result
            
        # except Exception as e:
        #     raise Exception(f"SOAP call failed: {str(e)}")