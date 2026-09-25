from fastapi import APIRouter
from src.util.dbcontroller import DBController

router = APIRouter()

@router.get("/connection")
def test_connection():
    try:
        db = DBController()
        conn = db.get_conn()
        if conn and conn.is_connected():
            info = conn.get_server_info()
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE()")
            database = cursor.fetchone()[0]
            cursor.close()
            return {
                "status": "ok",
                "connected": True,
                "server_version": info,
                "database": database,
            }
        return {"status": "fail", "connected": False, "detail": "Connection returned None"}
    except Exception as e:
        return {"status": "error", "connected": False, "detail": str(e)}
