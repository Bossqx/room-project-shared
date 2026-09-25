from fastapi import APIRouter, File,  Query
from fastapi import  HTTPException
from src.models.schedule import Schedule_Controller
from src.models.roomUsage import RoomUsage_Controller
from src.endpoints.send_to_device import publish_to_mqtt
from src.util.dbcontroller import DBController as DB
from datetime import date, datetime
from typing import Literal, Optional
import os
import json

router = APIRouter(
    prefix="/schedule",
    tags=["schedule"],
    responses={404: {"description": "Not found"}},
)

# @router.get("/get_booking_at_current_time/")
# async def get_booking_at_current_time():
#     db = Schedule_Controller()
#     results=db.get_booking_at_current_time()
#     return results 

@router.get("/delete_schedule_by_id/")
async def delete_schedule_by_id(schedule_id: str,source_type: str):
    db = Schedule_Controller()
    result = db.delete_schedule_by_id(schedule_id, source_type) 
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found or could not be deleted")
    return {"success": True, "schedule_id": schedule_id, "source_type": source_type or 'schedule'}

@router.get("/get_schedule_by_id/")
async def get_schedule_by_id(schedule_id: str,source_type: Optional[str] = Query(None, description="Filter by source: 'MIS Schedule', 'booking', or omit for all.")):
    db = Schedule_Controller()
    result = db.get_schedule_by_id(schedule_id, source_type)
    if result is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return result

