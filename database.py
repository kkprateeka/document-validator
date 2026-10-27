import pyodbc

def get_connection():
    return pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=DocumentValidation;"
    "Trusted_Connection=yes;"
)

def get_user_role(emp_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT role FROM users WHERE emp_id = ?",
            emp_id
        )

        row = cursor.fetchone()

        if row and row[0]:
            return row[0]

        return None

    except Exception as e:
        print("DB ERROR:", e)
        return None

    finally:
        if conn:
            conn.close()
    
def get_default_word():
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT default_word_path FROM app_config WHERE id = 1")
        row = cursor.fetchone()

        if row and row[0]:
            print("📦 DB DEFAULT WORD PATH:", row[0])
            return row[0]

        print("❌ DEFAULT WORD PATH EMPTY OR NULL")
        return None

    except Exception as e:
        print("DB ERROR:", e)
        return None

    finally:
        if conn:
            conn.close()

def set_default_word(path):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE app_config SET default_word_path = ? WHERE id = 1",
            (path,)
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO app_config (id, default_word_path) VALUES (1, ?)",
                path
                )
        conn.commit()

        return True

    except Exception as e:
        print("DB ERROR:", e)
        return False

    finally:
        if conn:
            conn.close()