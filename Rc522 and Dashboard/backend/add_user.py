import sqlite3
import sys

DATABASE = 'database.db'

def add_user(name, uid, daily_limit=3600):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (name, uid, daily_limit) VALUES (?, ?, ?)', (name, uid, daily_limit))
        conn.commit()
        print(f"Successfully added user: {name} ({uid})")
    except sqlite3.IntegrityError:
        print(f"Error: UID {uid} already exists!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_user.py \"Name\" \"UID\" [DailyLimitSeconds]")
        print("Example: python add_user.py \"John Doe\" \"A1B2C3D4\"")
    else:
        name = sys.argv[1]
        uid = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3600
        add_user(name, uid, limit)
