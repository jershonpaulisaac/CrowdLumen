import sqlite3
import os
from datetime import datetime
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = 'database.db'

# --- MVMS GLOBAL (In-Memory State) ---
# Each venue: {name, limit, count, occupants: set(uids)}
VENUES = {
    1: {"name": "Main Hall", "limit": 50, "count": 0, "occupants": set()},
    2: {"name": "Conf Room", "limit": 30, "count": 0, "occupants": set()},
    3: {"name": "Cafeteria", "limit": 100, "count": 0, "occupants": set()},
    4: {"name": "VIP Lounge", "limit": 20, "count": 0, "occupants": set()},
}
CURRENT_VENUE_ID = 1
TAP_LOGS = [] # Stores last 50 events: {name, uid, venue, type, time}
EVAC_ALARM_ACTIVE = False
OVER_CAPACITY_SILENCED = {} # {venue_id: bool} - Store if user silenced the warning

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (name TEXT, uid TEXT UNIQUE)')
        db.commit()

# --- API: TAP LOGIC (ANY TAG ACCEPTED) ---
@app.route('/api/tap', methods=['POST'])
def tap():
    data = request.get_json()
    uid = data.get('uid')
    ttype = data.get('type')
    
    if not uid:
        return jsonify({"status": "error", "msg": "No UID"}), 400
    
    # 1. Resolve Name (Optional - just for display)
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name FROM users WHERE uid = ?', (uid,))
    res = cursor.fetchone()
    name = res['name'] if res else f"Guest [{uid}]"

    # 2. Logic on CURRENT VENUE
    v = VENUES[CURRENT_VENUE_ID]
    
    event = {
        "name": name,
        "uid": uid,
        "venue": v['name'],
        "time": datetime.now().strftime("%H:%M:%S")
    }

    if ttype == 'entry':
        # Removed hard capacity limit restriction
        if uid not in v['occupants']:
            v['count'] += 1
            v['occupants'].add(uid)
            event["type"] = "entry"
            TAP_LOGS.insert(0, event)
            if len(TAP_LOGS) > 50: TAP_LOGS.pop()
            
            # If we just crossed the limit, reset the silence flag for this venue
            if v['count'] > v['limit']:
                OVER_CAPACITY_SILENCED[CURRENT_VENUE_ID] = False
                
            return jsonify({"status": "allowed", "msg": f"Welcome {name}"})
        return jsonify({"status": "allowed", "msg": "Already In"})
        
    elif ttype == 'exit':
        if uid in v['occupants']:
            v['count'] -= 1
            v['occupants'].remove(uid)
            event["type"] = "exit"
            TAP_LOGS.insert(0, event)
            if len(TAP_LOGS) > 50: TAP_LOGS.pop()
            return jsonify({"status": "allowed", "msg": f"Goodbye {name}"})
        return jsonify({"status": "denied", "msg": "Not Inside"})

    return jsonify({"status": "error"}), 400

# --- API: STATUS ---
@app.route('/api/status', methods=['GET'])
def status():
    all_venues = []
    for vid, vdata in VENUES.items():
        all_venues.append({
            "id": vid,
            "name": vdata['name'],
            "limit": vdata['limit'],
            "count": vdata['count']
        })
        
    curr = VENUES[CURRENT_VENUE_ID]
    is_over = curr['count'] > curr['limit']
    is_silenced = OVER_CAPACITY_SILENCED.get(CURRENT_VENUE_ID, False)

    occupant_list = []
    db = get_db()
    cur = db.cursor()
    for uid in curr['occupants']:
        cur.execute('SELECT name FROM users WHERE uid = ?', (uid,))
        r = cur.fetchone()
        n = r['name'] if r else f"Guest {uid}"
        occupant_list.append({"name": n, "uid": uid})
    
    return jsonify({
        "current_id": CURRENT_VENUE_ID,
        "current_name": curr['name'],
        "current_limit": curr['limit'],
        "current_count": curr['count'],
        "occupants": occupant_list,
        "venues": all_venues,
        "logs": TAP_LOGS,
        "over_capacity_alarm": is_over and not is_silenced
    })

