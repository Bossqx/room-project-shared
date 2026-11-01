from fastapi import APIRouter, Query
from fastapi import  HTTPException
from src.models.schedule import Schedule_Controller
from src.models.migration import Migration_Controller,ManualSchedule_Base,ManualScheduleAllRooms_Base,Semester_Base,Semester_Controller
from src.util.dbcontroller import DBController as DB
from datetime import date, datetime, timedelta
from typing import Optional
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


# A year of daily rows for every room is already tens of thousands of inserts;
# anything beyond it is a mistyped year rather than a real booking.
MAX_MANUAL_DAYS = 366


def _to_hhmm(value: str, field: str) -> str:
    """Accept HH:MM or HH:MM:SS, return HH:MM, and say which field was wrong."""
    text = str(value or "").strip()
    for pattern in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).strftime("%H:%M")
        except ValueError:
            continue
    raise HTTPException(
        status_code=422,
        detail=f"Invalid {field}: {value!r}. Expected HH:MM.",
    )


# One room booked for one day is five or so database connections, and
# set_manual_schedule_all makes that call for every room on every date. This
# is where an innocent-looking request — every room, a whole term — stops
# being a few thousand connections.
MAX_MANUAL_CALLS = 1000


@router.get("/get_rooms/")
async def get_rooms(
    search: Optional[str] = Query(
        None,
        description="Narrow the list to room numbers containing this text. "
                    "Leave it out, or send it empty, for every room.",
    ),
):
    """
    The rooms set_manual_schedule will accept, for the form that calls it.

    Read straight from the rooms table in room_no order, which is the list
    set_manual_schedule validates its room_no against — so anything chosen
    here is accepted there.

    search is optional: omitted, empty or null all list every room, so a form
    can send its search box through unconditionally.
    """
    db = Migration_Controller()
    rooms = db.list_rooms(search)
    return {
        "count": len(rooms),
        "room_numbers": [room["room_no"] for room in rooms],
        "rooms": rooms,
    }


@router.post("/set_manual_schedule/")
async def set_manual_schedule(payload: ManualSchedule_Base):
    """
    Book one or more rooms at the same hours on every date in a range.

    One schedule row per room per date, from start_date to finish_date
    inclusive, all carrying the given start_time and finish_time. weekday is
    derived from each row's own date rather than taken from the caller, so it
    always agrees with schedule_date.
    """
    start_date = _to_datetime(payload.start_date).date()
    finish_date = _to_datetime(payload.finish_date).date()
    if finish_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="finish_date must not be earlier than start_date.",
        )

    span = (finish_date - start_date).days + 1
    if span > MAX_MANUAL_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Date range covers {span} days; the limit is {MAX_MANUAL_DAYS}.",
        )

    start_time = _to_hhmm(payload.start_time, "start_time")
    finish_time = _to_hhmm(payload.finish_time, "finish_time")
    if finish_time <= start_time:
        raise HTTPException(
            status_code=422,
            detail="finish_time must be later than start_time.",
        )

    db = Migration_Controller()
    rooms, unknown = db.get_room_numbers(payload.room_no)
    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"No such room in the rooms table: {', '.join(unknown)}",
        )
    if not rooms:
        raise HTTPException(status_code=404, detail="No rooms to schedule.")

    schedule_db = Schedule_Controller()
    current_schedule = schedule_db.get_current()
    if current_schedule is None:
        raise HTTPException(status_code=404, detail="No current schedule found.")
    year_no = current_schedule["year_no"]
    semester = current_schedule["semester"]

    period_from, period_to = db.get_periods_for_times(start_time, finish_time)

    columns = [
        "roomcode", "weekday", "timeperiodfrom", "timeperiodto", "coursecode", "coursename",
        "revisioncode", "periodfrom", "periodto", "week_type", "week_no", "schedule_date",
        "teacher_name", "startTime", "finishTime", "yearNo", "semester", "userCode"
    ]

    records = []
    dates = []
    # The week number is the same for every room on a given date, so it is
    # looked up once per date rather than once per row.
    current_date = start_date
    while current_date <= finish_date:
        date_str = current_date.strftime("%Y-%m-%d")
        # Read back off the string that goes into schedule_date, so the
        # weekday column can never describe a different day from the one
        # stored beside it.
        weekday = Migration_Controller.weekday_of(date_str)
        week_info = schedule_db.get_week_type_no_by_date(year_no, semester, date_str) or {}
        dates.append(date_str)
        for room in rooms:
            records.append((
                room,
                weekday,
                period_from,
                period_to,
                payload.coursecode,
                payload.coursename,
                None,
                period_from,
                period_to,
                week_info.get("week_type"),
                week_info.get("week_no"),
                date_str,
                payload.teacher_name,
                start_time,
                finish_time,
                year_no,
                semester,
                payload.userCode,
            ))
        current_date += timedelta(days=1)

    try:
        result = db.add_manual_schedules(columns, records)
    except Exception as error:
        # create_multiple_records swallows the driver error and leaves its
        # row count unbound, so a refused insert surfaces here as something
        # unrelated. Report the insert as the thing that failed.
        raise HTTPException(
            status_code=500,
            detail=f"Could not insert the schedule rows: {error}",
        )

    return {
        "affected_rows": (result or {}).get("affected_rows", 0),
        "rooms": rooms,
        "dates": dates,
        "rows_built": len(records),
        "startTime": start_time,
        "finishTime": finish_time,
        "periodfrom": period_from,
        "periodto": period_to,
        "yearNo": year_no,
        "semester": semester,
    }


