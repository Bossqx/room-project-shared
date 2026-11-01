
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Union
import requests
from pydantic import BaseModel, Field
from typing import Iterator
from src.util.dbcontroller import DBController as DB


class Semester_Base(BaseModel):
    academic_year:str
    semester:str 
    status:int=1
    created_date:datetime=datetime.now()


class ManualSchedule_Base(BaseModel):
    """One room booked at the same hours on every date in a range."""

    room_no: Union[str, List[str]] = Field(
        ...,
        description='Room number, a list of them, or "all" for every room in the rooms table.',
    )
    start_date: date = Field(..., description="First schedule_date, inclusive.")
    finish_date: date = Field(..., description="Last schedule_date, inclusive.")
    start_time: str = Field(..., description="HH:MM, the same on every date.")
    finish_time: str = Field(..., description="HH:MM, the same on every date.")
    coursename: Optional[str] = Field("กำหนดการใช้ห้อง")
    coursecode: Optional[str] = None
    teacher_name: Optional[str] = None
    userCode: Optional[str] = None



class ManualScheduleAllRooms_Base(BaseModel):
    """The same booking as ManualSchedule_Base, for every room get_rooms lists."""

    start_date: date = Field(..., description="First schedule_date, inclusive.")
    finish_date: date = Field(..., description="Last schedule_date, inclusive.")
    start_time: str = Field(..., description="HH:MM, the same on every date.")
    finish_time: str = Field(..., description="HH:MM, the same on every date.")
    search: Optional[str] = Field(
        None,
        description="Only rooms whose room_no contains this; every room when omitted.",
    )
    coursename: Optional[str] = Field("กำหนดการใช้ห้อง")
    coursecode: Optional[str] = None
    teacher_name: Optional[str] = None
    userCode: Optional[str] = None
    weekdays: Optional[List[int]] = Field(
        None,
        description="Only these weekdays, numbered Sunday=1 … Saturday=7. All days when omitted.",
    )


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

    
    
    # schedules.weekday is stored Sunday=1 … Saturday=7, which is what the MIS
    # feed sends. isoweekday() is Monday=1 … Sunday=7, so Sunday wraps round to
    # 1 and every other day shifts up by one — the same mapping
    # get_schedule_migrate applies when it matches a date against the feed.
    @staticmethod
    def weekday_of(day) -> int:
        if isinstance(day, str):
            day = datetime.strptime(day[:10], "%Y-%m-%d").date()
        elif isinstance(day, datetime):
            day = day.date()
        iso = day.isoweekday()
        return 1 if iso == 7 else iso + 1

    def list_rooms(self, search: Optional[str] = None) -> list:
        """
        The rooms a manual schedule can be written against.

        The same table and ordering get_room_numbers validates against, so a
        room offered by the picker is always one set_manual_schedule accepts.

        search is optional. None, an empty string and whitespace all mean the
        same thing — every room — because a cleared search box sends an empty
        string, not an absent parameter, and that has to list everything
        rather than match nothing.
        """
        needle = (search or "").strip()

        db = DB()
        sql = """SELECT
            room_no,
            room_type,
            floor_no,
            building,
            computer_no,
            seat_no
        FROM rooms"""
        params = None
        if needle:
            # Matched in SQL rather than in Python so a large rooms table does
            # not have to come across the wire to be filtered.
            sql += " WHERE room_no LIKE %s"
            params = (f"%{needle}%",)
        sql += " ORDER BY room_no"
        results = db.get_specific_sql(sql, None, params)
        del db
        return results or []
    
    def _date_range(self, start_date, finish_date) -> Iterator[date]:
        start = self._to_datetime(start_date).date()
        finish = self._to_datetime(finish_date).date()
        span = (finish - start).days
        return span 
      
    
    
    def _to_datetime(value) -> datetime:
            """Normalize str | date | datetime into a datetime object."""
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid date format: {value!r}. Expected YYYY-MM-DD.",
                )

            
    def set_manaul_schedule(self,start_date:date,finish_date:date):
        rooms=self.list_rooms()
        diff=self._date_range(start_date,finish_date)
        for item in rooms:
            i=0 
            for i in range(0, span + 1, step_days):
                current_date = start_date + timedelta(days=i)            
        return rooms 
            
            

    def get_room_numbers(self, room_no) -> list:
        """
        Resolve the request's room_no against the rooms table.

        Returns the rooms in the order the table gives them, and never
        invents one: a room that is not in rooms would produce schedule rows
        nothing else in the system can join to.
        """
        db = DB()
        known = [row["room_no"] for row in (db.get_specific_sql(
            "SELECT room_no FROM rooms ORDER BY room_no") or [])]
        del db

        if isinstance(room_no, str):
            wanted = [room_no]
        else:
            wanted = list(room_no or [])

        cleaned = [str(item).strip() for item in wanted if str(item).strip()]
        if len(cleaned) == 1 and cleaned[0].lower() in ("all", "*"):
            return known, []

        valid = [item for item in known if item in cleaned]
        unknown = [item for item in cleaned if item not in known]
        return valid, unknown

    def get_periods_for_times(self, start_time: str, finish_time: str):
        """
        The first and last teaching period the given hours cover.

        Manual bookings do not have to line up with the period grid, so these
        can both come back None; the schedule row is still valid without
        them, it just will not show up in anything that groups by period.
        """
        db = DB()
        rows = db.get_specific_sql(
            "SELECT period, startTime, finishTime FROM periods ORDER BY period") or []
        del db

        def as_minutes(value) -> Optional[int]:
            text = str(value)[:5]
            try:
                parsed = datetime.strptime(text, "%H:%M")
            except ValueError:
                return None
            return parsed.hour * 60 + parsed.minute

        begins, ends = as_minutes(start_time), as_minutes(finish_time)
        if begins is None or ends is None:
            return None, None

        covered = [
            row["period"] for row in rows
            if (as_minutes(row["startTime"]) is not None
                and as_minutes(row["finishTime"]) is not None
                # Any overlap counts, so a booking that starts mid-period
                # still reports the period it started in.
                and as_minutes(row["startTime"]) < ends
                and as_minutes(row["finishTime"]) > begins)
        ]
        if not covered:
            return None, None
        return covered[0], covered[-1]

    def add_manual_schedules(self, columns, records):
        """Insert the generated rows, reporting a database refusal as itself."""
        db = DB("schedules")
        try:
            return db.create_multiple_records(columns, records)
        finally:
            del db

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
