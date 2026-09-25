
from datetime import datetime
# from multiprocessing.connection import Client
# from shlex import quote
from typing import List
from pydantic import BaseModel, Field
# import requests
# import urllib3
from src.util.dbcontroller import DBController as DB
# from src.util.utility import Util
# from src.models.schedule import Teacher
import os

class ScheduleReplace_Base(BaseModel):
    schedule_id: str
    schedule_date: datetime = Field(default_factory=datetime.now)
    start_time: str
    finish_time: str
    request_by: str
    created_date: datetime = Field(default_factory=datetime.now)
    semester: str


class Teacher_Base(BaseModel):
    officerid:str 
    officerlogin:str 
    prefixname:str 
    officername:str 
    officersurname:str 


class SendSchedule_Base(BaseModel):
    roomcode: str
    weekday: str
    timeperiodfrom: str
    timeperiodto: str
    coursecode: str
    revisioncode:str 
    coursename: str
    periodfrom: str
    periodto: str
    teacher: List[Teacher_Base]
    id: str
    startTime: str= None
    finishTime: str = None
    status: int


class ScheduleReplace_Controller():
    __tablename__ = 'schedules_replace'

    def __init__(self):
        self.__tableName__ = 'schedules_replace'

    def add(self, schedule_replace):
        db = DB(self.__tableName__)
        result = db.create(schedule_replace)
        del db
        return result

    def update(self, schedule_replace, id):
        db = DB(self.__tableName__)
        result = db.update(schedule_replace, id)
        del db
        return result
    
    def delete(self, id):
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result
    