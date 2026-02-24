from flask import Blueprint, jsonify, send_from_directory, g
import sqlite3
import os
import time

# Create Blueprint
evac_bp = Blueprint('evacuation', __name__)

DATABASE = 'database.db'

def get_evac_db():
    db = getattr(g, '_database_evac', None)
    if db is None:
        db = g._database_evac = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@evac_bp.route('/evacuation_dashboard')
def evac_dashboard():
    # Serve the specific HTML file for evacuation
    return send_from_directory(os.path.abspath('../frontend'), 'evacuation.html')

@evac_bp.route('/api/evacuation/summary')
def evac_summary():
    db = get_evac_db()
    cursor = db.cursor()
    
    # Get all users
    cursor.execute('SELECT name, uid, status, entry_time FROM users')
    users = cursor.fetchall()
    
    inside_list = []
    outside_list = []
    
    for u in users:
        if u['name'] == 'MASTER KEY':
            continue

        user_data = {
            "name": u['name'],
            "uid": u['uid'],
            "status": u['status']
        }
        if u['status'] == 'INSIDE':
            inside_list.append(user_data)
        else:
            outside_list.append(user_data)
            
    return jsonify({
        "timestamp": int(time.time()),
        "total_inside": len(inside_list),
        "total_outside": len(outside_list),
        "inside": inside_list,
        "outside": outside_list
    })