# --- API: CONTROL ---
@app.route('/api/set_venue', methods=['POST'])
def set_venue():
    global CURRENT_VENUE_ID
    CURRENT_VENUE_ID = int(request.json.get('id'))
    return jsonify({"status": "ok"})

@app.route('/api/update_venue', methods=['POST'])
def update_venue():
    # Rename or Change Limit
    data = request.get_json()
    vid = int(data.get('id'))
    if vid in VENUES:
        if 'name' in data: VENUES[vid]['name'] = data['name']
        if 'limit' in data: VENUES[vid]['limit'] = int(data['limit'])
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/api/reset_venue', methods=['POST'])
def reset_venue():
    data = request.get_json()
    vid = int(data.get('id'))
    if vid in VENUES:
        VENUES[vid]['count'] = 0
        VENUES[vid]['occupants'] = set()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

# --- API: EVACUATION ALARM ---
@app.route('/api/evac_status', methods=['GET'])
def evac_status():
    return jsonify({"active": EVAC_ALARM_ACTIVE})

@app.route('/api/evac_trigger', methods=['POST'])
def evac_trigger():
    global EVAC_ALARM_ACTIVE
    EVAC_ALARM_ACTIVE = True
    return jsonify({"status": "ok"})

@app.route('/api/evac_stop', methods=['POST'])
def evac_stop():
    global EVAC_ALARM_ACTIVE
    EVAC_ALARM_ACTIVE = False
    return jsonify({"status": "ok"})

@app.route('/api/silence_over_capacity', methods=['POST'])
def silence_over_capacity():
    data = request.get_json()
    vid = int(data.get('id', CURRENT_VENUE_ID))
    OVER_CAPACITY_SILENCED[vid] = True
    return jsonify({"status": "ok"})

@app.route('/api/hw_status', methods=['GET'])
def hw_status():
    # Polling endpoint for hardware to check both alarms
    curr = VENUES[CURRENT_VENUE_ID]
    over_alarm = (curr['count'] > curr['limit']) and not OVER_CAPACITY_SILENCED.get(CURRENT_VENUE_ID, False)
    return jsonify({
        "evac": EVAC_ALARM_ACTIVE,
        "over_cap": over_alarm
    })

@app.route('/api/evacuation/full_summary', methods=['GET'])
def evac_full_summary():
    db = get_db()
    cursor = db.cursor()
    
    venue_data = []
    total_inside = 0
    all_occupants = []
    
    # 1. Gather per-venue stats
    for vid, v in VENUES.items():
        v_occupants = []
        for uid in v['occupants']:
            cursor.execute('SELECT name FROM users WHERE uid = ?', (uid,))
            row = cursor.fetchone()
            name = row['name'] if row else f"Guest {uid}"
            v_occupants.append({"name": name, "uid": uid, "venue": v['name']})
            all_occupants.append({"name": name, "uid": uid, "venue": v['name']})
            
        venue_data.append({
            "name": v['name'],
            "count": v['count'],
            "occupants": v_occupants
        })
        total_inside += v['count']

    # 2. Gather "Safe" (Muster Point) - Everyone in DB not in any venue
    # First, get all UIDs currently inside
    inside_uids = set()
    for v in VENUES.values():
        inside_uids.update(v['occupants'])
        
    cursor.execute('SELECT name, uid FROM users')
    all_users = cursor.fetchall()
    safe_list = []
    for u in all_users:
        if u['uid'] not in inside_uids:
            safe_list.append({"name": u['name'], "uid": u['uid']})

    return jsonify({
        "venues": venue_data,
        "total_inside": total_inside,
        "total_safe": len(safe_list),
        "inside_list": all_occupants,
        "safe_list": safe_list
    })

@app.route('/')
def index():
    return send_from_directory(os.path.abspath('../frontend'), 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.abspath('../frontend'), filename)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
