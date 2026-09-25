
import base64
import json
import os
import uuid
from datetime import datetime, timedelta
# from multiprocessing.connection import Client
# from shlex import quote
import requests
from typing import List, Optional
from fastapi import HTTPException
from pydantic import BaseModel
from src.util.dbcontroller import DBController as DB
# from src.util.utility import Util
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class Teacher(BaseModel):
    officerlogin: Optional[str] = None
    name: Optional[str] = None


class ScheduleItem(BaseModel):
    roomcode: str
    weekday: str
    timeperiodfrom: str
    timeperiodto: str
    coursecode: str
    coursename: str
    revisioncode: Optional[str] = None
    periodfrom: str
    periodto: str
    teacher: List[Teacher]
    id: str
    startTime: Optional[str] = None
    finishTime: Optional[str] = None
    status: int
    



class Schedule_Controller():
    __tablename__ = 'semesters'

    def __init__(self):
        self.__tableName__ = 'semesters'

    def delete_schedule_by_id(self, rowId: str,source_type:str):
        db = DB()
        # The same two sources are spelled several ways across the codebase:
        # the MIS side arrives as 'MIS', 'MIS Schedule' or 'schedule', the
        # booking side as 'BOOKING' or 'booking'. Normalize before matching so
        # any of them reaches the right table.
        normalized = (source_type or '').strip().lower()
        if normalized in ('mis', 'mis schedule', 'schedule'):
            sql = f"DELETE FROM schedules WHERE id = %s"
            result=db.set_specific_sql (sql,(rowId,))
            print(sql)       
            del db
            return result 
        elif normalized == 'booking':
            sql = f"DELETE FROM room_usages WHERE id = %s"
            result=db.set_specific_sql (sql,(rowId,))
            print(sql)
            del db
            return result
        else:
            raise ValueError(
                f"Invalid source type {source_type!r}. "
                "Must be 'MIS'/'MIS Schedule'/'schedule' or 'BOOKING'/'booking'."
            )
        
       
    
    
    def get_schedule_by_id(self, rowId: str):
        db = DB()
        sql = f"""SELECT *
        FROM (
            SELECT
                CONCAT('M', CAST(id AS CHAR)) AS id,
                coursecode AS subjectcode,
                coursename AS coursename,
                roomcode        AS roomno,
                schedule_date,
                startTime,
                finishTime,
                semester,
                yearNo,
                userCode        AS instructure,
                'MIS'           AS source
            FROM `db_roomcontrol`.`schedules`

            UNION ALL

            SELECT
                CONCAT('B',CAST(id AS CHAR)) AS id,
                subject_code    AS subjectcode,
                subject_code    AS coursename,
                room_no         AS roomno,
                created_date    AS schedule_date,
                start_time      AS startTime,
                finish_time     AS finishTime,
                semester,
                year_no         AS yearNo,
                user_name       AS instructure,
                'BOOKING'       AS source
            FROM `db_roomcontrol`.`room_usages`
        ) AS V
        WHERE id = %s"""
        print(sql)
        results = db.get_specific_sql(sql, None, (rowId,))
        del db
        if not results:
            return None
        return results[0]
    
    
    def get_teacher_profile(self, user_code: str) -> list:
        url = f"https://cos.nrru.ac.th/NRRUCredential/NRRUGetProfileByUser.php?userCode={user_code}"
        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Profile fetch failed: {e}")
            return []
        except ValueError:
            return []

        return [
            {
                "officerid":      str(p.get("staffid", "")),
                "officerlogin":   p.get("username", ""),
                "prefixname":     p.get("prefixname", ""),
                "officername":    p.get("firstname", ""),
                "officersurname": p.get("lastname", ""),
            }
            for p in data
        ]

    def get_active_semester(self):
        db=DB()
        sql=f"""SELECT 
            academic_year AS year_no,
            semester 
        FROM semesters 
        WHERE status=1"""
        results=db.get_specific_sql(sql)
        if len(results)>0:
            return results[0]
        else:
            return None


    def get_dates_on_week(self):
        today = datetime.now()
        # Monday-start week
        start_of_week = today - timedelta(days=today.weekday())
        week_dates = [(start_of_week + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        return week_dates

    def get_week_date_range(self, scheduleDate=None):
        if scheduleDate is None:
            date_obj = datetime.now()
        elif isinstance(scheduleDate, str):
            date_obj = datetime.strptime(scheduleDate, "%Y-%m-%d")
        else:
            date_obj = scheduleDate

        # Monday-start week
        first_date_of_week = date_obj - timedelta(days=date_obj.weekday())
        last_date_of_week  = first_date_of_week + timedelta(days=6)
        first_date = first_date_of_week.strftime("%Y-%m-%d")
        last_date  = last_date_of_week.strftime("%Y-%m-%d")
        return first_date, last_date

    def get_period(self, period_no):
        db = DB('periods')
        sql = """SELECT period, startTime, finishTime FROM periods WHERE period = %s"""
        results = db.get_specific_sql(sql, None, (period_no,))
        del db
        if not results:
            return None
        return results[0]

    def get_current(self):
        db = DB(self.__tableName__)
        sql = """SELECT academic_year AS year_no, semester FROM semesters
                 WHERE status =1"""
        results = db.get_specific_sql(sql)
        del db
        if not results:
            return None
        return results[0]
    
  
    
    def get_booking_db(self,room_code:str):
        db=DB()
        today=datetime.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom, 
                    T2.period AS timeperiodfrom,
                    false As isExist
        FROM room_usages A  LEFT OUTER JOIN 
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN 
        periods T2 ON A.finish_time=T2.finishTime
        WHERE A.room_no=%s AND DATE(created_date)=%s AND A.objective<>'MIS Schedule'"""
        params=(room_code,today)
        results=db.get_specific_sql(sql,None,params)
        for item in results:
            user_code = item.get('teacher', '')
            item['teacher_name'] = self.get_teacher_profile(user_code)
        return results
    
    def get_schedule_rooms_by_date(self,booking_date:str):
        db=DB()
        #today=datetime.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom, 
                    T2.period AS timeperiodfrom,
                    false As isExist
        FROM room_usages A LEFT OUTER JOIN 
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN 
        periods T2 ON A.finish_time=T2.finishTime
        WHERE DATE(booking_date)=%s 
        AND A.objective<>'MIS Schedule' ORDER BY A.start_time"""
        params=(booking_date,)
        results=db.get_specific_sql(sql,None,params)
        del db 
        return results 

    
    def get_booking_db_date(self,room_code:str,booking_date:str):
        db=DB()
        #today=datetime.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id AS rowId,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    A.weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom, 
                    T2.period AS timeperiodfrom,
                    'booking' AS objective,
                    false As isExist,
                    A.usage_status
        FROM room_usages A  LEFT OUTER JOIN 
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN 
        periods T2 ON A.finish_time=T2.finishTime
        WHERE A.room_no=%s AND DATE(booking_date)=%s AND A.objective<>'MIS Schedule'"""
        params=(room_code,booking_date,)
        results=db.get_specific_sql(sql,None,params)
        for item in results:
            user_code = item.get('teacher', '')
            item['teacher'] = self.get_teacher_profile(user_code)
        return results
    
    def get_booking_range_db(self,room_code:str,start_date:str,finish_date:str):
        db=DB()
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.user_name AS userCode,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    A.weekday, 
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    A.booking_date AS schedule_date,
                    T1.period AS timeperiodfrom,
                    T2.period AS timeperiodto,
                    false As isExist,
                    'booking' AS objective,
                    A.usage_status
        FROM room_usages A  LEFT OUTER JOIN
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN
        periods T2 ON A.finish_time=T2.finishTime
        WHERE A.room_no='{room_code}' AND 
        DATE(booking_date) 
        BETWEEN '{start_date}' AND '{finish_date}'
        AND A.objective<>'MIS Schedule'"""
        
        #print(sql)
        #CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
        
       
       
        results=db.get_specific_sql(sql)
        #print(results)
        for item in results:
             user_code = item.get('teacher', '')
             obj = (self.get_teacher_profile(user_code) or [{}])[0]
             item['teacher_name']=obj.get("prefixname","")+" "+obj.get("officername","")+" "+obj.get("officersurname","")
        return results
    
    def get_booking_db(self,room_code:str,uuid:str,start_date:str,finish_date:str):
            db=DB()
            sql=f"""SELECT
                        A.id,
                        A.user_name AS teacher,
                        A.user_name AS userCode,
                        A.room_no AS roomcode,
                        A.subject_code AS coursecode,
                        A.objective AS coursename,
                        CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                        A.start_time AS startTime,
                        A.finish_time AS finishTime,
                        A.booking_date AS schedule_date,
                        T1.period AS timeperiodfrom,
                        T2.period AS timeperiodto,
                        false As isExist,
                        'booking' AS objective,
                        A.usage_status
            FROM room_usages A  LEFT OUTER JOIN
            periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN
            periods T2 ON A.finish_time=T2.finishTime
            WHERE A.room_no='{room_code}' AND 
            DATE(booking_date) 
            BETWEEN '{start_date}' AND '{finish_date}'
            AND A.id <>'{uuid}'
            AND A.objective<>'MIS Schedule'"""
            
            
            print(sql)
            
           
           
            results=db.get_specific_sql(sql)
            print(results)
            for item in results:
                 user_code = item.get('teacher', '')
                 obj = (self.get_teacher_profile(user_code) or [{}])[0]
                 item['teacher_name']=obj.get("prefixname","")+" "+obj.get("officername","")+" "+obj.get("officersurname","")
            return results
    



     
    def get_booking_db_all(self):
        db=DB()
        today=datetime.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom,
                    T2.period AS timeperiodto,
                    false As isExist
        FROM room_usages A  LEFT OUTER JOIN
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN
        periods T2 ON A.finish_time=T2.finishTime
        WHERE DATE(created_date)=%s AND A.objective<>'MIS Schedule'"""
        params=(today,)
        results=db.get_specific_sql(sql,None,params)
        for item in results:
            user_code = item.get('teacher', '')
            item['teacher'] = self.get_teacher_profile(user_code)
        return results
    
    def get_booking_db_all(self,booking_date:datetime):
        db=DB()
        booking_date=booking_date.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom,
                    T2.period AS timeperiodto,
                    false As isExist
        FROM room_usages A  LEFT OUTER JOIN
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN
        periods T2 ON A.finish_time=T2.finishTime
        WHERE DATE(booking_date)=%s AND A.objective<>'MIS Schedule'"""
        params=(booking_date,)
        results=db.get_specific_sql(sql,None,params)
        for item in results:
            user_code = item.get('teacher', '')
            item['teacher'] = self.get_teacher_profile(user_code)
        return results

    def get_booking_db_by_user(self,user_code:str):
        db=DB()
        today=datetime.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom, 
                    T2.period AS timeperiodfrom,
                    false As isExist
        FROM room_usages A  
        LEFT OUTER JOIN 
        periods T1 ON A.start_time=T1.startTime 
        LEFT OUTER JOIN 
        periods T2 ON A.finish_time=T2.finishTime
        WHERE A.user_name=%s 
        AND DATE(created_date)=%s 
        AND A.objective<>'MIS Schedule'"""
        params=(user_code,today)
        results=db.get_specific_sql(sql,None,params)
        for item in results:
            user_code = item.get('teacher', '')
            item['teacher'] = self.get_teacher_profile(user_code)
        return results
    
    def get_booking_db_by_user(self,user_code:str,booking_date:datetime):
        db=DB()
        booking_date=booking_date.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom, 
                    T2.period AS timeperiodfrom,
                    false As isExist
        FROM room_usages A  
        LEFT OUTER JOIN 
        periods T1 ON A.start_time=T1.startTime 
        LEFT OUTER JOIN 
        periods T2 ON A.finish_time=T2.finishTime
        WHERE A.user_name=%s 
        AND DATE(booking_date)=%s 
        AND A.objective<>'MIS Schedule'"""
        params=(user_code,booking_date)
        results=db.get_specific_sql(sql,None,params)
        for item in results:
            user_code = item.get('teacher', '')
            item['teacher'] = self.get_teacher_profile(user_code)
        return results


    def get_current_week(self, year_no, semester_no):
        db = DB()
        sql = """SELECT start_date FROM semesters
                 WHERE academic_year = %s AND semester = %s"""
        results = db.get_specific_sql(sql, None, (year_no, semester_no))
        del db
        if not results:
            return None
        start_date = results[0]['start_date']
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
        elif hasattr(start_date, 'date'):
            start_date = start_date.date()
        if start_date.weekday() > 0:
            print( start_date.weekday())
            start_date = start_date - timedelta(days=start_date.weekday())
        today = datetime.now().date()
        delta_days = (today - start_date).days
        return (delta_days // 7) + 1
    
    def get_date_week(self, year_no, semester_no, schedule_date=None):
            db = DB()
            sql = """SELECT start_date FROM semesters
                     WHERE academic_year = %s AND semester = %s"""
            results = db.get_specific_sql(sql, None, (year_no, semester_no))
            del db
            if not results:
                return None
            start_date = results[0]['start_date']
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
            elif hasattr(start_date, 'date'):
                start_date = start_date.date()
            if start_date.weekday() > 0:
                print( start_date.weekday())
                start_date = start_date - timedelta(days=start_date.weekday())

            runing_date = datetime.strptime(schedule_date[:10], '%Y-%m-%d').date()
           # print("Runing Date",runing_date)
           

            delta_days = (runing_date - start_date).days
            #print("Delta Day ",delta_days)
            return (delta_days // 7) + 1
    

    def get_week_type(self, year_no, semester_no):
        week = self.get_current_week(year_no, semester_no)
        print("Week ",week,week%2!=0)
        if week is None:
            return None
        if  week % 2 != 0:
             return 'O'
        return 'E'
    
    
    def get_week_type_no(self, year_no, semester_no):
        week = self.get_current_week(year_no, semester_no)
        print("Week ",week,week%2!=0)
        if week is None:
            return None
        week_type = 'O' if week % 2 != 0 else 'E'
        return {"week_type": week_type, "week_no": week}
    
    def get_week_type_no_by_date(self, year_no, semester_no,schedule_date=datetime.now):
        week = self. get_date_week(year_no, semester_no,schedule_date)
        print("Week ",week,week%2!=0)
        if week is None:
            return None
        week_type = 'O' if week % 2 != 0 else 'E'
        return {"week_type": week_type, "week_no": week}

        #return 'E' if week % 2 == 0 else 'O'

    def get_all_rooms(self):
        db = DB()
        sql="SELECT room_no FROM rooms ORDER BY room_no"
        results=db.get_specific_sql(sql)
        del db 
        return results

    def get_rooms(self, yearNo, semester):
        url = f"https://cos.nrru.ac.th/mis_api/getRoom.php?yearNo={yearNo}&semester={semester}"
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            return None

        data = response.json()
        filtered_data = self.get_current_element(data, yearNo, semester)

        result_exist = self.get_usage_checked()
        filtered_data = [
            item for item in filtered_data
            if not any(
                db_item["roomCode"] == item["roomcode"][:8]
                and db_item["periodFrom"] == item["periodfrom"]
                and db_item["periodTo"] == item["periodto"]
                for db_item in result_exist
            )
        ]

        booking = self.get_booking_db_all()
        for b in (booking or []):
            filtered_data.append({
                'roomcode':       b.get('roomcode', ''),
                'weekday':        b.get("weekday"),
                'timeperiodfrom': str(b.get('timeperiodfrom', '')),
                'timeperiodto':   str(b.get('timeperiodto', '')),
                'coursecode':     b.get('coursecode', ''),
                'coursename':     b.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'teacher':        b.get('teacher', []),
                'id':             '',
                'startTime':      b.get('startTime', ''),
                'finishTime':     b.get('finishTime', ''),
                'uuid':           '',
                'status':         0,
                'source':         'booking',
            })

        return filtered_data
    
    def get_rooms_by_user(self, yearNo, semester, usercode, schedule_date=None):
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
        if schedule_date is None:
            weekday = datetime.now().isoweekday()
        elif isinstance(schedule_date, str):
            weekday = datetime.strptime(schedule_date, "%Y-%m-%d").isoweekday()
        else:
            weekday = schedule_date.isoweekday()
        if week_day==7:
            week_day=1
        else:
            week_day+=1
        


        print(f"Week type: {week_type}, Weekday: {weekday}")
        keep = {'(คู่)', '**', ''} if week_type == 'E' else {'(คี่)', '**', ''}

        result = [
            item for item in data
            if (item.get('teacher') or [{}])[0].get('officerlogin') == usercode
            and item['roomcode'][8:] in keep
            and int(item['weekday']) == weekday
        ]

        periods_map = self._get_periods_map()
        for item in result:
            from_period = periods_map.get(int(item['timeperiodfrom']), {})
            to_period   = periods_map.get(int(item['timeperiodto']), {})
            item["roomcode"] = item["roomcode"][:8]
            item['startTime']  = str(from_period.get('startTime',  ''))[:5]
            item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
            today      = datetime.now().strftime("%Y-%m-%d")
            userLogin  = item.get('teacher', [{}])[0].get('officerlogin', '')
            raw = f"{item['coursecode']}_{item['roomcode']}_{item['weekday']}_{item['startTime']}_{item['finishTime']}_{yearNo}_{semester}_{today}_{userLogin}"
            item['id'] = base64.urlsafe_b64encode(raw.encode()).decode()
            item['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item['coursecode']}{today}{userLogin}"))
            item['isExist'] = False

        booking = self.get_booking_db_by_user(usercode)
        for b in (booking or []):
            result.append({
                'roomcode':       b.get('roomcode', ''),
                'weekday':        str(datetime.now().isoweekday()),
                'timeperiodfrom': str(b.get('timeperiodfrom', '')),
                'timeperiodto':   str(b.get('timeperiodto', '')),
                'coursecode':     b.get('coursecode', ''),
                'coursename':     b.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'teacher':        b.get('teacher', []),
                'id':             '',
                'startTime':      b.get('startTime', ''),
                'finishTime':     b.get('finishTime', ''),
                'uuid':           '',
                'status':         0,
                'isExist':        False,
                'source':         'booking',
            })

        result.sort(key=lambda x: x.get('startTime') or '')

        uuids = [item['uuid'] for item in result if item.get('uuid')]
        cancelled = set()
        if uuids:
            db = DB()
            #placeholders = ','.join(['%s'] * len(uuids))
            rows = db.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE DATE(created_date) = %s ",
                None, (today,)
            )
            del db
            cancelled = {row['uuid'] for row in (rows or [])}

        result = [item for item in result if item.get('uuid') not in cancelled]

        return result
    
    #*************************************************************
    def get_list_current_rooms(self, yearNo, semester):
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

        #week_type = self.get_week_type(yearNo, semester)
        week_day = datetime.now().isoweekday()

        if week_day==7:
            week_day=1
        else:
            week_day+=1

        result = [
            item for item in data
            if (week_day is None or int(item['weekday']) == int(week_day))
        ]

        for item in result:
            item["roomcode"] = item["roomcode"][:8]

        seen = set()
        results = [{"roomCode": item["roomcode"]} for item in result if item["roomcode"] not in seen and not seen.add(item["roomcode"])]
        return results
       


    #*************************************************************
    def get_booking_all_DB(self):
                db=DB()
                sql=f"""SELECT
                            A.id,
                            A.user_name AS teacher,
                            A.room_no AS roomcode,
                            A.subject_code AS coursecode,
                            A.objective AS coursename,
                            A.booking_date AS schedule_date,
                            A.start_time AS startTime,
                            A.finish_time AS finishTime
                FROM room_usages A  LEFT OUTER JOIN
                periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN
                periods T2 ON A.finish_time=T2.finishTime
                """
                results=db.get_specific_sql(sql,None)
                for item in results:
                    user_code = item.get('teacher', '')
                    item['teacher_name'] = self.get_teacher_profile(user_code)
                return results
    
    
    def get_schedule_all_DB(self):
            db=DB()
           
    
            sql=f"""SELECT
                           
                            id AS rowId,
                            roomcode,
                            coursecode,
                            coursename,
                            schedule_date,
                            teacher_name,
                            startTime,
                            finishTime,
                            userCode
            FROM schedules
            ORDER BY weekday,startTime
            """
            result=db.get_specific_sql(sql)
            
    
            booking = self.get_booking_all_DB()
            for b in (booking or []):
                
                result.append({
                    'rowId':b.get('id'),
                    'id':             b.get('id'),
                    'roomcode':       b.get('roomcode'),
                    'coursecode':     b.get('coursecode', ''),
                    'coursename':     b.get('coursename', ''),
                    'teacher':        b.get('teacher', []),
                    'teacher_name':   b.get('teacher_name', []),
                    'schedule_date':  b.get('schedule_date'),
                    'startTime':      b.get('startTime', ''),
                    'finishTime':     b.get('finishTime', ''),
                    'status':         0,
                    'userCode':b.get('teacher')
                })
    
            del db
            
    
            result.sort(key=lambda x: x.get('startTime') or '')
    
    
            return result
    
    def migrate_schedule_2_json(self):
        data = self.get_schedule_all_DB()

        repo_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'repositories')
        os.makedirs(repo_dir, exist_ok=True)
        file_path = os.path.join(repo_dir, 'schedule_all.json')

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return {"Flag": True, "file": os.path.abspath(file_path), "count": len(data)}

    def get_schedule_from_json(self):
        repo_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'repositories')
        file_path = os.path.join(repo_dir, 'schedule_all.json')

        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


    #************Get at current time********************************
    def get_room_binding(self,room_code:str):
        db=DB()
        sql=f"""SELECT room_no,ip_address,devices,pin 
        FROM room_binding WHERE room_no='{room_code}'"""
        results=db.get_specific_sql(sql)
        del db
        if len(results)>0:
            return results[0]
        else:
            return None 
    
    def get_booking_at_current_time(self):
        db=DB()
        sql=f"""SELECT room_no FROM rooms """
        results=db.get_specific_sql(sql)
        del db
        today=datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")

        def to_minutes(t):
            if not t:
                return None
            t = str(t)[:5]
            h, m = t.split(":")
            return int(h) * 60 + int(m)

        now_minutes = to_minutes(current_time)

        results_T=[]
        for item in results:
            room_code = item.get('room_no')
            result=self.get_schedule_by_rooms_db(room_code,today)
            results_T.extend(result)



        results_T = [
            item for item in results_T
            if to_minutes(item.get('startTime')) is not None
            and to_minutes(item.get('finishTime')) is not None
            and to_minutes(item.get('startTime')) <= now_minutes <= to_minutes(item.get('finishTime'))
            and item.get('usage_status') == 0
        ]
        
        for item in results_T:
            item["room_binding"] = self.get_room_binding(item.get('roomcode'))
            binding = item["room_binding"]
            if binding:
                item["topic"] = f"AP-TOPIC/{binding.get('room_no')}"
            else:
                item["topic"] = None

        # results_T = [
        #     {
        #         "rowId": item.get("rowId"),
        #         "token": item.get("id"),
        #         "room_binding": item.get("room_binding"),
        #         "topic": item.get("topic"),
        #     }
        #     for item in results_T
        #     if item.get("room_binding") is not None
        # ]

        return results_T
    
    

    #************Get Current Rooms  on DB************************
    def get_schedule_by_rooms_db(self,roomCode:str,scheduleDate=datetime.now()):
        db=DB()
        if scheduleDate is None:
            scheduleDate = datetime.now().strftime("%Y-%m-%d")
        elif not isinstance(scheduleDate, str):
            scheduleDate = scheduleDate.strftime("%Y-%m-%d")

        sql=f"""SELECT
                       
                        id AS rowId,
                        roomcode,
                        weekday,
                        timeperiodfrom,
                        timeperiodto,
                        coursecode,
                        coursename,
                        periodfrom,
                        periodto,
                        week_type,
                        week_no,
                        schedule_date,
                        teacher_name,
                        startTime,
                        finishTime,
                        'schedule' as source,
                        userCode,
                        usage_status
        FROM schedules
        WHERE roomcode='{roomCode}'
        AND schedule_date ='{scheduleDate}'
        ORDER BY weekday,startTime
        """
        result=db.get_specific_sql(sql)
        

        booking = self.get_booking_db_date(roomCode,scheduleDate)
        for b in (booking or []):
            
            result.append({
                'rowId':b.get('rowId'),
                'id':             b.get('id'),
                'roomcode':       b.get('roomcode', roomCode),
                'weekday':        str(b.get("weekday", '')),
                'timeperiodfrom': str(b.get('timeperiodfrom', '')),
                'timeperiodto':   str(b.get('timeperiodto', '')),
                'coursecode':     b.get('coursecode', ''),
                'coursename':     b.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'teacher':        b.get('teacher', []),
                'startTime':      b.get('startTime', ''),
                'finishTime':     b.get('finishTime', ''),
                'uuid':           '',
                'status':         0,
                'source':         'booking',
                'userCode':b.get('teacher')
            })

        del db
        
        #print(result)
        
        current_schedule = self.get_current()
        
        if current_schedule is None:
            raise HTTPException(status_code=404, detail="Current schedule not found")
        yearNo = current_schedule['year_no']
        semester = current_schedule['semester']
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        now_m = now.hour * 60 + now.minute

        def _to_minutes(t):
            try:
                h, m = str(t).split(':')[:2]
                return int(h) * 60 + int(m)
            except (ValueError, AttributeError):
                return None

        for item in (result or []):
            raw = f"{item['coursecode']}_{item['roomcode']}_{item['weekday']}_{item['startTime']}_{item['finishTime']}_{yearNo}_{semester}_{today}_{item['userCode']}"
            item['id'] = base64.urlsafe_b64encode(raw.encode()).decode()

            start_m = _to_minutes(item.get('startTime'))
            finish_m = _to_minutes(item.get('finishTime'))
            same_day = str(item.get('schedule_date') or scheduleDate)[:10] == today

            # total booked length, seconds
            item['duration'] = (finish_m - start_m) * 60 if start_m is not None and finish_m is not None else 0

            # countdown, seconds: time left until the slot ends (0 once finished,
            # full duration before it starts). Only meaningful for today's slots.
            # if finish_m is not None and same_day:
            #     item['countdown'] = max(0, min(item['duration'], (finish_m - now_m) * 60))
            # else:
            #     item['countdown'] = 0

        result.sort(key=lambda x: x.get('startTime') or '')

        uuids = [item['uuid'] for item in result if item.get('uuid')]
        cancelled = set()
        if uuids:
            db_T = DB()
            rows = db.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) = %s",
                None, (scheduleDate,)
            )
            del db_T
            cancelled = {row['uuid'] for row in (rows or [])}

        result = [item for item in result if item.get('uuid') not in cancelled]
        return result
    
    
    
    


    def get_schedule_by_room(self, yearNo, semester, roomCode, scheduleDate=datetime.now()):
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

        week_type = self.get_week_type(yearNo, semester)

        print("Week type --",week_type)

        if scheduleDate is None:
            weekday = datetime.now().isoweekday()
        elif isinstance(scheduleDate, str):
            weekday = datetime.strptime(scheduleDate, "%Y-%m-%d").isoweekday()
        else:
            weekday = scheduleDate.isoweekday()  # 1=Mon … 7=Sun

        if weekday==7:
            weekday=1
        else:
            weekday+=1

        print(f"Week type: {week_type}, Weekday: {weekday}")
        keep = {'(คู่)', '**', ''} if week_type == 'E' else {'(คี่)', '**', ''}

        result = [
            item for item in data
            if item['roomcode'][:8] == roomCode
            and item['roomcode'][8:] in keep
            and int(item['weekday']) == weekday
        ]

        periods_map = self._get_periods_map()
        for item in result:
            from_period = periods_map.get(int(item['timeperiodfrom']), {})
            to_period   = periods_map.get(int(item['timeperiodto']), {})
            item["roomcode"] = item["roomcode"][:8]
            item['startTime']  = str(from_period.get('startTime',  ''))[:5]
            item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
            today      = datetime.now().strftime("%Y-%m-%d")
            userLogin  = item.get('teacher', [{}])[0].get('officerlogin', '')
            raw = f"{item['coursecode']}_{item['roomcode']}_{item['weekday']}_{item['startTime']}_{item['finishTime']}_{yearNo}_{semester}_{today}_{userLogin}"
            item['id'] = base64.urlsafe_b64encode(raw.encode()).decode()
            item['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item['coursecode']}{today}{userLogin}"))
            item['isExist']=False
        
        if scheduleDate is None:
            booking_date = datetime.now().strftime("%Y-%m-%d")
        elif isinstance(scheduleDate, str):
            booking_date = scheduleDate
        else:
            booking_date = scheduleDate.strftime("%Y-%m-%d")


        booking = self.get_booking_db(roomCode)
        for b in (booking or []):
            result.append({
                'roomcode':       b.get('roomcode', roomCode),
                'weekday':        b.get('weekday', weekday),
                'timeperiodfrom': str(b.get('timeperiodfrom', '')),
                'timeperiodto':   str(b.get('timeperiodto', '')),
                'coursecode':     b.get('coursecode', ''),
                'coursename':     b.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'teacher':        b.get('teacher', []),
                'id':             '',
                'startTime':      b.get('startTime', ''),
                'finishTime':     b.get('finishTime', ''),
                'uuid':           '',
                'status':         0,
                'source':         'booking',
            })

        result.sort(key=lambda x: x.get('startTime') or '')

        uuids = [item['uuid'] for item in result if item.get('uuid')]
        cancelled = set()
        if uuids:
            db = DB()
            #placeholders = ','.join(['%s'] * len(uuids))
            rows = db.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) = %s",
                None, (today,)
            )
            del db
            cancelled = {row['uuid'] for row in (rows or [])}

        result = [item for item in result if item.get('uuid') not in cancelled]

        return result
    

    
    def get_schedule_all_empty_rooms(self,scheduleDate=datetime.now()):
        db=DB()
        sql=f"""SELECT room_no FROM rooms"""
        rows = db.get_specific_sql(sql, None)
        del db

        result = []
        for row in (rows or []):
            # room_schedule = self.get_empty_rooms(yearNo, semester, scheduleDate, row['room_no'])
            room_schedule = self.get_empty_rooms_db(scheduleDate, row['room_no'])
            if room_schedule:
                result.extend(room_schedule)
        return result
    
    #*******************Get Usage Rooms***************************
    def get_usage_rooms_db(self,scheduleDate=datetime.now,roomCode=''):
        if scheduleDate is None:
                    scheduleDate = datetime.now().strftime("%Y-%m-%d")
        elif not isinstance(scheduleDate, str):
                    scheduleDate = scheduleDate.strftime("%Y-%m-%d")
        db=DB()
        sql=f"""SELECT
                roomcode, 
                startTime,
                finishTime,
                usage_status
        FROM schedules 
        WHERE 
        roomcode LIKE '{roomCode}%'
        AND schedule_date ='{scheduleDate}'  
        ORDER BY startTime"""

        result_mis=db.get_specific_sql(sql)
        sql=f"""SELECT
            room_no AS roomcode, 
            start_time AS startTime,
            finish_time AS finishTime,
            usage_status 
        FROM room_usages 
        WHERE room_no LIKE '{roomCode}%' 
        AND booking_date='{scheduleDate}' 
        ORDER BY start_time"""

        #print(sql)

        result_booking=db.get_specific_sql(sql)

        results = (result_mis or []) + (result_booking or [])

        results.sort(key=lambda x: x.get('startTime') or '')
        
        results = [
                    {
                        'roomcode':   item.get('roomcode', ''),
                        'startTime':  item.get('startTime', ''),
                        'finishTime': item.get('finishTime', ''),
                        'usageStatus':item.get('usage_status')
                    }
                    for item in results
                ]
        

        del db
        return results
    
    #*******************Count************************************* 

    
    def get_sumary_hour_db(self):
        result_T=self.get_schedule_date_range()
        startDate=result_T["startDate"]
        finishDate=result_T["finishDate"]
        db=DB()
        sql="""(SELECT
            roomcode,
            schedule_date,
            COUNT(*) AS total_bookings,
            'schedule' AS source,
            SUM(TIME_TO_SEC(TIMEDIFF(STR_TO_DATE(finishTime, '%H:%i'), STR_TO_DATE(startTime, '%H:%i'))) / 3600) AS total_hours,
            GROUP_CONCAT(
                CONCAT(startTime, '-', finishTime, ' (',
                    ROUND(TIME_TO_SEC(TIMEDIFF(STR_TO_DATE(finishTime, '%H:%i'), STR_TO_DATE(startTime, '%H:%i'))) / 3600, 2), 'h)')
                ORDER BY startTime SEPARATOR ', '
            ) AS slot_breakdown
        FROM schedules
        WHERE usage_status>=3
        GROUP BY roomcode, schedule_date)
        UNION ALL
        (SELECT
            room_no AS roomcode,
            booking_date AS schedule_date,
            COUNT(*) AS total_bookings,
            'booking' AS source,
            SUM(TIME_TO_SEC(TIMEDIFF(finish_time, start_time)) / 3600) AS total_hours,
            GROUP_CONCAT(
                CONCAT(start_time, '-', finish_time, ' (',
                    ROUND(TIME_TO_SEC(TIMEDIFF(finish_time, start_time)) / 3600, 2), 'h)')
                ORDER BY start_time SEPARATOR ', '
            ) AS slot_breakdown
        FROM room_usages
        WHERE objective<>'MIS Schedule' AND booking_date BETWEEN %s AND %s
        GROUP BY room_no, booking_date)
        ORDER BY roomcode, schedule_date;"""
        results=db.get_specific_sql(sql,None,(startDate,finishDate))

        del db
        return results

    def get_schedule_date_range(self):
        db=DB()
        sql="""SELECT
            DATE_FORMAT(MIN(schedule_date), '%Y-%m-%d') AS startDate,
            DATE_FORMAT(MAX(schedule_date), '%Y-%m-%d') AS finishDate
        FROM schedules"""
        results=db.get_specific_sql(sql)
        del db
        if not results:
            return {"startDate": None, "finishDate": None}
        return results[0]

    #*******************Get Empty rooms DB************************
    
    

    def get_empty_rooms_db(self,scheduleDate=datetime.now(),roomCode=''):
        if scheduleDate is None:
            scheduleDate = datetime.now().strftime("%Y-%m-%d")
        elif not isinstance(scheduleDate, str):
            scheduleDate = scheduleDate.strftime("%Y-%m-%d")
        db=DB()
        sql_T=f"""SELECT
            roomcode,
            schedule_date,
            startTime,
            finishTime,
            usage_status
        FROM schedules

        UNION ALL

        SELECT
            room_no AS roomcode,
            CURDATE() AS schedule_date,
            '-' AS startTime,
            '-' AS finishTime,
            0 AS usage_status
        FROM rooms
        """

        sql=f"""SELECT
                roomcode,
                startTime,
                finishTime,
                usage_status
        FROM ({sql_T}) AS combined
        WHERE
        roomcode LIKE '{roomCode}%'
        AND schedule_date ='{scheduleDate}'  
        ORDER BY startTime
        
        
        
        """
        
        #print(sql)
        result_mis=db.get_specific_sql(sql)

        result=result_mis
        
        #print("Result MIS",result_mis)

        sql=f"""SELECT
            room_no AS roomcode, 
            start_time AS startTime,
            finish_time AS finishTime,
            usage_status 
        FROM room_usages 
        WHERE room_no LIKE '{roomCode}%' 
        AND booking_date='{scheduleDate}' 
        ORDER BY start_time"""

        #print(sql)

        result_booking=db.get_specific_sql(sql)

        result = (result_mis or []) + (result_booking or [])

        # result.sort(key=lambda x: x.get('startTime') or '')
        
        
        # print("Result T",result)

        del db 

        result = [
            {
                'roomcode':   item.get('roomcode', ''),
                'startTime':  item.get('startTime', ''),
                'finishTime': item.get('finishTime', ''),
                'usageStatus':item.get('usage_status')
            }
            for item in result
        ]
        
        #print(result)

        return self._get_empty_ranges(result)
    




    #*************************************************************

    def get_empty_rooms(self, yearNo, semester, scheduleDate=datetime.now(), roomCode=None):
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
        week_type = self.get_week_type(yearNo, semester)
        if scheduleDate is None:
            week_day = datetime.now().isoweekday()
        elif isinstance(scheduleDate, str):
            week_day = datetime.strptime(scheduleDate, "%Y-%m-%d").isoweekday()
        else:
            week_day = scheduleDate.isoweekday()  # date object

        if scheduleDate is None:
            booking_date = datetime.now().strftime("%Y-%m-%d")
        elif isinstance(scheduleDate, str):
            booking_date = scheduleDate
        else:
            booking_date = scheduleDate.strftime("%Y-%m-%d")

        if week_day==7:
            week_day=1
        else:
            week_day+=1

        print(f"Week type: {week_type}, Weekday filter: {week_day}")
        keep = {'(คู่)', '**', ''} if week_type == 'E' else {'(คี่)', '**', ''}

        result = [
            item for item in data
            if item['roomcode'][8:] in keep
            and (week_day is None or int(item['weekday']) == int(week_day))
            and (roomCode is None or item['roomcode'][:8] == roomCode)
        ]

        periods_map = self._get_periods_map()
        for item in result:
            from_period = periods_map.get(int(item['timeperiodfrom']), {})
            to_period   = periods_map.get(int(item['timeperiodto']), {})
            item["roomcode"] = item["roomcode"][:8]
            item['startTime']  = str(from_period.get('startTime',  ''))[:5]
            item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
            today      = datetime.now().strftime("%Y-%m-%d")
            userLogin  = item.get('teacher', [{}])[0].get('officerlogin', '')
            raw = f"{item['coursecode']}_{item['roomcode']}_{item['weekday']}_{item['startTime']}_{item['finishTime']}_{yearNo}_{semester}_{today}_{userLogin}"
            item['id'] = base64.urlsafe_b64encode(raw.encode()).decode()
            item['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item['coursecode']}{today}{userLogin}"))

        booking = self.get_booking_db_date(roomCode,booking_date)
        for b in (booking or []):
            result.append({
                'roomcode':       b.get('roomcode', roomCode),
                'weekday':        str(b.get("weekday", '')),
                'timeperiodfrom': str(b.get('timeperiodfrom', '')),
                'timeperiodto':   str(b.get('timeperiodto', '')),
                'coursecode':     b.get('coursecode', ''),
                'coursename':     b.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'teacher':        b.get('teacher', []),
                'id':             '',
                'startTime':      b.get('startTime', ''),
                'finishTime':     b.get('finishTime', ''),
                'uuid':           '',
                'status':         0,
                'source':         'booking',
            })

        result.sort(key=lambda x: x.get('startTime') or '')



        result = [
            {
                'roomcode':   item.get('roomcode', ''),
                'startTime':  item.get('startTime', ''),
                'finishTime': item.get('finishTime', ''),
            }
            for item in result
        ]

        return self._get_empty_ranges(result)


    #**********Function for migrate*********************

    def get_schedule_datasets(self, roomCode, startDate, finishDate,current_schedule):
        # current_schedule = self.get_current()
        # if current_schedule is None:
        #     return None
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

        #week_type_info = self.get_week_type_no(yearNo, semester)
        # week_typ_info=self.get_week_type_no_by_date(yearNo,semester,scheduleDate)
        # week_type = week_type_info.get('week_type') if week_type_info else None
        # week_no = week_type_info.get('week_no') if week_type_info else None
        
        week_type_info = self.get_week_type_no_by_date(yearNo, semester,scheduleDate)
        #print("Test Week",week_type_info)
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
            item["userCode"]=teacher.get("officerlogin","")
            item.pop("teacher", None)
            from_period = periods_map.get(int(item['timeperiodfrom']), {})
            to_period   = periods_map.get(int(item['timeperiodto']), {})
            item['startTime']  = str(from_period.get('startTime',  ''))[:5]
            item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
            item["yearNo"]=yearNo
            item["semester"]=semester

            
        return result
    #*********************Get Schedule Test Ord or Event*************
    def get_schedule_TEST(self,yearNo,semester,roomCode,scheduleDate=datetime.now):
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
    
            week_type_info = self.get_week_type_no_by_date(yearNo, semester,scheduleDate)
            print("Test Week",week_type_info)
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
                item["roomcode"]=item['roomcode']
                teacher = (item.get("teacher") or [{}])[0]
                item["teacher_name"]=teacher.get("prefixname","")+" "+teacher.get("officername","")+" "+teacher.get("officersurname","")
                item["user_name"]=teacher.get("officerlogin","")
                item["userCode"]=teacher.get("officerlogin","")
                item.pop("teacher", None)
                from_period = periods_map.get(int(item['timeperiodfrom']), {})
                to_period   = periods_map.get(int(item['timeperiodto']), {})
                item['startTime']  = str(from_period.get('startTime',  ''))[:5]
                item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
                item["yearNo"]=yearNo
                item["semester"]=semester
    
                
            return result

    #****************************************************************
    #*********************Get Schedule Sumary************************
    
    def get_rooms_dashboard(self):
        db=DB()
        sql_usage="""SELECT
              COUNT(id) AS usage_count
        FROM schedules
        WHERE DATE(schedule_date) = CURDATE()
        AND CURTIME() BETWEEN startTime AND finishTime 
        AND usage_status=3
        UNION 
        SELECT COUNT(id) FROM room_usages
        WHERE booking_date 
        AND CURTIME() BETWEEN start_time AND finish_time 
        AND usage_status=3
        
        
        """
        result_usage = db.get_specific_sql(sql_usage)
        
        
        
        sql_schedule="""SELECT COUNT(roomcode) AS schedule_count FROM
                (SELECT
                    roomcode
                FROM schedules
                WHERE DATE(schedule_date) = CURDATE()
                AND CURTIME() BETWEEN startTime AND finishTime
                AND usage_status<3
                UNION
                SELECT
                    room_no AS roomcode
                FROM room_usages
                WHERE DATE(booking_date) = CURDATE()
                AND CURTIME() BETWEEN start_time AND finish_time
                AND usage_status<3) AS V

                """
        result_schedule = db.get_specific_sql(sql_schedule)
        #print(result_schedule)
        
        
        sql_all_room="""SELECT 
        count(room_no) AS room_count
        FROM rooms     
             
                """
                
        #print(sql_all_room)
        result_all_room = db.get_specific_sql(sql_all_room)
        
        sql_room_usage="""SELECT
                    roomcode    
                FROM schedules
                WHERE DATE(schedule_date) = CURDATE()
                AND CURTIME() BETWEEN startTime AND finishTime 
                AND usage_status>=3
                
                UNION 
                SELECT 
                    room_no AS roomcode 
                FROM room_usages
                WHERE booking_date 
                AND CURTIME() BETWEEN start_time AND finish_time 
                AND usage_status>=3
                 
                
                
                """
        
        sql_unuse=f"""SELECT COUNT(room_no) AS free_room_count
        
        
        FROM rooms WHERE room_no NOT IN({sql_room_usage})"""
        #print(sql_unuse)
        
        result_free=db.get_specific_sql(sql_unuse)
        result={
            "schedule_count":result_schedule[0]["schedule_count"],
            "usage_count":result_usage[0]["usage_count"],
            "all_rooms_count":result_all_room[0]["room_count"],
            "free_rooms_count":result_free[0]["free_room_count"],
            "list_empty_rooms":self.get_empty_rooms_db(datetime.now().strftime("%Y-%m-%d")),
            "list_usage_rooms":self.get_usage_rooms_db(datetime.now().strftime("%Y-%m-%d")),
            "sumary_hours":self.get_sumary_hour_db()
            }
        
        del db
        return result
        # return result 
    

    #*********************Get Room By Criteria DB********************


    def get_schedule_booking_room_by_date(self,booking_date:str):
        db=DB()
        #today=datetime.now().strftime("%Y-%m-%d")
        sql=f"""SELECT
                    A.id AS schedule_id,
                    A.user_name AS teacher,
                    A.room_no AS roomcode,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.subject_code AS coursecode,
                    A.objective AS coursename,
                    A.start_time AS startTime,
                    A.finish_time AS finishTime,
                    T1.period AS timeperiodfrom, 
                    T2.period AS timeperiodfrom,
                    false As isExist
        FROM room_usages A LEFT OUTER JOIN 
        periods T1 ON A.start_time=T1.startTime LEFT OUTER JOIN 
        periods T2 ON A.finish_time=T2.finishTime
        WHERE DATE(booking_date)=%s 
        AND A.objective<>'MIS Schedule' ORDER BY A.start_time"""
        params=(booking_date,)
        results=db.get_specific_sql(sql,None,params)
        del db 
        return results 
    
    def get_schedule_by_weekly_db(self,scheduleDate=datetime.now):
        if scheduleDate is None:
            booking_date = datetime.now()
        elif isinstance(scheduleDate, str):
            booking_date = datetime.strptime(scheduleDate, "%Y-%m-%d")
        else:
            booking_date = scheduleDate

        db=DB()
        sql="""SELECT
                        id AS schedule_id,
                        roomcode,
                        weekday,
                        timeperiodfrom,
                        timeperiodto,
                        coursecode,
                        coursename,
                        periodfrom,
                        periodto,
                        week_type,
                        week_no,
                        schedule_date,
                        teacher_name,
                        startTime,
                        finishTime,
                        'MIS Schedule' as objective
        FROM schedules
        WHERE 
        schedule_date =%s
        ORDER BY weekday,startTime
        """

        params=(booking_date,)
        results=db.get_specific_sql(sql,None,params)
        results_V1=self.get_schedule_booking_room_by_date(booking_date)

        for item in (results_V1 or []):
            schedule_date_val = item.get('schedule_date')
        

            results.append({
                'roomcode':       item.get('roomcode', ''),
                'weekday':        str(item.get("weekday", '')),
                'timeperiodfrom': str(item.get('timeperiodfrom', '')),
                'timeperiodto':   str(item.get('timeperiodto', '')),
                'coursecode':     item.get('coursecode', ''),
                'coursename':     item.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'week_type':      None,
                'week_no':        None,
                'schedule_date':  schedule_date_val,
                'teacher_name':   item.get('teacher_name', ''),
                'startTime':      item.get('startTime', ''),
                'finishTime':     item.get('finishTime', ''),
                'source':         'booking',
            })

        results.sort(key=lambda x: (str(x.get('weekday') or ''), x.get('startTime') or ''))
        del db 
        return results 
    
    
    def get_schedule_by_criteria_db(self,roomCode,scheduleDate=datetime.now):
        if scheduleDate is None:
            date_obj = datetime.now()
        elif isinstance(scheduleDate, str):
            date_obj = datetime.strptime(scheduleDate, "%Y-%m-%d")
        else:
            date_obj = scheduleDate

        #weekday = date_obj.isoweekday()
        first_date_of_week = date_obj - (timedelta(days=date_obj.weekday()))
        last_date_of_week  = first_date_of_week + timedelta(days=6)
        first_date = first_date_of_week.strftime("%Y-%m-%d")
        last_date  = last_date_of_week.strftime("%Y-%m-%d")
        db=DB()
        sql="""SELECT
                        id AS schedule_id,
                        roomcode,
                        weekday,
                        timeperiodfrom,
                        timeperiodto,
                        coursecode,
                        coursename,
                        periodfrom,
                        periodto,
                        week_type,
                        week_no,
                        schedule_date,
                        teacher_name,
                        userCode,
                        startTime,
                        finishTime,
                        'MIS Schedule' as objective,
                        'MIS Schedule' as source_type,
                        usage_status
        FROM schedules
        WHERE roomcode=%s
        AND schedule_date BETWEEN %s AND %s
        ORDER BY weekday,startTime
        """

        params=(roomCode,first_date,last_date,)
        results=db.get_specific_sql(sql,None,params)

        results_T=self.get_booking_db(roomCode,first_date,last_date)
        

        for item in (results_T or []):
       

            results.append({
                'schedule_id':item.get('id'),
                'roomcode':       item.get('roomcode', roomCode),
                'weekday':        item.get('weekday'),
                'timeperiodfrom': str(item.get('timeperiodfrom', '')),
                'timeperiodto':   str(item.get('timeperiodto', '')),
                'coursecode':     item.get('coursecode', ''),
                'coursename':     item.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'week_type':      None,
                'week_no':        None,
                'schedule_date':  item.get('booking_date', ''),
                'teacher_name':   item.get('teacher_name', ''),
                'startTime':      item.get('startTime', ''),
                'finishTime':     item.get('finishTime', ''),
                'objective':         'booking',
                'source_type':       'booking',
                'usage_status':item.get('usage_status')
            })

        results.sort(key=lambda x: (str(x.get('weekday') or ''), x.get('startTime') or ''))

        uuids = [item['schedule_id'] for item in results if item.get('schedule_id')]
        cancelled = set()
        if uuids:
            db_T = DB()
            placeholders = ','.join(['%s'] * len(uuids))
            rows = db_T.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) = %s",
                None,(scheduleDate,)
            )
            del db_T
            cancelled = {row['uuid'] for row in (rows or [])}

        results = [item for item in results if item.get('schedule_id') not in cancelled]

        return results

    def get_schedule_by_criteria_db(self,roomCode,sourceType='all',scheduleDate=datetime.now):
        if scheduleDate is None:
            date_obj = datetime.now()
        elif isinstance(scheduleDate, str):
            date_obj = datetime.strptime(scheduleDate, "%Y-%m-%d")
        else:
            date_obj = scheduleDate

        first_date_of_week = date_obj - (timedelta(days=date_obj.weekday()))
        last_date_of_week  = first_date_of_week + timedelta(days=6)
        first_date = first_date_of_week.strftime("%Y-%m-%d")
        last_date  = last_date_of_week.strftime("%Y-%m-%d")

        include_mis     = sourceType in (None, '', 'all', 'MIS Schedule')
        include_booking = sourceType in (None, '', 'all', 'booking')
        
        # print("Include Booking,",include_booking)
        # print("Include MIS,",include_mis)
        
        #print(f"Fetching schedule for room: {roomCode}, date: {scheduleDate}, source type: {sourceType}")

        results = []

        if include_mis:
            sql_c=f"""SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) = '{scheduleDate}'"""
            db=DB()
            sql=f"""SELECT
                            id AS schedule_id,
                            roomcode,
                            weekday,
                            timeperiodfrom,
                            timeperiodto,
                            coursecode,
                            coursename,
                            periodfrom,
                            periodto,
                            week_type,
                            week_no,
                            schedule_date,
                            teacher_name,
                            userCode,
                            startTime,
                            finishTime,
                            'MIS Schedule' as objective,
                            usage_status
            FROM schedules
            WHERE roomcode=%s
            AND schedule_date BETWEEN %s AND %s
            AND id NOT IN ({sql_c})
            ORDER BY weekday,startTime
            """
            
            
            params=(roomCode,first_date,last_date,)
            results=db.get_specific_sql(sql,None,params)
            del db

        if include_booking:
            #print("Booking Access")
            results_T=self.get_booking_range_db(roomCode,first_date,last_date)

            for item in (results_T or []):
                results.append({
                    'schedule_id':item.get('id'),
                    'roomcode':       item.get('roomcode', roomCode),
                    'weekday':        item.get('weekday'),
                    'timeperiodfrom': str(item.get('timeperiodfrom', '')),
                    'timeperiodto':   str(item.get('timeperiodto', '')),
                    'coursecode':     item.get('coursecode', ''),
                    'coursename':     item.get('coursename', ''),
                    'periodfrom':     '',
                    'periodto':       '',
                    'week_type':      None,
                    'week_no':        None,
                    'schedule_date':  item.get('booking_date', ''),
                    'teacher_name':   item.get('teacher_name', ''),
                    'user_code':        item.get('userCode', ''),
                    'startTime':      item.get('startTime', ''),
                    'finishTime':     item.get('finishTime', ''),
                    'objective':         'booking',
                    'usage_status':item.get('usage_status')
                })

        results.sort(key=lambda x: (str(x.get('weekday') or ''), x.get('startTime') or ''))

        uuids = [item['schedule_id'] for item in results if item.get('schedule_id')]
        cancelled = set()
        if uuids:
            db_T = DB()
            rows = db_T.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) = %s",
                None,(scheduleDate,)
            )
            del db_T
            cancelled = {row['uuid'] for row in (rows or [])}

        results = [item for item in results if item.get('schedule_id') not in cancelled]

        return results

    #*************Get Schedule by date range *************************************
    def get_schedule_by_date_range_db(self,roomCode,start_date:str,finish_date:str):
       

        first_date = start_date.strftime("%Y-%m-%d")
        last_date  = finish_date.strftime("%Y-%m-%d")
        db=DB()
        sql=f"""SELECT
                        id,
                        roomcode,
                        weekday,
                        timeperiodfrom,
                        timeperiodto,
                        coursecode,
                        coursename,
                        periodfrom,
                        periodto,
                        week_type,
                        week_no,
                        schedule_date,
                        teacher_name,
                        startTime,
                        finishTime,
                        'MIS Schedule' as objective
        FROM schedules
        WHERE roomcode='{roomCode}'
        AND schedule_date BETWEEN '{first_date}' AND '{last_date}' 
        ORDER BY weekday,startTime
        """
        
        #print(sql)

        #params=(roomCode,first_date,last_date,)
        results=db.get_specific_sql(sql)

        results_T=self.get_booking_range_db(roomCode,first_date,last_date)
        
        today=datetime.now().strftime("%Y-%m-%d")

        for item in (results_T or []):
            raw = f"{item['coursecode']}_{item['roomcode']}_{item['weekday']}_{item['startTime']}_{item['finishTime']}_{yearNo}_{semester}_{today}_{userLogin}"

            results.append({
                'id':item.get('id'),
                'roomcode':       item.get('roomcode', roomCode),
                'weekday':        item.get('weekday'),
                'timeperiodfrom': str(item.get('timeperiodfrom', '')),
                'timeperiodto':   str(item.get('timeperiodto', '')),
                'coursecode':     item.get('coursecode', ''),
                'coursename':     item.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'week_type':      None,
                'week_no':        None,
                'schedule_date':  item.get('booking_date', ''),
                'teacher_name':   item.get('teacher_name', ''),
                'startTime':      item.get('startTime', ''),
                'finishTime':     item.get('finishTime', ''),
                'source':         'booking',
            })

        results.sort(key=lambda x: (str(x.get('weekday') or ''), x.get('startTime') or ''))

        uuids = [item['uuid'] for item in results if item.get('uuid')]
        cancelled = set()
        if uuids:
            db_T = DB()
            #placeholders = ','.join(['%s'] * len(uuids))
            rows = db_T.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) BETWEEN %s AND %s",
                None,(first_date,last_date,)
            )
            del db_T
            cancelled = {row['uuid'] for row in (rows or [])}

        results = [item for item in results if item.get('uuid') not in cancelled]
        
        return results

        
    #****************************************************************
    def get_schedule_by_criteria(self, yearNo, semester, roomCode, scheduleDate=datetime.now):
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

        week_type = self.get_week_type(yearNo, semester)
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
        print("Week Day",week_day)
        #week_day-=1
        print(f"Week type: {week_type}, Weekday filter: {week_day}")
        keep = {'(คู่)', '**', ''} if week_type == 'E' else {'(คี่)', '**', ''}

        result = [
            item for item in data
            if item['roomcode'][:8] == roomCode
            and item['roomcode'][8:] in keep
            and (week_day is None or int(item['weekday']) == int(week_day))
        ]

        periods_map = self._get_periods_map()
        for item in result:
            from_period = periods_map.get(int(item['timeperiodfrom']), {})
            to_period   = periods_map.get(int(item['timeperiodto']), {})
            item["roomcode"] = item["roomcode"][:8]
            item['startTime']  = str(from_period.get('startTime',  ''))[:5]
            item['finishTime'] = str(to_period.get('finishTime', ''))[:5]
            today      = datetime.now().strftime("%Y-%m-%d")
            userLogin  = item.get('teacher', [{}])[0].get('officerlogin', '')
            raw = f"{item['coursecode']}_{item['roomcode']}_{item['weekday']}_{item['startTime']}_{item['finishTime']}_{yearNo}_{semester}_{today}_{userLogin}"
            item['id'] = base64.urlsafe_b64encode(raw.encode()).decode()
            item['uuid'] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{item['coursecode']}{today}{userLogin}"))

        booking = self.get_booking_db_date(roomCode,booking_date)
        for b in (booking or []):
            result.append({
                'roomcode':       b.get('roomcode', roomCode),
                'weekday':        b.get("weekday"),
                'timeperiodfrom': str(b.get('timeperiodfrom', '')),
                'timeperiodto':   str(b.get('timeperiodto', '')),
                'coursecode':     b.get('coursecode', ''),
                'coursename':     b.get('coursename', ''),
                'periodfrom':     '',
                'periodto':       '',
                'teacher':        b.get('teacher', []),
                'id':             '',
                'startTime':      b.get('startTime', ''),
                'finishTime':     b.get('finishTime', ''),
                'uuid':           '',
                'status':         0,
                'source':         'booking',
            })

        result.sort(key=lambda x: x.get('startTime') or '')

        uuids = [item['uuid'] for item in result if item.get('uuid')]
        cancelled = set()
        if uuids:
            db = DB()
            placeholders = ','.join(['%s'] * len(uuids))
            rows = db.get_specific_sql(
                f"SELECT uuid FROM cancel_rooms WHERE  DATE(created_date) = %s",
                None,(today,)
            )
            del db
            cancelled = {row['uuid'] for row in (rows or [])}

        result = [item for item in result if item.get('uuid') not in cancelled]

        return result
    
    
    def schedule_decode(self, schedule_id: str | bytes) -> dict | None:
        try:
            if isinstance(schedule_id, str):
                schedule_id = schedule_id.encode()
            decoded = base64.urlsafe_b64decode(schedule_id).decode()
            # format: "coursecode_roomcode_weekday_startTime_finishTime_yearNo_semester_today_officerlogin"
            fields = decoded.split('_')
            if len(fields) != 9:
                return None
            sid = schedule_id.decode() if isinstance(schedule_id, bytes) else schedule_id
            return {
                'id':            sid,
                'subject_code':    fields[0],
                'room_code':      fields[1],
                'weekday':       fields[2],
                'start_time':     fields[3],
                'finish_time':    fields[4],
                'year_no':        fields[5],
                'semester':      fields[6],
                'date':          fields[7],
                'user_login':  fields[8],
            }
        except Exception:
            return None
            




    def _get_empty_ranges(self, occupied: list, day_start="07:00", day_end="19:00") -> list:
        by_room = {}
        for item in occupied:
            by_room.setdefault(item['roomcode'], []).append((item['startTime'], item['finishTime']))

        empty = []
        for roomcode, slots in by_room.items():
            slots.sort()
            merged = []
            for start, finish in slots:
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], finish))
                else:
                    merged.append((start, finish))

            cursor = day_start
            for start, finish in merged:
                if start > cursor:
                    empty.append({'roomcode': roomcode, 'startTime': cursor, 'finishTime': start})
                cursor = max(cursor, finish)
            if cursor < day_end:
                empty.append({'roomcode': roomcode, 'startTime': cursor, 'finishTime': day_end})

        return empty

    def _get_periods_map(self) -> dict:
        db = DB('periods')
        sql = """SELECT period, startTime, finishTime FROM periods ORDER BY period"""
        rows = db.get_specific_sql(sql)
        del db
        return {int(row['period']): row for row in (rows or [])}

    def get_current_period(self):
        db = DB('periods')
        sql = """SELECT period, startTime, finishTime FROM periods ORDER BY period"""
        results = db.get_specific_sql(sql)
        del db
        if not results:
            return None
        now = datetime.now().replace(second=0, microsecond=0)
        for row in results:
            start = datetime.combine(now.date(), datetime.strptime(str(row['startTime'])[:5], '%H:%M').time())
            if (start - timedelta(minutes=5)) <= now <= (start + timedelta(minutes=5)):
                return row['period']
        return None

    def get_current_element(self, data: list, year_no, semester_no) -> list:
        week_type = self.get_week_type(year_no, semester_no)
        period = self.get_current_period()
        weekday = datetime.now().isoweekday()  # 1=Mon … 7=Sun

        if week_type is None or period is None:
            return []

        exclude_suffix = '(คู่)' if week_type == 'E' else '(คี่)'

        filtered = [
            item for item in data
            if exclude_suffix not in item['roomcode']
            and int(item['weekday']) == weekday
            and int(item['timeperiodfrom']) <= int(period) <= int(item['timeperiodto'])
        ]

        for item in filtered:
            item['weekType'] = week_type

        return filtered

    def get_semester_id(self, semester_name):
        db = DB(self.__tableName__)
        sql = """SELECT
                    id
                FROM semesters
                WHERE name = %s
        """
        results = db.get_specific_sql(sql, None, (semester_name,))
        del db
        if results:
            return results[0]['id']
        return None

    def remove_schedule(self,id):
        db=DB()
        sql="DELETE FROM schedules WHERE id=%s"
        params=(id,)
        result=db.set_specific_sql(sql,params)
        del db 
        return result 
    
    def remove_booking(self,id):
        db=DB()
        sql="DELETE FROM room_usages WHERE id=%s "
        params=(id,)
        result=db.set_specific_sql(sql,params)
        del db 
        return result
    
    #***********Get schedule by ID***************
    def get_schedule_by_id(self, schedule_id, source_type='schedule'):
        db = DB()
        sql = """SELECT * FROM (
                SELECT  
                        id,
                        coursecode,
                        coursename,
                        roomcode,
                        schedule_date,
                        startTime,
                        finishTime,
                        yearNo,
                        semester,
                        userCode, 
                        'schedule' AS source_type
                FROM schedules 
                UNION
                SELECT 
                        id,
                        subject_code AS coursecode,
                        subject_code AS coursename,
                        room_no AS roomcode, 
                        booking_date AS schedule_date,
                        start_time AS startTime,
                        finish_time AS finishTime,
                        year_no AS yearNo,
                        semester AS semester,
                        user_name AS userCode,
                        'booking' AS source_type
                FROM room_usages) AS V 
                WHERE V.source_type = %s AND V.id = %s"""
        params = (source_type, schedule_id,)
        results = db.get_specific_sql(sql, None, params)
        del db
        if results:
            return results[0]
        return None
    
    def set_schedule_usage_status(self, schedule_id, source_type, usage_status):
        db = DB()
        if source_type == 'schedule':
            sql = "UPDATE schedules SET usage_status = %s WHERE id = %s"
        elif source_type == 'booking':
            sql = "UPDATE room_usages SET usage_status = %s WHERE id = %s"
        else:
            del db
            raise ValueError("Invalid source_type. Must be 'schedule' or 'booking'.")
        
        params = (usage_status, schedule_id,)
        result = db.set_specific_sql(sql, params)
        del db
        return result

    def check_usage_status(self, schedule_id, source_type='schedule'):
        db = DB()
        if source_type == 'schedule':
            sql = "SELECT usage_status FROM schedules WHERE id = %s"
        elif source_type == 'booking':
            sql = "SELECT usage_status FROM room_usages WHERE id = %s"
        else:
            del db
            raise ValueError("Invalid source_type. Must be 'schedule' or 'booking'.")

        params = (schedule_id,)
        results = db.get_specific_sql(sql, None, params)
        del db
        if results:
            return results[0].get('usage_status')
        return None