@router.get("/get_schedule_by_id/{schedule_id}")
async def get_schedule_by_id(schedule_id: str):
    db = Schedule_Controller()
    result = db.get_schedule_by_id(schedule_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return result


@router.get("/get_rooms_dashboard/")
async def get_rooms_dashboard():
    db = Schedule_Controller()
    result=db.get_rooms_dashboard()
    return result 

@router.get("/get_empty_rooms_db/{room_code}")
async def get_empty_rooms_db(
    room_code: str,
    schedule_date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    choose_date = datetime.strptime(schedule_date, "%Y-%m-%d").date() if schedule_date else date.today()
    #get_empty_rooms_db(self,scheduleDate=datetime.now(),roomCode=None):
    result = db.get_empty_rooms_db(choose_date, room_code)
    if result is None:
        raise HTTPException(status_code=404, detail="Empty rooms not found")
    return result


@router.get("/get_schedule_all_empty_rooms/")
async def get_schedule_all_empty_rooms(
    schedule_date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
):
    db = Schedule_Controller()
    # current_schedule = db.get_current()
    # if current_schedule is None:
    #     raise HTTPException(status_code=404, detail="Current schedule not found")
    # year_no = current_schedule['year_no']
    # semester_no = current_schedule['semester']
    choose_date = datetime.strptime(schedule_date, "%Y-%m-%d").date() if schedule_date else date.today()
    empty_rooms = db.get_schedule_all_empty_rooms(choose_date)
    if empty_rooms is None:
        raise HTTPException(status_code=404, detail="Empty rooms not found")
    return empty_rooms

@router.get("/get_empty_rooms")
async def get_empty_rooms(
    schedule_date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
    room_code: Optional[str] = Query(None, description="Filter by room code (first 8 characters).")
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    choose_date = datetime.strptime(schedule_date, "%Y-%m-%d").date() if schedule_date else date.today()
    empty_rooms = db.get_empty_rooms(year_no, semester_no, choose_date, room_code)
    if empty_rooms is None:
        raise HTTPException(status_code=404, detail="Empty rooms not found")
    return empty_rooms


@router.get("/get_empty_rooms_db")
async def get_empty_rooms_db(
    schedule_date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
    room_code: Optional[str] = Query(None, description="Filter by room code (first 8 characters).")
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    choose_date = datetime.strptime(schedule_date, "%Y-%m-%d").date() if schedule_date else date.today()
    empty_rooms = db.get_empty_rooms_db(choose_date, room_code)
    if empty_rooms is None:
        raise HTTPException(status_code=404, detail="Empty rooms not found")
    return empty_rooms

@router.get("/get_booking_db/{room_code}")
async def  get_booking_db(room_code:str):
    ctrl=  Schedule_Controller()
    return ctrl.get_booking_db(room_code) 

@router.get("/get_week_type/")
async def get_week_type(year_no: int, semester_no: int):
    db = Schedule_Controller()
    week_type = db.get_week_type(year_no, semester_no)
    if week_type is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"week_type": week_type}

@router.get("/get_list_current_rooms/")
async def get_list_current_rooms():
    db=Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester = current_schedule['semester']
    results=db.get_list_current_rooms(year_no,semester)
    return results 

@router.get("/get_rooms_by_user/user/{user_code}")
async def get_rooms_by_user(
    user_code: str,
    schedule_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today.")
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    schedule = db.get_rooms_by_user(year_no, semester_no, user_code, schedule_date)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/get_rooms_by_user_date/user/{user_code}/")
async def get_rooms_by_user_date(user_code:str,schedule_date:str):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    choose_date = datetime.strptime(schedule_date, "%Y-%m-%d").date() if schedule_date else date.today()
    schedule = db.get_schedule_by_room_date(year_no, semester_no, user_code, choose_date)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.get("/migrate_schedule_2_json/")
async def migrate_schedule_2_json():
    db = Schedule_Controller()
    result=db.migrate_schedule_2_json()
    return result


@router.get("/get_schedule_from_json/")
async def get_schedule_from_json():
    db = Schedule_Controller()
    result = db.get_schedule_from_json()
    if result is None:
        raise HTTPException(status_code=404, detail="schedule_all.json not found — run migrate_schedule_2_json first")
    return result



@router.get("/get_schedule_all_DB/")
async def get_schedule_all_DB():
    db = Schedule_Controller()
    results=db.get_schedule_all_DB()
    del db 
    return results 


@router.get("/get_current_schedule_DB/")
async def get_current_schedule_DB(roomCode: str):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    today=datetime.now().strftime("%Y-%m-%d")
    schedule = db.get_schedule_by_rooms_db(roomCode,today)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule     

@router.get("/get_current_schedule/")
async def get_current_schedule(room_code: str):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    today=datetime.now().strftime("%Y-%m-%d")
    schedule = db.get_schedule_by_room(year_no, semester_no, room_code,today)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

@router.get("/get_schedule_booking_room_by_date/")
async def get_schedule_booking_room_by_date(booking_date:str ):
    db = Schedule_Controller()
    results=db.get_schedule_booking_room_by_date(booking_date)
    return results 


@router.get("/get_schedule_by_weekly_db/")
async def get_schedule_by_date():
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    week_dates = db.get_dates_on_week()
    results=[]
    for item_date in week_dates:
        schedule=db.get_schedule_by_weekly_db(item_date)
        if schedule:
            obj={
                "date":item_date,
                "schedule":schedule
            }
            results.append(obj)
    return results 

    




@router.get("/get_schedule_weekly/{room_code}")
async def get_schedule_weekly(room_code: str):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    week_dates = db.get_dates_on_week()
    #return week_dates
    if week_dates is None:
        raise HTTPException(status_code=404, detail="Week dates not found")

    weekly_schedule = []
    for schedule_date in week_dates:
        daily_schedule = db.get_schedule_by_criteria(year_no, semester_no, room_code, schedule_date)
        if daily_schedule is not None:
            weekly_schedule.append({
                "date": schedule_date,
                "schedule": daily_schedule
            })

    return weekly_schedule

@router.get("/get_all_schedule/")
async def get_all_schedule(startDate,finishDate):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
            return None
    rooms=db.get_all_rooms()
    #return rooms
    results=[]
    for item in rooms:
        result=db.get_schedule_datasets(item["room_no"],startDate,finishDate,current_schedule)
        results.append(result)
    del db

    columns = [
        "roomcode", "weekday", "timeperiodfrom", "timeperiodto", "coursecode", "coursename",
        "revisioncode", "periodfrom", "periodto", "week_type", "week_no", "schedule_date",
        "teacher_name", "startTime", "finishTime", "yearNo", "semester",
    ]
    records = [
        tuple(schedule_item.get(col) for col in columns)
        for room_result in results
        for day_entry in (room_result or [])
        for schedule_item in day_entry.get("schedule", [])
    ]

    if records:
        schedules_db = DB("schedules")
        schedules_db.create_multiple_records(columns, records)

    return results


@router.get("/get_schedule_datasets/{roomcode}")
async def get_schedule_datasets(roomCode,startDate,finishDate):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
            return None
    results=db.get_schedule_datasets(roomCode,startDate,finishDate,current_schedule)
    return results 

@router.get("/get_schedule_migrate/{roomCode}")
async def get_schedule_migrate(
    room_code: str,
    schedule_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today.")
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    schedule = db.get_schedule_migrate(year_no, semester_no, room_code, schedule_date)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return schedule






@router.get("/get_schedule_by_criteria/{room_code}")
async def get_schedule_by_criteria(
    room_code: str,
    schedule_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today.")
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    year_no = current_schedule['year_no']
    semester_no = current_schedule['semester']
    schedule = db.get_schedule_by_criteria(year_no, semester_no, room_code, schedule_date)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    usage_db = RoomUsage_Controller()
    for item in schedule:
        check = usage_db.get_exist_by_time(item['uuid'],item['roomcode'], item.get('startTime', ''), item.get('finishTime', ''))
        item['isExist'] = check['isExist']
    return schedule

@router.get("/get_schedule_by_criteria_db/{room_code}")
async def get_schedule_by_criteria_db(
    room_code: str,
    schedule_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
    source_type: Optional[str] = Query(None, description="Filter by source: 'MIS Schedule', 'booking', or omit for all.")
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    # year_no = current_schedule['year_no']
    # semester_no = current_schedule['semester']
    choose_date = schedule_date.strftime("%Y-%m-%d") if schedule_date else date.today().strftime("%Y-%m-%d")
    schedule = db.get_schedule_by_criteria_db(room_code,source_type,choose_date)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    #usage_db = RoomUsage_Controller()
    # for item in schedule:
    #     check = usage_db.get_exist_by_time(item['uuid'],item['roomcode'], item.get('startTime', ''), item.get('finishTime', ''))
    #     item['isExist'] = check['isExist']
    return schedule


@router.get("/get_schedule_by_date_range_db/")
async def get_schedule_by_date_range_db(
    room_code: str,
    start_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
    finish_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD). Defaults to today."),
):
    db = Schedule_Controller()
    current_schedule = db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="Current schedule not found")
    start = start_date or date.today()
    finish = finish_date or date.today()
    schedule = db.get_schedule_by_date_range_db(room_code, start, finish)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule




@router.get("/is_allow_booking/{room_code}")
async def get_is_allow_booking(
    room_code: str,
    booking_date: str,
    start_time: str,
    finish_time: str
):
    db = Schedule_Controller()
    # current_schedule = db.get_current()
    # if current_schedule is None:
    #     raise HTTPException(status_code=404, detail="Current schedule not found")
    # today       = date.today().strftime("%Y-%m-%d")

    #schedules = db.get_schedule_by_criteria(year_no, semester_no, room_code, today) or []
    schedules=db.get_schedule_by_criteria_db(room_code,None,booking_date) or []

    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(':'))
        return h * 60 + m

    req_start = to_minutes(start_time)
    req_end   = to_minutes(finish_time)

    def same_date(s) -> bool:
        sd = s.get('schedule_date')
        if sd is None:
            return False
        return str(sd)[:10] == booking_date[:10]

    conflicts = [
        s for s in schedules
        if same_date(s)
        and s.get('startTime') and s.get('finishTime')
        and to_minutes(s['startTime']) < req_end
        and to_minutes(s['finishTime']) > req_start
    ]

    return {
        "isAllow":    len(conflicts) == 0,
        "conflicts":  conflicts,
    }

@router.post("/notify_update")
async def notify_update(
    status: Literal["booking_schedule", "delete","confirm_schedule"] = "replace"
):
    payload = json.dumps({
        "status": status,
        "update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    try:
        publish_to_mqtt("update_schedule", payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "topic": "update_schedule", "payload": payload}


@router.get("/get_sample_set")
async def get_sample_set():
    path = os.path.join(os.path.dirname(__file__), '..', '..',  'config', 'sampleset.json')
    print(path)
    with open(os.path.abspath(path), encoding='utf-8') as f:
        return json.load(f)



@router.get("/get_active_semester")
async def get_active_semester():
    db=Schedule_Controller()
    result=db.get_active_semester()
    return result

@router.get("/schedule_decode/{schedule_id}")
async def schedule_decode(schedule_id: str):
    db = Schedule_Controller()
    decoded_schedule = db.schedule_decode(schedule_id)
    if decoded_schedule is None:
        raise HTTPException(status_code=404, detail="Invalid schedule ID")
    return decoded_schedule

@router.get("/get_schedule_by_room/{year_no}/{semester_no}/{room_code}")
async def get_schedule_by_room(year_no: int, semester_no: int, room_code: str):
    db = Schedule_Controller()
    schedule = db.get_schedule_by_room(year_no, semester_no, room_code)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

@router.get("/remove_schedule/{id}")
async def remove_schedule(id:int):
    db = Schedule_Controller()
    result=db.remove_schedule(id)
    return result 


@router.get("/remove_booking/{id}")
async def remove_booking(id:int):
    db = Schedule_Controller()
    result=db.remove_booking(id)
    return result 

@router.get("/set_schedule_usage_status/")
async def set_schedule_usage_status(
    schedule_id: str,
    status: int=0,
    source_type: Optional[str] = Query(None, description="Filter by source: 'MIS Schedule', 'booking', or omit for all.")
):
    db = Schedule_Controller()
    result = db.set_schedule_usage_status(schedule_id, source_type or 'schedule', status)
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found or status unchanged")
    return {"success": True, "schedule_id": schedule_id, "source_type": source_type or 'schedule', "status": status}


@router.get("/check_usage_status/")
async def check_usage_status(schedule_id: str,source_type: Optional[str] = Query(None, description="Filter by source: 'MIS Schedule', 'booking', or omit for all.")):
    db = Schedule_Controller()
    result = db.check_usage_status(schedule_id, source_type or 'schedule')
    if result is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"schedule_id": schedule_id, "source_type": source_type or 'schedule', "usage_status": result}


##get_schedule_TEST(self,yearNo,semester,roomCode,scheduleDate=datetime.now):
@router.get("/migration_test/")
async def get_schedule_TEST(yearNo,semester,roomCode,scheduleDate=datetime.now):
    db = Schedule_Controller()
    results = db.get_schedule_TEST(yearNo,semester,roomCode,scheduleDate)
    return results

# @router.get("/check_usage_status/")
# async def check_usage_status(schedule_id: str,source_type: Optional[str] = Query(None, description="Filter by source: 'MIS Schedule', 'booking', or omit for all.")):  
#     db = Schedule_Controller()
#     result = db.check_usage_status(schedule_id, source_type )
#     if result is None:
#         raise HTTPException(status_code=404, detail="Schedule not found")
#     return {"schedule_id": schedule_id, "status": result}   


