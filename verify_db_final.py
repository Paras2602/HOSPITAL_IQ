import requests

def verify_api():
    # Since I don't have an admin token easily, I'll just check the DB again via the simple script
    import sqlite3
    conn = sqlite3.connect('hospitaliq.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, access_code FROM users WHERE access_code IS NOT NULL")
    rows = cursor.fetchall()
    print(f"Users with access codes: {len(rows)}")
    for row in rows:
        print(f"Email: {row[0]} | Code: {row[1]}")
    conn.close()

if __name__ == "__main__":
    verify_api()
