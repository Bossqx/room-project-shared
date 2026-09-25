from src.util.dbcontroller import DBController as DB


class Dashboard_Controller():

    def create_index(self):
        db = DB()
        sql = "CREATE INDEX idx_room_usages_room_date ON room_usages (room_no, booking_date)"
        try:
            result = db.set_specific_sql(sql, None)
        except Exception as e:
            result = {"Flag": False, "err": str(e)}
        del db
        return result

    def get_raw_schedule(self, room_no, date_from, date_to):
        db = DB()
        sql = """SELECT
                    A.id,
                    A.user_name    AS teacher,
                    A.room_no      AS roomcode,
                    A.subject_code AS coursecode,
                    A.objective    AS coursename,
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    A.start_time   AS startTime,
                    A.finish_time  AS finishTime,
                    A.booking_date AS schedule_date,
                    T1.period      AS timeperiodfrom,
                    T2.period      AS timeperiodto,
                    FALSE          AS isExist,
                    'booking'      AS record_type
        FROM room_usages A
        LEFT OUTER JOIN periods T1 ON A.start_time  = T1.startTime
        LEFT OUTER JOIN periods T2 ON A.finish_time = T2.finishTime
        WHERE A.room_no = %s
          AND A.booking_date >= %s
          AND A.booking_date <  DATE_ADD(%s, INTERVAL 1 DAY)
        ORDER BY A.booking_date, A.start_time"""
        params = (room_no, date_from, date_to)
        results = db.get_specific_sql(sql, None, params)
        del db
        return results

    def get_summary_stats(self, room_no, date_from, date_to):
        db = DB()
        sql = """SELECT
                    COUNT(*)                       AS total_bookings,
                    COUNT(DISTINCT A.booking_date) AS days_used,
                    COUNT(DISTINCT A.user_name)    AS distinct_teachers,
                    COUNT(DISTINCT A.subject_code) AS distinct_courses
        FROM room_usages A
        WHERE A.room_no = %s
          AND A.booking_date >= %s
          AND A.booking_date <  DATE_ADD(%s, INTERVAL 1 DAY)"""
        params = (room_no, date_from, date_to)
        results = db.get_specific_sql(sql, None, params)
        del db
        return results[0] if results else None

    def get_occupancy_rate(self, room_no, date_from, date_to):
        db = DB()
        sql = """SELECT
                    booked.slots_booked,
                    total.slots_available,
                    ROUND(booked.slots_booked / total.slots_available * 100, 1) AS occupancy_pct
        FROM
            (SELECT COUNT(*) AS slots_booked
             FROM room_usages A
             WHERE A.room_no = %s
               AND A.booking_date >= %s
               AND A.booking_date <  DATE_ADD(%s, INTERVAL 1 DAY)
            ) AS booked,
            (SELECT
                 (SELECT COUNT(*) FROM periods) *
                 (DATEDIFF(%s, %s) + 1) AS slots_available
            ) AS total"""
        params = (room_no, date_from, date_to, date_to, date_from)
        results = db.get_specific_sql(sql, None, params)
        del db
        return results[0] if results else None

    def get_top_teachers(self, room_no, date_from, date_to, limit=5):
        db = DB()
        sql = """SELECT
                    A.user_name AS teacher,
                    COUNT(*)    AS sessions
        FROM room_usages A
        WHERE A.room_no = %s
          AND A.booking_date >= %s
          AND A.booking_date <  DATE_ADD(%s, INTERVAL 1 DAY)
        GROUP BY A.user_name
        ORDER BY sessions DESC
        LIMIT %s"""
        params = (room_no, date_from, date_to, limit)
        results = db.get_specific_sql(sql, None, params)
        del db
        return results

    def get_top_courses(self, room_no, date_from, date_to, limit=5):
        db = DB()
        sql = """SELECT
                    A.subject_code AS coursecode,
                    A.objective    AS coursename,
                    COUNT(*)       AS sessions
        FROM room_usages A
        WHERE A.room_no = %s
          AND A.booking_date >= %s
          AND A.booking_date <  DATE_ADD(%s, INTERVAL 1 DAY)
        GROUP BY A.subject_code, A.objective
        ORDER BY sessions DESC
        LIMIT %s"""
        params = (room_no, date_from, date_to, limit)
        results = db.get_specific_sql(sql, None, params)
        del db
        return results

    def get_weekly_grid(self, room_no, date_from, date_to):
        db = DB()
        sql = """SELECT
                    CASE WHEN A.weekday = 7 THEN 1 ELSE A.weekday + 1 END AS weekday,
                    T1.period      AS period_from,
                    T2.period      AS period_to,
                    A.subject_code AS coursecode,
                    A.user_name    AS teacher
        FROM room_usages A
        LEFT OUTER JOIN periods T1 ON A.start_time  = T1.startTime
        LEFT OUTER JOIN periods T2 ON A.finish_time = T2.finishTime
        WHERE A.room_no = %s
          AND A.booking_date >= %s
          AND A.booking_date <  DATE_ADD(%s, INTERVAL 1 DAY)
        ORDER BY weekday, period_from"""
        params = (room_no, date_from, date_to)
        results = db.get_specific_sql(sql, None, params)
        del db
        return results
