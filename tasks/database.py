import mariadb
import sys

# Connect to MariaDB
def connect_db():
    try:
        conn = mariadb.connect(
            user="casaos",
            password="casaos",
            host="192.168.1.102",
            port=3307,
            database="FoxBot"
        )
        return conn
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        sys.exit(1)

# Get server settings from the database
def get_guild_settings(guild_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT e621_safe_mode, broadcast_enabled FROM settings WHERE guild_id=?", (guild_id,))
    result = cursor.fetchone()
    if result:
        return {"e621_safe_mode": result[0], "broadcast_enabled": result[1]}
    else:
        return {"e621_safe_mode": False, "broadcast_enabled": True}

# Save server settings to the database
def save_guild_settings(guild_id, settings):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "REPLACE INTO settings (guild_id, e621_safe_mode, broadcast_enabled) VALUES (?, ?, ?)",
        (guild_id, settings['e621_safe_mode'], settings['broadcast_enabled'])
    )
    conn.commit()
    conn.close()
