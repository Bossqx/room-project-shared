
from datetime import datetime, timedelta
import requests
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB
from datetime import datetime, timedelta


class Semester_Base(BaseModel):
    academic_year:str
    semester:str 
    status:int=1
    created_date:datetime=datetime.now()


class Semester_Controller():
    __tablename__ = 'staff_access'

    def __init__(self):
        self.__tableName__ = 'semesters' 


    def reset_status(self):
        db=DB()
        sql="UPDATE semesters SET status=0"
        result=db.set_specific_sql(sql, None)
        del db
        return result
    
    def set_status(self,id:int):
        db=DB()
        sql="UPDATE semesters SET status=%s WHERE id=%s "
        params=(1,id)
        result=db.set_specific_sql(sql, params)
        del db
        return result
    
    def get_list_semester(self):
        db=DB()
        sql=f"""SELECT 
            id,
            academic_year,
            semester,status 
        FROM semesters 
        ORDER BY academic_year,semester """
        results=db.get_specific_sql(sql)
        del db
        return results 
     
    
    def add(self, semester):
        self.reset_status()
        db = DB(self.__tableName__)
        result = db.create(semester)
        del db
        return result
    
    def update(self, semester,id: int):
        # Implementation for updating staff access
        db = DB(self.__tableName__)
        result = db.update(semester, id)
        del db
        return result
    
    def delete(self, id: int):
        # Implementation for deleting staff access
        db = DB(self.__tableName__)
        result = db.delete(id)
        del db
        return result 
    

class Migration_Controller():


    def remove_all_schedules(self):
        db=DB("schedules")
        result=db.delete_all()
        del db
        return result

    
    
    def get_schedule_datasets(self, roomCode, startDate, finishDate,current_schedule):
        year_no = current_schedule['year_no']
        semester_no = current_schedule['semester']

        start = datetime.strptime(startDate, "%Y-%m-%d").date() if isinstance(startDate, str) else startDate
        finish = datetime.strptime(finishDate, "%Y-%m-%d").date() if isinstance(finishDate, str) else finishDate

        datasets = []
        current_date = start
        while current_date <= finish:
            date_str = current_date.strftime("%Y-%m-%d")
            schedule = self.get_schedule_migrate(year_no, semester_no, roomCode, date_str)
            if schedule is not None:
                datasets.append({
                    "date": date_str,
                    "schedule": schedule
                })
            current_date += timedelta(days=1)

        return datasets
    
    def get_schedule_migrate(self,yearNo,semester,roomCode,scheduleDate=datetime.now):
        url = f"https://cos.nrru.ac.th/mis_api/getRoom.php?yearNo={yearNo}&semester={semester}"
        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
            data = response.json()  # returns a list, not a dict
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except ValueError:
            print("Invalid JSON response")
            return None

        week_type_info = self.get_week_type_no(yearNo, semester)
        week_type = week_type_info.get('week_type') if week_type_info else None
        week_no = week_type_info.get('week_no') if week_type_info else None

        if scheduleDate is None:
            booking_date = datetime.now().strftime("%Y-%m-%d")
        elif isinstance(scheduleDate, str):
            booking_date = scheduleDate
        else:
            booking_date = scheduleDate.strftime("%Y-%m-%d")

        if scheduleDate is None:
            week_day = datetime.now().isoweekday()
        elif isinstance(scheduleDate, str):
            week_day = datetime.strptime(scheduleDate, "%Y-%m-%d").isoweekday()
        else:
            week_day = scheduleDate.isoweekday()  # date object

        if week_day==7:
            week_day=1
        else:
            week_day+=1
        keep = {'(คู่)', '**', ''} if week_type == 'E' else {'(คี่)', '**', ''}

        result = [
            item for item in data
            if item['roomcode'][:8] == roomCode
            and item['roomcode'][8:] in keep
            and (week_day is None or int(item['weekday']) == int(week_day))
        ]

        periods_map = self._get_periods_map()

        for item in result:
            item["week_type"]=week_type
            item["week_no"]=week_no
            item["schedule_date"]=booking_date
            item["roomcode"]=item['roomcode'][0:8]
            teacher = (item.get("teacher") or [{}])[0]
            item["teacher_name"]=teacher.get("prefixname","")+" "+teacher.get("officername","")+" "+teacher.get("officersurname","")
            item["user_name"]=teacher.get("officerlogin","")
            item.pop("teacher", None)
            from_period = periods_map.get(int(item['timeperiodfrom']), {})
            to_period   = periods_map.get(int(item['timeperiodto']), {})
            item['startTime']  = str(from_period.get('startTime',  ''))[:5]
            item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
            item["yearNo"]=yearNo
            item["semester"]=semester
            item["userCode"]=teacher.get("officerlogin","")

            
        return result

    #*****************************************************************