@router.post("/set_manual_schedule_all/")
async def set_manual_schedule_all(payload: ManualScheduleAllRooms_Base):
    """
    Run set_manual_schedule once per room per date.

    Two nested loops: the rooms get_rooms returns, and inside each of them
    every date from start_date to finish_date. Each call books one room on
    one day, so a room the database refuses on one date is reported against
    that room and that date, and every other room and date is still written.
    A complaint about the payload itself would repeat for every call, so the
    first one stops the run before anything is inserted.
    """
    start_date = _to_datetime(payload.start_date).date()
    finish_date = _to_datetime(payload.finish_date).date()
    if finish_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="finish_date must not be earlier than start_date.",
        )

    # Built once and reused for every room: the range is the same whichever
    # room is being booked.
    dates = []
    current_date = start_date
    while current_date <= finish_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    db = Migration_Controller()
    rooms = db.list_rooms(payload.search)
    if not rooms:
        raise HTTPException(
            status_code=404,
            detail=(f"No room matches {payload.search!r}." if payload.search
                    else "No rooms found in the rooms table."),
        )

    planned = len(rooms) * len(dates)
    if planned > MAX_MANUAL_CALLS:
        raise HTTPException(
            status_code=422,
            detail=(f"{len(rooms)} rooms x {len(dates)} dates is {planned} separate "
                    f"bookings; the limit is {MAX_MANUAL_CALLS}. Narrow the range, "
                    f"use search, or post to /migration/set_manual_schedule/ with a "
                    f"list of rooms to write the whole range in one go."),
        )

    shared = payload.model_dump(exclude={"search", "start_date", "finish_date"})

    results = []
    affected_rows = 0
    for room in rooms:
        room_no = room["room_no"]
        day_results = []
        room_rows = 0
        for day in dates:
            try:
                outcome = await set_manual_schedule(ManualSchedule_Base(
                    room_no=room_no,
                    start_date=day,
                    finish_date=day,
                    **shared,
                ))
            except HTTPException as error:
                if error.status_code == 422:
                    # Wrong payload, not a wrong room or date. Every call
                    # still to come would fail the same way.
                    raise
                day_results.append({
                    "schedule_date": day.strftime("%Y-%m-%d"),
                    "status": "failed",
                    "status_code": error.status_code,
                    "detail": error.detail,
                })
                continue

            rows = outcome.get("affected_rows", 0)
            room_rows += rows
            day_results.append({
                "schedule_date": day.strftime("%Y-%m-%d"),
                "status": "ok",
                "affected_rows": rows,
            })

        affected_rows += room_rows
        failed_days = [item for item in day_results if item["status"] == "failed"]
        if not failed_days:
            status = "ok"
        elif len(failed_days) == len(day_results):
            status = "failed"
        else:
            status = "partial"
        results.append({
            "room_no": room_no,
            "status": status,
            "affected_rows": room_rows,
            "dates_written": len(day_results) - len(failed_days),
            "dates_failed": len(failed_days),
            "dates": day_results,
        })

    failed = [item for item in results if item["status"] == "failed"]
    return {
        "rooms_requested": len(rooms),
        "rooms_scheduled": len(results) - len(failed),
        "rooms_failed": len(failed),
        "dates_per_room": len(dates),
        "calls": planned,
        "affected_rows": affected_rows,
        "startTime": payload.start_time,
        "finishTime": payload.finish_time,
        "results": results,
    }
