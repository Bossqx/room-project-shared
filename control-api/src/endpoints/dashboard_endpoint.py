from fastapi import APIRouter, Query
from fastapi import HTTPException
from src.models.dashboard_model import Dashboard_Controller
from datetime import date

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)


@router.get("/create_index/")
async def create_index():
    db = Dashboard_Controller()
    result = db.create_index()
    return result


@router.get("/raw_schedule/")
async def raw_schedule(
    room_no: str,
    date_from: date = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    date_to: date = Query(None, description="End date (YYYY-MM-DD), inclusive. Defaults to today."),
):
    db = Dashboard_Controller()
    from_date = date_from or date.today()
    to_date = date_to or date.today()
    results = db.get_raw_schedule(room_no, from_date, to_date)
    if results is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return results


@router.get("/summary/")
async def summary(
    room_no: str,
    date_from: date = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    date_to: date = Query(None, description="End date (YYYY-MM-DD), inclusive. Defaults to today."),
):
    db = Dashboard_Controller()
    from_date = date_from or date.today()
    to_date = date_to or date.today()
    result = db.get_summary_stats(room_no, from_date, to_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return result


@router.get("/occupancy/")
async def occupancy(
    room_no: str,
    date_from: date = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    date_to: date = Query(None, description="End date (YYYY-MM-DD), inclusive. Defaults to today."),
):
    db = Dashboard_Controller()
    from_date = date_from or date.today()
    to_date = date_to or date.today()
    result = db.get_occupancy_rate(room_no, from_date, to_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Occupancy data not found")
    return result


@router.get("/top_teachers/")
async def top_teachers(
    room_no: str,
    date_from: date = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    date_to: date = Query(None, description="End date (YYYY-MM-DD), inclusive. Defaults to today."),
    limit: int = Query(5, description="Number of teachers to return."),
):
    db = Dashboard_Controller()
    from_date = date_from or date.today()
    to_date = date_to or date.today()
    results = db.get_top_teachers(room_no, from_date, to_date, limit)
    if results is None:
        raise HTTPException(status_code=404, detail="Top teachers not found")
    return results


@router.get("/top_courses/")
async def top_courses(
    room_no: str,
    date_from: date = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    date_to: date = Query(None, description="End date (YYYY-MM-DD), inclusive. Defaults to today."),
    limit: int = Query(5, description="Number of courses to return."),
):
    db = Dashboard_Controller()
    from_date = date_from or date.today()
    to_date = date_to or date.today()
    results = db.get_top_courses(room_no, from_date, to_date, limit)
    if results is None:
        raise HTTPException(status_code=404, detail="Top courses not found")
    return results


@router.get("/weekly_grid/")
async def weekly_grid(
    room_no: str,
    date_from: date = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    date_to: date = Query(None, description="End date (YYYY-MM-DD), inclusive. Defaults to today."),
):
    db = Dashboard_Controller()
    from_date = date_from or date.today()
    to_date = date_to or date.today()
    results = db.get_weekly_grid(room_no, from_date, to_date)
    if results is None:
        raise HTTPException(status_code=404, detail="Weekly grid not found")
    return results
