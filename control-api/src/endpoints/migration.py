from fastapi import APIRouter, Query
from fastapi import  HTTPException
from src.models.schedule import Schedule_Controller
from src.models.migration import Migration_Controller,Semester_Base,Semester_Controller
from src.util.dbcontroller import DBController as DB
from datetime import date, datetime, timedelta
from fastapi import HTTPException



router = APIRouter(
    prefix="/migration",
    tags=["migration"],
    responses={404: {"description": "Not found"}},
)

@router.post("/create_semester/")
async def create_semester(semester:Semester_Base):
    db =Semester_Controller()
    result=db.add(semester.dict())
    return result

@router.get("/set_status/{id}")
async def set_status(id:int):
    db =Semester_Controller()
    db.reset_status()
    result=db.set_status(id)
    return result 

@router.get("/get_list_semester/")
async def get_list_semester():
    db=Semester_Controller()
    results=db.get_list_semester()
    del db 
    return results 




@router.get("/remove_schedule/")
async def remove_schedule():
    db=Migration_Controller()
    result=db.remove_all_schedules()
    return result 



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


@router.post("/set_schedules/")
async def set_schedules(
    start_date: date,
    end_date: date,
    delta_day: int = 14,
):
    if delta_day <= 0:
        raise HTTPException(
            status_code=422,
            detail="delta_day must be a positive integer.",
        )

    db = Schedule_Controller()
    try:
        current_schedule = db.get_current()
        if current_schedule is None:
            raise HTTPException(
                status_code=404,
                detail="No current schedule found.",
            )

        rooms = db.get_all_rooms()

        start_date_obj = _to_datetime(start_date)
        end_date_obj = _to_datetime(end_date)
        last_date = (start_date_obj + timedelta(days=delta_day)).strftime("%Y-%m-%d")

        results = []
        for item in rooms:
            result = db.get_schedule_datasets(
                item["room_no"],
                start_date_obj.strftime("%Y-%m-%d"),
                last_date,
                current_schedule,
            )
            results.append(result)
    finally:
        # Ensures the DB connection/resources are released even if an
        # exception occurs above, unlike a bare `del db`.
        if hasattr(db, "close"):
            db.close()

    columns = [
        "roomcode", "weekday", "timeperiodfrom", "timeperiodto", "coursecode", "coursename",
        "revisioncode", "periodfrom", "periodto", "week_type", "week_no", "schedule_date",
        "teacher_name", "startTime", "finishTime", "yearNo", "semester","userCode"
    ]

    records = [
        tuple(schedule_item.get(col) for col in columns)
        for room_result in results
        for day_entry in (room_result or [])
        for schedule_item in day_entry.get("schedule", [])
    ]

    temp_records = list(records)
    schedule_date_idx = columns.index("schedule_date")

    # Repeat the base date range forward by delta_day increments until we
    # pass end_date. Since delta_day > 0 is now guaranteed above, this loop
    # is guaranteed to terminate.
    cycle = 1
    while True:
        shift_days = timedelta(days=delta_day * cycle)
        shifted_batch = []
        for record in records:
            old_date = datetime.strptime(record[schedule_date_idx], "%Y-%m-%d")
            new_date = old_date + shift_days
            if new_date > end_date_obj:
                continue
            new_record = list(record)
            new_record[schedule_date_idx] = new_date.strftime("%Y-%m-%d")
            shifted_batch.append(tuple(new_record))

        if not shifted_batch:
            break

        temp_records.extend(shifted_batch)
        cycle += 1

    if not temp_records:
        return {"affected_rows": 0}

    schedules_db = DB("schedules")
    result = schedules_db.create_multiple_records(columns, temp_records)
    return result