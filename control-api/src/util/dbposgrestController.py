import psycopg2
from psycopg2 import Error
import json


class DBController():
    def __init__(self, table_name=None):
        self.tablename = table_name
        self.conn = self.get_connection()

    def get_connection(self):
        file = open('././config/config.json')
        data = json.load(file)
        config = data["postgres_config"]
        try:
            conn = psycopg2.connect(**config)
            return conn
        except Error as e:
            print("Error while connecting to PostgreSQL", e)
            return None

    def get_conn(self):
        """Return the database connection."""
        return self.conn

    def create_multiple_records(self, attribute_names, records):
        sql = f"INSERT INTO {self.tablename}("
        sql_param = "VALUES("
        params = []
        
        for attribute in attribute_names:
            sql += f"{attribute},"
            sql_param += "%s,"

        sql = sql.rstrip(",\n") + ")\n"
        sql_param = sql_param.rstrip(",") + ")\n"
        sql += sql_param
        
        try:
            cursor = self.conn.cursor()

            # Execute the insert statement with multiple values
            cursor.executemany(sql, records)

            # Commit the changes to the database
            self.conn.commit()

            # Get the number of affected rows
            affected_rows = cursor.rowcount
            print(f"{affected_rows} record(s) inserted successfully.")

        except psycopg2.Error as error:
            # Rollback in case of an error
            self.conn.rollback()
            print(f"Error inserting records: {error}")

        finally:
            # Close the cursor and the database connection
            cursor.close()
            self.conn.close()
            
        return {"affected_rows": affected_rows}

    def create_multiple_records_T(self, conn, attribute_names, records):
        sql = f"INSERT INTO {self.tablename}("
        sql_param = "VALUES("
        params = []
        
        for attribute in attribute_names:
            sql += f"{attribute},"
            sql_param += "%s,"

        sql = sql.rstrip(",\n") + ")\n"
        sql_param = sql_param.rstrip(",") + ")\n"
        sql += sql_param
        
        try:
            cursor = conn.cursor()

            # Execute the insert statement with multiple values
            cursor.executemany(sql, records)

            # Commit the changes to the database
            conn.commit()

            # Get the number of affected rows
            affected_rows = cursor.rowcount
            print(f"{affected_rows} record(s) inserted successfully.")
            cursor.close()

        except psycopg2.Error as error:
            # Rollback in case of an error
            conn.rollback()
            print(f"Error inserting records: {error}")

        return {"affected_rows": affected_rows}

    def update_multiple_records(self, attribute_names, records):
        sql = f"UPDATE {self.tablename} SET "
        for i, attribute in enumerate(attribute_names):
            if attribute != "id":
                if i < len(attribute_names) - 1:
                    sql += f"{attribute} = %s, "
                else:
                    sql += f"{attribute} = %s "

        sql = sql.rstrip(", ") + " WHERE id=%s"
        try:
            cursor = self.conn.cursor()
            # Execute the update statement with multiple values
            cursor.executemany(sql, records)
            # Commit the changes to the database
            self.conn.commit()
            # Get the number of affected rows
            affected_rows = cursor.rowcount
            print(f"{affected_rows} record(s) updated successfully.")

        except psycopg2.Error as error:
            # Rollback in case of an error
            self.conn.rollback()
            print(f"Error updating records: {error}")

        finally:
            # Close the cursor and the database connection
            cursor.close()
            self.conn.close()

        return {"affected_rows": affected_rows}

    def update_multiple_records_T(self, conn, attribute_names, records):
        sql = f"UPDATE {self.tablename} SET "
        for i, attribute in enumerate(attribute_names):
            if attribute != "id":
                if i < len(attribute_names) - 1:
                    sql += f"{attribute} = %s, "
                else:
                    sql += f"{attribute} = %s "

        sql = sql.rstrip(", ") + " WHERE id=%s"
        try:
            cursor = conn.cursor()
            # Execute the update statement with multiple values
            cursor.executemany(sql, records)
            # Commit the changes to the database
            conn.commit()
            # Get the number of affected rows
            affected_rows = cursor.rowcount
            print(f"{affected_rows} record(s) updated successfully.")

        except psycopg2.Error as error:
            # Rollback in case of an error
            conn.rollback()
            print(f"Error updating records: {error}")

        finally:
            # Close the cursor and the database connection
            cursor.close()

        return {"affected_rows": affected_rows}

    def create(self, objects):
        cursor = self.conn.cursor()

        sql = f"INSERT INTO {self.tablename}("
        sql_param = "VALUES("
        params = ()

        for i, (field_name, field_value) in enumerate(objects.items()):
           # 
            if isinstance(field_value, dict):
                field_value = [json.dumps(field_value)]
            # Handle lists by converting them to JSON strings
            elif isinstance(field_value, list):
                field_value = [json.dumps(field_value)]
            
            print(field_value)

            params += (field_value,)
            sql += f"{field_name},\n"
            sql_param += "%s,"

        sql = sql.rstrip(",\n") + ")\n"
        sql_param = sql_param.rstrip(",") + ")\n"
        sql += sql_param

       

        try:
            cursor.execute(sql, params)
            self.conn.commit()
            # In PostgreSQL, we use RETURNING to get the last inserted ID
            #cursor.execute(f"SELECT currval(pg_get_serial_sequence('{self.tablename}', 'id'))")
            cursor.execute (f"SELECT COALESCE(MAX(id), 0) FROM {self.tablename}")
            last_id = cursor.fetchone()[0]
            return {"Flag": True, "Id": last_id}
        except psycopg2.Error as e:
            # Handle the exception
            error_message = str(e)
            print(f"Error executing query: {error_message}")
            return {"Flag": False, "err": error_message}
        finally:
            cursor.close()

    def create_single_record(self, objects):
        cursor = self.conn.cursor()

        sql = f"INSERT INTO {self.tablename}("
        sql_param = "VALUES("
        params = ()

        for i, (field_name, field_value) in enumerate(objects.items()):
            if isinstance(field_value, dict):
                field_value = [json.dumps(field_value)]
            # Handle lists by converting them to JSON strings
            elif isinstance(field_value, list):
                field_value = [json.dumps(field_value)]
            params += (field_value,)
            sql += f"{field_name},\n"
            sql_param += "%s,"

        sql = sql.rstrip(",\n") + ")\n"
        sql_param = sql_param.rstrip(",") + ")\n"
        sql += sql_param

        try:
            cursor.execute(sql, params)
            self.conn.commit()
            # Get the last inserted ID using RETURNING
            cursor.execute(f"SELECT currval(pg_get_serial_sequence('{self.tablename}', 'id'))")
            last_id = cursor.fetchone()[0]
            
            return {"Flag": True, "Id": last_id}
        except psycopg2.Error as e:
            # Handle the exception
            error_message = str(e)
            print(f"Error executing query: {error_message}")
            return {"Flag": False, "err": error_message}
        finally:
            cursor.close()

    def update_single_record(self, record):
        cursor = self.conn.cursor()

        try:
            # Extract the id and the fields to update
            record_id = record.pop("id")
            update_parts = []
            params = []

            # Build the SQL SET clause and parameters list
            for field_name, field_value in record.items():
                update_parts.append(f"{field_name} = %s")
                if isinstance(field_value, dict):
                    field_value = [json.dumps(field_value)]
                    # Handle lists by converting them to JSON strings
                elif isinstance(field_value, list):
                    field_value = [json.dumps(field_value)]
                
                params.append(field_value)

            sql = f"UPDATE {self.tablename} SET "
            sql += ", ".join(update_parts)
            sql += " WHERE id = %s"
            params.append(record_id)

            # Execute the update for the single record
            cursor.execute(sql, tuple(params))
            self.conn.commit()

            return {"Flag": True, "id": record_id}
        except psycopg2.Error as e:
            error_message = str(e)
            print(f"Error executing update for record ID {record_id}: {error_message}")
            return {"Flag": False, "id": record_id, "err": error_message}
        finally:
            cursor.close()

    def update(self, objects, id):
        cursor = self.conn.cursor()

        sql = f"UPDATE {self.tablename} SET "
        params = ()
        update_parts = []

        for field_name, field_value in objects.items():
            update_parts.append(f"{field_name} = %s")
            if isinstance(field_value, dict):
                field_value = [json.dumps(field_value)]
            # Handle lists by converting them to JSON strings
            elif isinstance(field_value, list):
                field_value = [json.dumps(field_value)]
            params += (field_value,)

        sql += ", ".join(update_parts)

        sql += " WHERE id=%s"
        params += (int(id),)

        try:
            cursor.execute(sql, params)
            self.conn.commit()
            # Fetch the updated result
            sql = f"SELECT id FROM {self.tablename} WHERE id = %s"
            params = (int(id),)
            cursor.execute(sql, params)
            update_result = cursor.fetchall()
            cursor.close()
            return {"Flag": True, "Id": id}
        except psycopg2.Error as e:
            # Handle the exception
            error_message = str(e)
            print(f"Error executing query: {error_message}")
            return {"Flag": False, "err": error_message}
        finally:
            cursor.close()

    def delete_all(self):
        cursor = self.conn.cursor()
        sql = f"DELETE FROM {self.tablename}"
        cursor.execute(sql)
        cursor.close()
        self.conn.commit()
        return {"Flag": True}

    def delete(self, id):
        cursor = self.conn.cursor()
        sql = f"DELETE FROM {self.tablename} WHERE id=%s"
        params = (int(id),)
        cursor.execute(sql, params)
        cursor.close()
        self.conn.commit()
        return {"Flag": True}

    def set_elements(self, element, id):
        cursor = self.conn.cursor()
        sql = f"UPDATE {self.tablename} SET "
        params = ()
        update_parts = []

        for field_name, field_value in element.items():
            update_parts.append(f"{field_name} = %s")
            if isinstance(field_value, dict):
                field_value = [json.dumps(field_value)]
            # Handle lists by converting them to JSON strings
            elif isinstance(field_value, list):
                field_value = [json.dumps(field_value)]

        sql += ", ".join(update_parts)
        sql += " WHERE id=%s"
        params += (int(id),)

        cursor.execute(sql, params)
        self.conn.commit()
        row_update = cursor.rowcount
        Flag = True if row_update > 0 else False
        json_obj = {"Flag": Flag}
        return json_obj

    def get_data(self, fields, id):
        cursor = self.conn.cursor()
        sql = f"SELECT {', '.join(fields)} FROM {self.tablename} WHERE id = %s"
        params = (int(id),)
        cursor.execute(sql, params)
        result = cursor.fetchall()
        json_result = [
            {field: value for field, value in zip(fields, row)}
            for row in result
        ]
        if len(json_result) > 0:
            result = json_result[0]
            result["Flag_found"] = True
            return result
        else:
            return {"Flag_found": False}

    def get_specific_sql(self, sql, fields=None, params=None):
        try:
            cursor = self.conn.cursor()
            if params is not None:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            
            if fields is None:
                fields = [column[0] for column in cursor.description]
                
            if len(results) > 0:
                if results[0][0] is not None:
                    json_result = [
                        {field: value for field, value in zip(fields, row)}
                        for row in results
                    ]
                    return json_result
                else:
                    return []
            else:
                return []

        except Exception as e:
            print(f"Error occurred: {e}")
            raise
        finally:
            cursor.close()

    def get_max_id(self):
        cursor = self.conn.cursor()
        sql = f"SELECT MAX(id) FROM {self.tablename}"
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            if results[0][0] is not None:
                return {"max_id": results[0][0]}
            else:
                return {"max_id": 0}
                
        except psycopg2.Error as e:
            return {"max_id": 0}

    def set_specific_sql(self, sql, params):
        cursor = self.conn.cursor()
        cursor.execute(sql, params)

        self.conn.commit()
        row_update = cursor.rowcount
        Flag = True if row_update > 0 else False
        cursor.close()

        result = {"Flag": Flag}
        return result