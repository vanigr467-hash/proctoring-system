#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   🩸 BloodBridge AI — Emergency Blood Donor Matching System      ║
║   Full-Stack Application in a Single Python File                 ║
╠══════════════════════════════════════════════════════════════════╣
║  INSTALL:  pip install flask flask-socketio flask-cors           ║
║            flask-jwt-extended bcrypt                             ║
║  RUN:      python bloodbridge_ai.py                              ║
║  OPEN:     http://localhost:5000                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  DEMO LOGINS:                                                    ║
║    Admin:    admin@bloodbridge.org  / admin123                   ║
║    Donor 1:  alice@donor.com        / pass123   (O+)             ║
║    Donor 2:  bob@donor.com          / pass123   (A+)             ║
║    Donor 3:  carol@donor.com        / pass123   (B-)             ║
║    Donor 4:  david@donor.com        / pass123   (O-)             ║
║    Donor 5:  emma@donor.com         / pass123   (AB+)            ║
║    Hospital: hospital@citygeneral.com / hosp123                  ║
║    Patient:  patient@example.com    / patient123                 ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────────────
# IMPORTS & SETUP
# ─────────────────────────────────────────────────────────────────
import os, sys, math, uuid, json, threading, time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity, get_jwt
)
try:
    import bcrypt
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "bcrypt", "-q"])
    import bcrypt

# ─────────────────────────────────────────────────────────────────
# APP CONFIGURATION
# ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bloodbridge-ultra-secure-2024-xK9$mP2#')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-bb-secret-9mN$kL3@qR7')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

CORS(app, origins="*", supports_credentials=True)
jwt = JWTManager(app)

# Comprehensive WebSocket fix
@app.before_request
def before_request():
    # Handle WebSocket upgrade requests properly
    if request.path.startswith('/socket.io/'):
        # Let Socket.IO handle WebSocket requests completely
        return None

# Configure Socket.IO with robust settings
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    logger=False,  # Disable to reduce log spam
    engineio_logger=False,
    ping_timeout=60,  # Increased timeout
    ping_interval=25,  # Increased interval
    always_connect=True,
    transports=['websocket', 'polling'],
    socketio_path='socket.io',
    allow_upgrades=True,
    http_compression=False
)

# ─────────────────────────────────────────────────────────────────
# BLOOD COMPATIBILITY MATRIX
# ─────────────────────────────────────────────────────────────────
BLOOD_COMPATIBILITY = {
    'O-':  ['O-','O+','A-','A+','B-','B+','AB-','AB+'],
    'O+':  ['O+','A+','B+','AB+'],
    'A-':  ['A-','A+','AB-','AB+'],
    'A+':  ['A+','AB+'],
    'B-':  ['B-','B+','AB-','AB+'],
    'B+':  ['B+','AB+'],
    'AB-': ['AB-','AB+'],
    'AB+': ['AB+'],
}

URGENCY_LEVELS = ['low', 'medium', 'high', 'critical']
ROLES = ['donor', 'patient', 'hospital', 'admin']

# ─────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────
def _now(offset_days=0):
    dt = datetime.utcnow() + timedelta(days=offset_days)
    return dt.isoformat()

def _haversine(lat1, lng1, lat2, lng2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _match_donors(blood_group, lat, lng, urgency, donors_list, max_radius=50):
    compatible = [bg for bg, targets in BLOOD_COMPATIBILITY.items() if blood_group in targets]
    urgency_mult = {'critical': 1.5, 'high': 1.2, 'medium': 1.0, 'low': 0.8}.get(urgency, 1.0)
    matched = []
    for d in donors_list:
        if d['blood_group'] not in compatible: continue
        if not d.get('availability', False): continue
        dist = _haversine(lat, lng, d['lat'], d['lng'])
        if dist > max_radius: continue
        dist_score  = max(0, 100 - (dist / max_radius) * 70)
        don_score   = min(20, d.get('total_donations', 0) * 2)
        avail_score = 25
        last = d.get('last_donation')
        if last:
            try:
                days = (datetime.utcnow() - datetime.fromisoformat(last)).days
                rec_score = min(15, days // 8)
            except: rec_score = 8
        else: rec_score = 15
        score = min(100, (dist_score + don_score + avail_score + rec_score) * urgency_mult)
        matched.append({**d, 'distance_km': round(dist, 2), 'match_score': round(score, 1)})
    matched.sort(key=lambda x: x['match_score'], reverse=True)
    return matched

# ─────────────────────────────────────────────────────────────────
# IN-MEMORY DATABASE  (MongoDB Collections Equivalent)
# ─────────────────────────────────────────────────────────────────
class DB:
    def __init__(self):
        self.users          = []
        self.donors         = []
        self.blood_requests = []
        self.notifications  = []
        self.logs           = []
        self._seed()

    # ── Helpers ──────────────────────────────────────────────────
    def find_user(self, uid):
        return next((u for u in self.users if u['id'] == uid), None)

    def find_user_by_email(self, email):
        return next((u for u in self.users if u['email'] == email), None)

    def find_donor_by_user(self, uid):
        return next((d for d in self.donors if d['user_id'] == uid), None)

    def find_request(self, rid):
        return next((r for r in self.blood_requests if r['id'] == rid), None)

    # ── Seed ─────────────────────────────────────────────────────
    def _seed(self):
        def H(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

        # Admin
        self.users.append({
            'id': 'admin-001', 'name': 'System Admin',
            'email': 'admin@bloodbridge.org', 'password': H('admin123'),
            'role': 'admin', 'phone': '+1-800-BLOOD-AI', 'is_active': True,
            'created_at': _now()
        })

        # Donors
        donors_seed = [
            ('Alice Johnson',  'alice@donor.com',  'O+',  12.9716, 77.5946, True,  8,  120),
            ('Bob Smith',      'bob@donor.com',    'A+',  12.9352, 77.6245, True,  3,  60),
            ('Carol Davis',    'carol@donor.com',  'B-',  12.9800, 77.5900, False, 12, 200),
            ('David Lee',      'david@donor.com',  'O-',  12.9600, 77.6100, True,  5,  90),
            ('Emma Wilson',    'emma@donor.com',   'AB+', 12.9900, 77.5800, True,  2,  45),
            ('Raj Patel',      'raj@donor.com',    'B+',  12.9450, 77.6350, True,  6,  150),
        ]
        for i, (name, email, bg, lat, lng, avail, dons, days_ago) in enumerate(donors_seed):
            uid = f'donor-{i+1:03d}'
            self.users.append({
                'id': uid, 'name': name, 'email': email,
                'password': H('pass123'), 'role': 'donor',
                'phone': f'+919{i+1}0{i*3:07d}', 'is_active': True,
                'created_at': _now()
            })
            self.donors.append({
                'id': f'dnr-{i+1:03d}', 'user_id': uid,
                'blood_group': bg, 'availability': avail,
                'lat': lat, 'lng': lng,
                'last_donation': _now(-days_ago),
                'total_donations': dons,
                'name': name, 'email': email,
                'phone': f'+919{i+1}0{i*3:07d}',
                'accepted_requests': [], 'rejected_requests': []
            })

        # Hospital
        self.users.append({
            'id': 'hosp-001', 'name': 'City General Hospital',
            'email': 'hospital@citygeneral.com', 'password': H('hosp123'),
            'role': 'hospital', 'phone': '+91-80-2345-6789', 'is_active': True,
            'created_at': _now()
        })

        # Patient
        self.users.append({
            'id': 'pat-001', 'name': 'John Patient',
            'email': 'patient@example.com', 'password': H('patient123'),
            'role': 'patient', 'phone': '+91-99876-54321', 'is_active': True,
            'created_at': _now()
        })

        # Sample blood request
        self.blood_requests.append({
            'id': 'req-demo-001',
            'requester_id': 'hosp-001',
            'requester_name': 'City General Hospital',
            'blood_group': 'O+',
            'units': 2,
            'urgency': 'critical',
            'hospital_name': 'City General Hospital',
            'lat': 12.9716, 'lng': 77.5946,
            'description': 'Emergency surgery patient requires O+ blood immediately.',
            'status': 'pending',
            'matched_donors': [],
            'accepted_donors': [],
            'created_at': _now(-1),
            'updated_at': _now(-1)
        })
        # Run initial match for demo request
        matched = _match_donors('O+', 12.9716, 77.5946, 'critical', self.donors)
        self.blood_requests[0]['matched_donors'] = matched[:8]

db = DB()

# ─────────────────────────────────────────────────────────────────
# ADDITIONAL UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────
def _create_notif(user_id, ntype, title, message, data=None):
    n = {
        'id': str(uuid.uuid4()), 'user_id': user_id, 'type': ntype,
        'title': title, 'message': message, 'data': data or {},
        'read': False, 'created_at': _now()
    }
    db.notifications.append(n)
    return n

def _log(action, user_id=None, details=None):
    db.logs.append({
        'id': str(uuid.uuid4()), 'action': action,
        'user_id': user_id, 'details': details, 'timestamp': _now()
    })

def _safe_user(u):
    return {k: v for k, v in u.items() if k != 'password'}

def _role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            role = get_jwt().get('role')
            if role not in roles:
                return jsonify({'error': f'Access denied. Required: {", ".join(roles)}'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# ─────────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.json or {}
    for f in ['name', 'email', 'password', 'role']:
        if not d.get(f):
            return jsonify({'error': f'Field "{f}" is required'}), 400
    if d['role'] not in ['donor', 'patient', 'hospital']:
        return jsonify({'error': 'Role must be donor, patient, or hospital'}), 400
    if db.find_user_by_email(d['email']):
        return jsonify({'error': 'Email already registered'}), 409

    uid = str(uuid.uuid4())
    user = {
        'id': uid, 'name': d['name'], 'email': d['email'],
        'password': bcrypt.hashpw(d['password'].encode(), bcrypt.gensalt()).decode(),
        'role': d['role'], 'phone': d.get('phone', ''), 'is_active': True,
        'created_at': _now()
    }
    db.users.append(user)

    if d['role'] == 'donor':
        db.donors.append({
            'id': str(uuid.uuid4()), 'user_id': uid,
            'blood_group': d.get('blood_group', 'O+'),
            'availability': True,
            'lat': float(d.get('lat', 12.9716)),
            'lng': float(d.get('lng', 77.5946)),
            'last_donation': None, 'total_donations': 0,
            'name': d['name'], 'email': d['email'], 'phone': d.get('phone', ''),
            'accepted_requests': [], 'rejected_requests': []
        })
    _log('register', uid, {'role': d['role']})
    token = create_access_token(identity=uid, additional_claims={'role': d['role'], 'name': d['name']})
    return jsonify({'token': token, 'user': _safe_user(user)}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.json or {}
    if not d.get('email') or not d.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    user = db.find_user_by_email(d['email'])
    if not user or not bcrypt.checkpw(d['password'].encode(), user['password'].encode()):
        return jsonify({'error': 'Invalid email or password'}), 401
    if not user['is_active']:
        return jsonify({'error': 'Account is deactivated. Contact admin.'}), 403
    _log('login', user['id'])
    token = create_access_token(identity=user['id'], additional_claims={'role': user['role'], 'name': user['name']})
    return jsonify({'token': token, 'user': _safe_user(user)}), 200

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    uid = get_jwt_identity()
    user = db.find_user(uid)
    if not user: return jsonify({'error': 'Not found'}), 404
    result = _safe_user(user)
    if user['role'] == 'donor':
        donor = db.find_donor_by_user(uid)
        if donor: result['donor_profile'] = donor
    return jsonify(result), 200

# ─────────────────────────────────────────────────────────────────
# DONOR ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route('/api/donors', methods=['GET'])
@jwt_required()
def get_donors():
    bg   = request.args.get('blood_group')
    avail = request.args.get('available') == 'true'
    donors = db.donors
    if bg:    donors = [d for d in donors if d['blood_group'] == bg]
    if avail: donors = [d for d in donors if d.get('availability')]
    return jsonify(donors), 200

@app.route('/api/donors/profile', methods=['GET'])
@jwt_required()
def get_donor_profile():
    uid = get_jwt_identity()
    donor = db.find_donor_by_user(uid)
    if not donor: return jsonify({'error': 'Donor profile not found'}), 404
    return jsonify(donor), 200

@app.route('/api/donors/profile', methods=['PUT'])
@jwt_required()
def update_donor_profile():
    uid = get_jwt_identity()
    donor = db.find_donor_by_user(uid)
    if not donor: return jsonify({'error': 'Donor profile not found'}), 404
    d = request.json or {}
    for k in ['blood_group', 'availability', 'lat', 'lng', 'last_donation', 'phone']:
        if k in d: donor[k] = d[k]
    if 'name' in d:
        donor['name'] = d['name']
        u = db.find_user(uid)
        if u: u['name'] = d['name']
    _log('update_donor_profile', uid)
    return jsonify(donor), 200

@app.route('/api/donors/availability', methods=['PATCH'])
@jwt_required()
def toggle_availability():
    uid = get_jwt_identity()
    donor = db.find_donor_by_user(uid)
    if not donor: return jsonify({'error': 'Donor not found'}), 404
    d = request.json or {}
    donor['availability'] = d.get('availability', not donor['availability'])
    socketio.emit('donor_status_changed', {
        'donor_id': donor['id'], 'availability': donor['availability'], 'name': donor['name']
    })
    return jsonify({'availability': donor['availability']}), 200

@app.route('/api/donors/location', methods=['PATCH'])
@jwt_required()
def update_location():
    uid = get_jwt_identity()
    donor = db.find_donor_by_user(uid)
    if not donor: return jsonify({'error': 'Donor not found'}), 404
    d = request.json or {}
    if 'lat' not in d or 'lng' not in d:
        return jsonify({'error': 'lat and lng required'}), 400
    donor['lat'], donor['lng'] = float(d['lat']), float(d['lng'])
    return jsonify({'lat': donor['lat'], 'lng': donor['lng']}), 200

# ─────────────────────────────────────────────────────────────────
# BLOOD REQUEST ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route('/api/requests', methods=['GET'])
@jwt_required()
def get_requests():
    claims = get_jwt()
    uid    = get_jwt_identity()
    role   = claims.get('role')
    reqs   = db.blood_requests

    if role == 'donor':
        donor = db.find_donor_by_user(uid)
        if donor:
            reqs = [r for r in reqs if any(
                md.get('id') == donor['id'] for md in r.get('matched_donors', [])
            )]
        else: reqs = []
    elif role in ['hospital', 'patient']:
        reqs = [r for r in reqs if r.get('requester_id') == uid]

    status = request.args.get('status')
    if status: reqs = [r for r in reqs if r['status'] == status]
    reqs = sorted(reqs, key=lambda x: x['created_at'], reverse=True)
    return jsonify(reqs), 200

@app.route('/api/requests', methods=['POST'])
@jwt_required()
def create_request():
    claims = get_jwt()
    uid    = get_jwt_identity()
    role   = claims.get('role')
    if role not in ['hospital', 'patient', 'admin']:
        return jsonify({'error': 'Only hospitals and patients may create requests'}), 403
    d = request.json or {}
    for f in ['blood_group', 'units', 'urgency', 'hospital_name', 'lat', 'lng']:
        if f not in d: return jsonify({'error': f'Field "{f}" required'}), 400
    if d['urgency'] not in URGENCY_LEVELS:
        return jsonify({'error': f'urgency must be one of {URGENCY_LEVELS}'}), 400

    matched = _match_donors(d['blood_group'], float(d['lat']), float(d['lng']),
                             d['urgency'], db.donors)
    req = {
        'id': str(uuid.uuid4()),
        'requester_id': uid, 'requester_name': claims.get('name', 'Unknown'),
        'blood_group': d['blood_group'], 'units': int(d['units']),
        'urgency': d['urgency'], 'hospital_name': d['hospital_name'],
        'lat': float(d['lat']), 'lng': float(d['lng']),
        'description': d.get('description', ''),
        'status': 'pending',
        'matched_donors': matched[:10],
        'accepted_donors': [],
        'created_at': _now(), 'updated_at': _now()
    }
    db.blood_requests.append(req)
    _log('create_request', uid, {'bg': d['blood_group'], 'urgency': d['urgency']})

    # Notify each matched donor via socket
    for m in matched[:10]:
        notif = _create_notif(
            m['user_id'], 'emergency_request',
            f"🚨 {d['urgency'].upper()} — {d['blood_group']} Blood Needed",
            f"{d['hospital_name']} needs {d['blood_group']} blood. "
            f"You are {m['distance_km']} km away. Match score: {m['match_score']}.",
            {'request_id': req['id']}
        )
        socketio.emit('new_request', {
            'request': req, 'notification': notif,
            'match_score': m['match_score'], 'distance_km': m['distance_km']
        }, room=f"user_{m['user_id']}")

    socketio.emit('request_created', req, room='hospital_room')
    socketio.emit('request_created', req, room='admin_room')
    socketio.emit('request_created', req, room='patient_room')

    return jsonify(req), 201

@app.route('/api/requests/<rid>', methods=['GET'])
@jwt_required()
def get_request(rid):
    r = db.find_request(rid)
    if not r: return jsonify({'error': 'Request not found'}), 404
    return jsonify(r), 200

@app.route('/api/requests/<rid>/respond', methods=['POST'])
@jwt_required()
def respond_to_request(rid):
    uid = get_jwt_identity()
    if get_jwt().get('role') != 'donor':
        return jsonify({'error': 'Only donors can respond'}), 403
    req = db.find_request(rid)
    if not req: return jsonify({'error': 'Request not found'}), 404
    donor = db.find_donor_by_user(uid)
    if not donor: return jsonify({'error': 'Donor profile not found'}), 404

    d = request.json or {}
    action = d.get('action')
    if action not in ['accept', 'reject']:
        return jsonify({'error': 'action must be accept or reject'}), 400

    # Update matched donor response
    for md in req['matched_donors']:
        if md.get('user_id') == uid:
            md['response'] = action
            md['responded_at'] = _now()

    if action == 'accept':
        already = any(x['user_id'] == uid for x in req['accepted_donors'])
        if not already:
            req['accepted_donors'].append({
                'donor_id': donor['id'], 'user_id': uid,
                'name': donor['name'], 'blood_group': donor['blood_group'],
                'phone': donor.get('phone', ''), 'accepted_at': _now()
            })
        if len(req['accepted_donors']) >= req['units']:
            req['status'] = 'matched'
        req['updated_at'] = _now()

        notif = _create_notif(
            req['requester_id'], 'donor_accepted',
            '✅ Donor Accepted Your Request!',
            f"{donor['name']} (Blood: {donor['blood_group']}) accepted the blood request.",
            {'request_id': rid, 'donor_id': donor['id']}
        )
        payload = {
            'request_id': rid,
            'donor': {'name': donor['name'], 'blood_group': donor['blood_group'],
                      'phone': donor.get('phone', '')},
            'accepted_count': len(req['accepted_donors']),
            'units_needed': req['units'],
            'request_status': req['status'],
            'notification': notif
        }
        socketio.emit('donor_accepted', payload, room=f"user_{req['requester_id']}")
        socketio.emit('request_updated', req, room='admin_room')
        socketio.emit('request_updated', req, room='hospital_room')

        donor['accepted_requests'].append(rid)
    else:
        donor['rejected_requests'].append(rid)

    _log('donor_respond', uid, {'rid': rid, 'action': action})
    return jsonify({'status': 'ok', 'action': action, 'request': req}), 200

@app.route('/api/requests/<rid>/status', methods=['PATCH'])
@jwt_required()
def update_request_status(rid):
    uid = get_jwt_identity()
    claims = get_jwt()
    req = db.find_request(rid)
    if not req: return jsonify({'error': 'Request not found'}), 404
    if claims.get('role') != 'admin' and req['requester_id'] != uid:
        return jsonify({'error': 'Unauthorized'}), 403
    d = request.json or {}
    req['status'] = d.get('status', req['status'])
    req['updated_at'] = _now()
    socketio.emit('request_updated', req, room='admin_room')
    socketio.emit('request_updated', req, room='hospital_room')
    socketio.emit('request_updated', req, room=f"user_{req['requester_id']}")
    return jsonify(req), 200

# ─────────────────────────────────────────────────────────────────
# NOTIFICATION ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifs():
    uid = get_jwt_identity()
    notifs = sorted([n for n in db.notifications if n['user_id'] == uid],
                    key=lambda x: x['created_at'], reverse=True)
    return jsonify(notifs), 200

@app.route('/api/notifications/<nid>/read', methods=['PATCH'])
@jwt_required()
def mark_read(nid):
    uid = get_jwt_identity()
    n = next((x for x in db.notifications if x['id'] == nid and x['user_id'] == uid), None)
    if not n: return jsonify({'error': 'Not found'}), 404
    n['read'] = True
    return jsonify(n), 200

@app.route('/api/notifications/read-all', methods=['PATCH'])
@jwt_required()
def mark_all_read():
    uid = get_jwt_identity()
    for n in db.notifications:
        if n['user_id'] == uid: n['read'] = True
    return jsonify({'status': 'ok'}), 200

# ─────────────────────────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route('/api/admin/stats', methods=['GET'])
@_role_required('admin')
def admin_stats():
    reqs = db.blood_requests
    total_r, pending_r, matched_r, closed_r = len(reqs), 0, 0, 0
    for r in reqs:
        if r['status'] == 'pending': pending_r += 1
        elif r['status'] == 'matched': matched_r += 1
        elif r['status'] == 'closed': closed_r += 1
    bg_stats = {}
    for d in db.donors:
        bg_stats[d['blood_group']] = bg_stats.get(d['blood_group'], 0) + 1
    urg_stats = {}
    for r in reqs:
        urg_stats[r['urgency']] = urg_stats.get(r['urgency'], 0) + 1
    return jsonify({
        'users':           len(db.users),
        'donors':          len(db.donors),
        'available_donors': len([d for d in db.donors if d.get('availability')]),
        'total_requests':  total_r,
        'pending':         pending_r,
        'matched':         matched_r,
        'closed':          closed_r,
        'fulfillment_rate': round(matched_r / total_r * 100, 1) if total_r else 0,
        'blood_group_stats': bg_stats,
        'urgency_stats':     urg_stats,
        'recent_logs':       db.logs[-30:],
        'total_notifications': len(db.notifications),
    }), 200

@app.route('/api/admin/users', methods=['GET'])
@_role_required('admin')
def admin_users():
    return jsonify([_safe_user(u) for u in db.users]), 200

@app.route('/api/admin/users/<uid>/toggle', methods=['PATCH'])
@_role_required('admin')
def admin_toggle_user(uid):
    u = db.find_user(uid)
    if not u: return jsonify({'error': 'User not found'}), 404
    u['is_active'] = not u['is_active']
    _log('toggle_user', get_jwt_identity(), {'target': uid, 'is_active': u['is_active']})
    return jsonify({'is_active': u['is_active'], 'id': uid}), 200

@app.route('/api/admin/requests', methods=['GET'])
@_role_required('admin')
def admin_requests():
    status = request.args.get('status')
    reqs = db.blood_requests
    if status: reqs = [r for r in reqs if r['status'] == status]
    return jsonify(sorted(reqs, key=lambda x: x['created_at'], reverse=True)), 200

# ─────────────────────────────────────────────────────────────────
# MATCHING API
# ─────────────────────────────────────────────────────────────────
@app.route('/api/match', methods=['POST'])
@jwt_required()
def api_match():
    d = request.json or {}
    for f in ['blood_group', 'lat', 'lng']:
        if f not in d: return jsonify({'error': f'Field {f} required'}), 400
    matched = _match_donors(d['blood_group'], float(d['lat']), float(d['lng']),
                             d.get('urgency', 'medium'), db.donors,
                             float(d.get('max_radius', 50)))
    return jsonify({'matched': matched, 'count': len(matched)}), 200

# ─────────────────────────────────────────────────────────────────
# SOCKET.IO EVENTS
# ─────────────────────────────────────────────────────────────────
@socketio.on('connect')
def on_connect(auth=None):
    emit('connected', {'msg': 'Connected to BloodBridge real-time server 🩸'})

@socketio.on('disconnect')
def on_disconnect():
    pass

@socketio.on('join')
def on_join(data):
    room = data.get('room')
    if room:
        join_room(room)
        emit('joined', {'room': room})

@socketio.on('join_role_room')
def on_join_role(data):
    role = data.get('role')
    if role in ['hospital', 'admin', 'patient']:
        join_room(f"{role}_room")
        emit('joined', {'room': f"{role}_room"})

@socketio.on('leave')
def on_leave(data):
    room = data.get('room')
    if room: leave_room(room)

@socketio.on('send_message')
def on_message(data):
    # Broadcast chat/announcement to all
    emit('message', data, broadcast=True)

# ─────────────────────────────────────────────────────────────────
# FRONTEND — Complete React SPA (served from '/')
# ─────────────────────────────────────────────────────────────────
FRONTEND = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BloodBridge AI — Emergency Donor System</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.2/babel.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.6.1/socket.io.min.js"></script>
<style>
:root {
  --red:      #E53935;
  --red-d:    #B71C1C;
  --red-l:    #FF6B6B;
  --red-glow: rgba(229,57,53,0.25);
  --bg:       #080810;
  --s1:       #0F0F1A;
  --s2:       #16162A;
  --s3:       #1E1E34;
  --s4:       #252540;
  --border:   rgba(229,57,53,0.12);
  --border2:  rgba(255,255,255,0.06);
  --text:     #F0F0F8;
  --muted:    #6A6A8A;
  --dim:      #3A3A55;
  --green:    #2ECC71;
  --yellow:   #F1C40F;
  --blue:     #4A90D9;
  --orange:   #E67E22;
  --font-d:   'Bebas Neue', sans-serif;
  --font-b:   'DM Sans', sans-serif;
  --font-m:   'DM Mono', monospace;
  --r-sm:     8px;
  --r-md:     12px;
  --r-lg:     18px;
  --r-xl:     24px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:var(--font-b);min-height:100vh;overflow-x:hidden;}
#root{min-height:100vh;}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:var(--s1);}
::-webkit-scrollbar-thumb{background:var(--s4);border-radius:3px;}

/* ── ANIMATIONS ── */
@keyframes pulse-ring{0%{transform:scale(.9);opacity:1}70%{transform:scale(1.6);opacity:0}100%{transform:scale(1.6);opacity:0}}
@keyframes heartbeat{0%,100%{transform:scale(1)}14%{transform:scale(1.15)}28%{transform:scale(1)}42%{transform:scale(1.08)}70%{transform:scale(1)}}
@keyframes fadeUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes slideLeft{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
@keyframes slideRight{from{opacity:0;transform:translateX(-40px)}to{opacity:1;transform:translateX(0)}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes flash-border{0%,100%{border-color:var(--red)}50%{border-color:transparent}}
@keyframes gradientMove{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
@keyframes drip{0%{height:0;opacity:1}100%{height:60px;opacity:0}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}

/* ── UTILITY ── */
.anim-fade{animation:fadeIn .5s ease both;}
.anim-up{animation:fadeUp .6s ease both;}
.anim-left{animation:slideLeft .5s ease both;}
.anim-d1{animation-delay:.1s}.anim-d2{animation-delay:.2s}.anim-d3{animation-delay:.3s}.anim-d4{animation-delay:.4s}.anim-d5{animation-delay:.5s}
.flex{display:flex;}.flex-col{display:flex;flex-direction:column;}
.items-center{align-items:center;}.justify-center{justify-content:center;}.justify-between{justify-content:space-between;}
.gap-1{gap:8px}.gap-2{gap:12px}.gap-3{gap:16px}.gap-4{gap:24px}
.w-full{width:100%}.h-full{height:100%}
.text-center{text-align:center}
.mt-1{margin-top:8px}.mt-2{margin-top:12px}.mt-3{margin-top:16px}.mt-4{margin-top:24px}
.mb-1{margin-bottom:8px}.mb-2{margin-bottom:12px}.mb-3{margin-bottom:16px}
.overflow-auto{overflow:auto}
.relative{position:relative}.absolute{position:absolute}
.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 20px;border-radius:var(--r-sm);font-family:var(--font-b);font-size:14px;font-weight:600;cursor:pointer;border:none;transition:all .2s;text-decoration:none;letter-spacing:.3px;}
.btn:disabled{opacity:.45;cursor:not-allowed;}
.btn-primary{background:var(--red);color:#fff;}
.btn-primary:hover:not(:disabled){background:var(--red-d);box-shadow:0 4px 20px var(--red-glow);}
.btn-outline{background:transparent;color:var(--red);border:1.5px solid var(--red);}
.btn-outline:hover:not(:disabled){background:rgba(229,57,53,.1);}
.btn-ghost{background:transparent;color:var(--muted);border:1.5px solid var(--border2);}
.btn-ghost:hover:not(:disabled){background:var(--s3);color:var(--text);}
.btn-success{background:var(--green);color:#fff;}
.btn-success:hover:not(:disabled){filter:brightness(1.1);}
.btn-danger{background:var(--red-d);color:#fff;}
.btn-danger:hover:not(:disabled){filter:brightness(1.1);}
.btn-sm{padding:6px 14px;font-size:13px;}
.btn-lg{padding:14px 32px;font-size:16px;border-radius:var(--r-md);}
.btn-icon{width:36px;height:36px;padding:0;border-radius:var(--r-sm);}

/* ── CARDS ── */
.card{background:var(--s1);border:1px solid var(--border2);border-radius:var(--r-lg);padding:24px;}
.card-sm{padding:16px;border-radius:var(--r-md);}
.card:hover{border-color:var(--border);}
.card-glow{border-color:var(--red);box-shadow:0 0 30px var(--red-glow);}

/* ── FORMS ── */
.form-group{display:flex;flex-direction:column;gap:6px;margin-bottom:16px;}
.form-group label{font-size:13px;font-weight:500;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;}
.input{background:var(--s2);border:1.5px solid var(--border2);border-radius:var(--r-sm);color:var(--text);font-family:var(--font-b);font-size:14px;padding:10px 14px;width:100%;transition:border-color .2s,box-shadow .2s;}
.input:focus{outline:none;border-color:var(--red);box-shadow:0 0 0 3px rgba(229,57,53,.15);}
.input::placeholder{color:var(--dim);}
select.input{cursor:pointer;}

/* ── BADGES ── */
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;}
.badge-red{background:rgba(229,57,53,.15);color:var(--red-l);}
.badge-green{background:rgba(46,204,113,.15);color:var(--green);}
.badge-yellow{background:rgba(241,196,15,.15);color:var(--yellow);}
.badge-blue{background:rgba(74,144,217,.15);color:var(--blue);}
.badge-orange{background:rgba(230,126,34,.15);color:var(--orange);}
.badge-muted{background:var(--s3);color:var(--muted);}

/* ── STAT CARD ── */
.stat-card{background:var(--s1);border:1px solid var(--border2);border-radius:var(--r-lg);padding:20px 24px;display:flex;flex-direction:column;gap:10px;transition:transform .2s;}
.stat-card:hover{transform:translateY(-2px);border-color:var(--border);}
.stat-num{font-family:var(--font-d);font-size:40px;letter-spacing:1px;line-height:1;}
.stat-label{font-size:12px;font-weight:500;color:var(--muted);letter-spacing:.8px;text-transform:uppercase;}
.stat-icon{width:44px;height:44px;border-radius:var(--r-md);display:flex;align-items:center;justify-content:center;font-size:20px;}

/* ── NAVBAR ── */
.navbar{background:rgba(8,8,16,.9);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:0 24px;height:60px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.logo{font-family:var(--font-d);font-size:22px;letter-spacing:2px;color:var(--text);display:flex;align-items:center;gap:10px;cursor:pointer;}
.logo-drop{font-size:24px;animation:heartbeat 2s ease infinite;}

/* ── SIDEBAR ── */
.layout{display:flex;min-height:calc(100vh - 60px);}
.sidebar{width:220px;min-width:220px;background:var(--s1);border-right:1px solid var(--border2);padding:20px 0;display:flex;flex-direction:column;gap:4px;}
.sidebar-item{display:flex;align-items:center;gap:12px;padding:10px 20px;cursor:pointer;transition:all .2s;border-left:3px solid transparent;font-size:14px;font-weight:500;color:var(--muted);}
.sidebar-item:hover{background:var(--s2);color:var(--text);}
.sidebar-item.active{background:rgba(229,57,53,.1);border-left-color:var(--red);color:var(--text);}
.sidebar-icon{font-size:18px;width:22px;text-align:center;}
.sidebar-section{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);padding:16px 20px 6px;}
.main{flex:1;padding:28px 32px;overflow-y:auto;max-height:calc(100vh - 60px);}

/* ── NOTIFICATION BELL ── */
.notif-btn{position:relative;cursor:pointer;width:38px;height:38px;display:flex;align-items:center;justify-content:center;border-radius:var(--r-sm);background:var(--s2);border:1px solid var(--border2);font-size:18px;transition:all .2s;}
.notif-btn:hover{border-color:var(--red);}
.notif-count{position:absolute;top:-5px;right:-5px;background:var(--red);color:#fff;font-size:10px;font-weight:700;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid var(--bg);}

/* ── NOTIFICATION PANEL ── */
.notif-panel{position:absolute;top:48px;right:0;width:360px;background:var(--s1);border:1px solid var(--border);border-radius:var(--r-lg);box-shadow:0 20px 60px rgba(0,0,0,.6);z-index:200;animation:fadeIn .2s ease;}
.notif-panel-header{padding:16px 20px;border-bottom:1px solid var(--border2);display:flex;align-items:center;justify-content:space-between;}
.notif-item{padding:14px 20px;border-bottom:1px solid var(--border2);cursor:pointer;transition:background .15s;display:flex;gap:12px;align-items:flex-start;}
.notif-item:hover{background:var(--s2);}
.notif-item.unread{border-left:3px solid var(--red);}
.notif-dot{width:8px;height:8px;border-radius:50%;background:var(--red);margin-top:6px;flex-shrink:0;}
.notif-title{font-size:13px;font-weight:600;margin-bottom:3px;}
.notif-msg{font-size:12px;color:var(--muted);line-height:1.4;}
.notif-time{font-size:11px;color:var(--dim);margin-top:4px;}

/* ── TOAST ── */
.toast-container{position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;}
.toast{padding:14px 18px;border-radius:var(--r-md);font-size:13px;font-weight:500;display:flex;align-items:center;gap:10px;min-width:300px;max-width:400px;box-shadow:0 8px 30px rgba(0,0,0,.4);animation:slideLeft .3s ease;}
.toast-success{background:#1a3a2a;border:1px solid var(--green);color:var(--green);}
.toast-error{background:#3a1a1a;border:1px solid var(--red);color:var(--red-l);}
.toast-info{background:#1a2a3a;border:1px solid var(--blue);color:var(--blue);}
.toast-warning{background:#3a2a1a;border:1px solid var(--yellow);color:var(--yellow);}

/* ── MODAL ── */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:500;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);animation:fadeIn .2s ease;}
.modal{background:var(--s1);border:1px solid var(--border);border-radius:var(--r-xl);padding:32px;max-width:540px;width:90vw;max-height:85vh;overflow-y:auto;animation:fadeUp .3s ease;}
.modal-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;}
.modal-title{font-family:var(--font-d);font-size:22px;letter-spacing:1px;}
.modal-close{cursor:pointer;font-size:22px;color:var(--muted);padding:4px;transition:color .2s;}
.modal-close:hover{color:var(--text);}

/* ── REQUEST CARD ── */
.req-card{background:var(--s2);border:1px solid var(--border2);border-radius:var(--r-lg);padding:20px;transition:all .2s;position:relative;overflow:hidden;}
.req-card:hover{border-color:var(--border);transform:translateY(-1px);}
.req-card.critical{border-color:rgba(229,57,53,.4);animation:flash-border 2s ease infinite;}
.req-card.high{border-color:rgba(230,126,34,.3);}
.req-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
.req-card.critical::before{background:var(--red);}
.req-card.high::before{background:var(--orange);}
.req-card.medium::before{background:var(--yellow);}
.req-card.low::before{background:var(--green);}

/* ── BLOOD GROUP BADGE ── */
.blood-badge{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;background:rgba(229,57,53,.15);border:2px solid var(--red);color:var(--red-l);font-family:var(--font-m);font-size:13px;font-weight:700;flex-shrink:0;}
.blood-badge-lg{width:60px;height:60px;font-size:16px;}

/* ── PROGRESS BAR ── */
.progress-wrap{background:var(--s3);border-radius:4px;overflow:hidden;height:8px;}
.progress-bar{height:100%;border-radius:4px;transition:width .6s cubic-bezier(.4,0,.2,1);}

/* ── DONOR CARD ── */
.donor-card{background:var(--s2);border:1px solid var(--border2);border-radius:var(--r-md);padding:16px;display:flex;align-items:center;gap:14px;transition:all .2s;}
.donor-card:hover{border-color:var(--border);}
.donor-avatar{width:44px;height:44px;border-radius:50%;background:var(--s4);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;}
.score-bar{height:6px;border-radius:3px;background:var(--s4);overflow:hidden;margin-top:4px;}
.score-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--red),var(--red-l));}

/* ── TABLE ── */
.table-wrap{overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{text-align:left;padding:10px 14px;font-size:11px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border2);}
td{padding:12px 14px;border-bottom:1px solid var(--border2);vertical-align:middle;}
tr:hover td{background:var(--s2);}
tr:last-child td{border-bottom:none;}

/* ── LANDING PAGE ── */
.landing{min-height:100vh;}
.hero{min-height:90vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:60px 24px;position:relative;overflow:hidden;}
.hero-bg{position:absolute;inset:0;background:radial-gradient(ellipse 80% 80% at 50% -20%,rgba(229,57,53,.2),transparent);pointer-events:none;}
.hero-grid{position:absolute;inset:0;background-image:linear-gradient(var(--border2) 1px,transparent 1px),linear-gradient(90deg,var(--border2) 1px,transparent 1px);background-size:60px 60px;opacity:.4;pointer-events:none;}
.hero-drop{font-size:96px;animation:float 4s ease-in-out infinite,heartbeat 2s ease infinite;}
.hero-title{font-family:var(--font-d);font-size:clamp(52px,9vw,100px);letter-spacing:3px;line-height:.95;margin:16px 0;}
.hero-title span{color:var(--red);}
.hero-sub{font-size:clamp(15px,2vw,18px);color:var(--muted);max-width:580px;line-height:1.7;margin:0 auto 36px;}
.hero-stats{display:flex;gap:40px;margin:40px 0;flex-wrap:wrap;justify-content:center;}
.hero-stat{text-align:center;}
.hero-stat-num{font-family:var(--font-d);font-size:42px;color:var(--red-l);}
.hero-stat-label{font-size:12px;color:var(--muted);letter-spacing:.8px;text-transform:uppercase;}
.features{padding:80px 24px;max-width:1100px;margin:0 auto;}
.features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;margin-top:48px;}
.feature-card{background:var(--s1);border:1px solid var(--border2);border-radius:var(--r-lg);padding:28px;transition:all .3s;}
.feature-card:hover{border-color:var(--border);transform:translateY(-4px);box-shadow:0 20px 60px rgba(0,0,0,.3);}
.feature-icon{font-size:36px;margin-bottom:16px;display:block;}
.feature-title{font-family:var(--font-d);font-size:22px;letter-spacing:1px;margin-bottom:10px;}
.feature-desc{font-size:14px;color:var(--muted);line-height:1.7;}
.section-label{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--red);margin-bottom:12px;}
.section-title{font-family:var(--font-d);font-size:clamp(32px,5vw,52px);letter-spacing:2px;}

/* ── AUTH PAGE ── */
.auth-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:40px 24px;background:radial-gradient(ellipse 60% 60% at 50% 50%,rgba(229,57,53,.08),transparent);}
.auth-box{background:var(--s1);border:1px solid var(--border);border-radius:var(--r-xl);padding:40px;width:100%;max-width:440px;box-shadow:0 40px 80px rgba(0,0,0,.5);}
.auth-tabs{display:flex;border-bottom:1px solid var(--border2);margin-bottom:28px;}
.auth-tab{flex:1;padding:10px;text-align:center;cursor:pointer;font-size:14px;font-weight:600;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px;transition:all .2s;}
.auth-tab.active{color:var(--red);border-bottom-color:var(--red);}
.role-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;}
.role-btn{padding:10px;border:1.5px solid var(--border2);border-radius:var(--r-sm);cursor:pointer;text-align:center;transition:all .2s;background:var(--s2);}
.role-btn:hover{border-color:var(--dim);}
.role-btn.selected{border-color:var(--red);background:rgba(229,57,53,.1);}
.role-btn-icon{font-size:22px;margin-bottom:4px;}
.role-btn-name{font-size:12px;font-weight:600;color:var(--muted);}
.role-btn.selected .role-btn-name{color:var(--red-l);}

/* ── AVAILABILITY TOGGLE ── */
.avail-toggle{position:relative;width:56px;height:30px;border-radius:15px;cursor:pointer;transition:background .3s;flex-shrink:0;}
.avail-toggle.on{background:var(--green);}
.avail-toggle.off{background:var(--s4);}
.avail-knob{position:absolute;top:3px;width:24px;height:24px;border-radius:50%;background:#fff;transition:left .3s;box-shadow:0 2px 4px rgba(0,0,0,.3);}
.avail-toggle.on .avail-knob{left:29px;}
.avail-toggle.off .avail-knob{left:3px;}

/* ── CHARTS ── */
.donut-wrap{position:relative;width:120px;height:120px;flex-shrink:0;}
.donut-svg{transform:rotate(-90deg);}
.donut-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;}
.bar-chart{display:flex;flex-direction:column;gap:8px;}
.bar-row{display:flex;align-items:center;gap:10px;}
.bar-label{font-size:12px;font-weight:600;color:var(--muted);width:32px;text-align:right;font-family:var(--font-m);}
.bar-wrap{flex:1;height:20px;background:var(--s3);border-radius:4px;overflow:hidden;}
.bar-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--red-d),var(--red));transition:width 1s cubic-bezier(.4,0,.2,1);}
.bar-count{font-size:12px;color:var(--muted);width:28px;font-family:var(--font-m);}

/* ── LIVE INDICATOR ── */
.live-dot{width:8px;height:8px;border-radius:50%;background:var(--green);position:relative;flex-shrink:0;}
.live-dot::after{content:'';position:absolute;inset:-4px;border-radius:50%;background:var(--green);opacity:.3;animation:pulse-ring 1.5s ease infinite;}

/* ── LOADER ── */
.spinner{width:24px;height:24px;border:2.5px solid var(--s4);border-top-color:var(--red);border-radius:50%;animation:spin .7s linear infinite;}
.page-loader{display:flex;align-items:center;justify-content:center;min-height:300px;}

/* ── EMPTY STATE ── */
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 24px;text-align:center;gap:12px;}
.empty-icon{font-size:48px;opacity:.4;}
.empty-text{font-size:15px;color:var(--muted);}

/* ── SECTION HEADER ── */
.section-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
.section-hdr-title{font-family:var(--font-d);font-size:22px;letter-spacing:1px;}

/* ── RESPONSIVE ── */
@media(max-width:768px){
  .sidebar{display:none;}
  .main{padding:16px;}
  .hero-drop{font-size:64px;}
  .stat-num{font-size:30px;}
  .features-grid{grid-template-columns:1fr;}
  .hero-stats{gap:24px;}
}
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect, useRef, useCallback, useContext, createContext } = React;

// ═══════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════
const getToken = () => localStorage.getItem('bb_token');
const api = {
  _h: (extra={}) => ({ 'Content-Type':'application/json', 'Authorization': `Bearer ${getToken()}`, ...extra }),
  get:   (url)       => fetch(url, { headers: api._h() }).then(r => r.json()),
  post:  (url, body) => fetch(url, { method:'POST',  headers: api._h(), body: JSON.stringify(body) }).then(r => r.json()),
  put:   (url, body) => fetch(url, { method:'PUT',   headers: api._h(), body: JSON.stringify(body) }).then(r => r.json()),
  patch: (url, body) => fetch(url, { method:'PATCH', headers: api._h(), body: JSON.stringify(body) }).then(r => r.json()),
};

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════
const urgencyColor = u => ({ critical:'red', high:'orange', medium:'yellow', low:'green' }[u] || 'muted');
const statusColor  = s => ({ pending:'yellow', matched:'green', closed:'muted' }[s] || 'muted');
const urgencyEmoji = u => ({ critical:'🚨', high:'⚠️', medium:'🔵', low:'🟢' }[u] || '');
const relTime = iso => {
  if (!iso) return 'Unknown';
  const diff = (Date.now() - new Date(iso + 'Z').getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  return `${Math.floor(diff/86400)}d ago`;
};
const bloodGroups = ['O+','O-','A+','A-','B+','B-','AB+','AB-'];

// ═══════════════════════════════════════════════════════════════
// TOAST SYSTEM
// ═══════════════════════════════════════════════════════════════
const ToastCtx = createContext(null);
function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const show = useCallback((msg, type='info', dur=4000) => {
    const id = Date.now();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), dur);
  }, []);
  const icons = { success:'✅', error:'❌', info:'ℹ️', warning:'⚠️' };
  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            <span>{icons[t.type]}</span><span>{t.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
const useToast = () => useContext(ToastCtx);

// ═══════════════════════════════════════════════════════════════
// SOCKET HOOK
// ═══════════════════════════════════════════════════════════════
function useSocket(user, onEvent) {
  const sockRef = useRef(null);
  useEffect(() => {
    if (!user) return;
    const sock = io({ transports: ['websocket', 'polling'] });
    sockRef.current = sock;
    sock.on('connect', () => {
      sock.emit('join', { room: `user_${user.id}` });
      if (['hospital','patient'].includes(user.role)) sock.emit('join_role_room', { role: user.role });
      if (user.role === 'admin') sock.emit('join_role_room', { role: 'admin' });
    });
    const events = ['new_request','donor_accepted','request_created','request_updated','donor_status_changed'];
    events.forEach(ev => sock.on(ev, data => onEvent && onEvent(ev, data)));
    return () => { sock.disconnect(); sockRef.current = null; };
  }, [user?.id]);
  return sockRef;
}

// ═══════════════════════════════════════════════════════════════
// NAVBAR
// ═══════════════════════════════════════════════════════════════
function Navbar({ user, onLogout, onNav, notifications }) {
  const [showNotif, setShowNotif] = useState(false);
  const [notifs, setNotifs] = useState(notifications || []);
  const toast = useToast();
  useEffect(() => setNotifs(notifications || []), [notifications]);
  const unread = notifs.filter(n => !n.read).length;

  const markAllRead = async () => {
    await api.patch('/api/notifications/read-all');
    setNotifs(n => n.map(x => ({ ...x, read: true })));
  };
  const markOne = async (id) => {
    await api.patch(`/api/notifications/${id}/read`);
    setNotifs(n => n.map(x => x.id === id ? { ...x, read: true } : x));
  };

  return (
    <nav className="navbar">
      <div className="logo" onClick={() => onNav('landing')}>
        <span className="logo-drop">🩸</span>
        <span>BLOOD<span style={{color:'var(--red)'}}>BRIDGE</span></span>
        <span style={{fontSize:'10px',color:'var(--dim)',letterSpacing:'2px',marginLeft:'2px',fontFamily:'var(--font-m)',marginTop:'4px'}}>AI</span>
      </div>
      {user ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2" style={{padding:'6px 14px',background:'var(--s2)',borderRadius:'var(--r-sm)',border:'1px solid var(--border2)'}}>
            <div className="live-dot" />
            <span style={{fontSize:'12px',color:'var(--muted)',textTransform:'uppercase',letterSpacing:'.8px'}}>{user.role}</span>
            <span style={{fontSize:'13px',fontWeight:'600',color:'var(--text)'}}>{user.name.split(' ')[0]}</span>
          </div>
          <div className="relative">
            <div className="notif-btn" onClick={() => setShowNotif(s => !s)}>
              🔔
              {unread > 0 && <span className="notif-count">{unread > 9 ? '9+' : unread}</span>}
            </div>
            {showNotif && (
              <div className="notif-panel">
                <div className="notif-panel-header">
                  <span style={{fontWeight:'700',fontSize:'14px'}}>Notifications</span>
                  <button className="btn btn-ghost btn-sm" onClick={markAllRead}>Mark all read</button>
                </div>
                <div style={{maxHeight:'360px',overflowY:'auto'}}>
                  {notifs.length === 0 ? (
                    <div className="empty" style={{padding:'32px'}}>
                      <span className="empty-icon">🔕</span>
                      <span className="empty-text">No notifications</span>
                    </div>
                  ) : notifs.slice(0,15).map(n => (
                    <div key={n.id} className={`notif-item ${!n.read ? 'unread' : ''}`} onClick={() => markOne(n.id)}>
                      {!n.read && <div className="notif-dot" />}
                      <div style={{flex:1}}>
                        <div className="notif-title">{n.title}</div>
                        <div className="notif-msg">{n.message}</div>
                        <div className="notif-time">{relTime(n.created_at)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onLogout}>Sign Out</button>
        </div>
      ) : (
        <div className="flex gap-2">
          <button className="btn btn-ghost btn-sm" onClick={() => onNav('auth')}>Login</button>
          <button className="btn btn-primary btn-sm" onClick={() => onNav('auth')}>Register</button>
        </div>
      )}
    </nav>
  );
}

// ═══════════════════════════════════════════════════════════════
// LANDING PAGE
// ═══════════════════════════════════════════════════════════════
function LandingPage({ onNav }) {
  const features = [
    { icon:'🤖', title:'AI-Powered Matching', desc:'Our algorithm scores donors by blood compatibility, GPS distance, availability, and donation history — finding the best match in milliseconds.' },
    { icon:'⚡', title:'Real-Time Alerts', desc:'Socket.io delivers instant push notifications to matched donors the moment an emergency request is created. Zero delay.' },
    { icon:'📍', title:'Geolocation Radius', desc:'Haversine formula calculates true distances. Donors within your configurable radius are ranked and surfaced automatically.' },
    { icon:'🛡️', title:'Role-Based Access', desc:'Donors, patients, hospitals, and admins each get tailored dashboards and permissions. Secure JWT authentication throughout.' },
    { icon:'📊', title:'Admin Analytics', desc:'Full system visibility: request fulfillment rates, blood group distribution, donor availability, and live activity logs.' },
    { icon:'🌐', title:'Scalability Ready', desc:'Clean service-layer architecture, modular design, and Redis-ready configuration for horizontal scaling.' },
  ];
  return (
    <div className="landing">
      <div className="hero">
        <div className="hero-bg" />
        <div className="hero-grid" />
        <div className="hero-drop anim-up">🩸</div>
        <h1 className="hero-title anim-up anim-d1">
          BLOOD<span>BRIDGE</span><br/>AI SYSTEM
        </h1>
        <p className="hero-sub anim-up anim-d2">
          AI-powered emergency blood donor matching with real-time Socket.io alerts, 
          GPS-based radius search, and instant hospital-donor coordination.
        </p>
        <div className="flex gap-3 anim-up anim-d3" style={{flexWrap:'wrap',justifyContent:'center'}}>
          <button className="btn btn-primary btn-lg" onClick={() => onNav('auth')}>
            🩸 Get Started Free
          </button>
          <button className="btn btn-outline btn-lg" onClick={() => onNav('auth')}>
            🏥 Hospital Portal
          </button>
        </div>
        <div className="hero-stats anim-up anim-d4">
          {[['12,500+','Registered Donors'],['98.2%','Match Rate'],['< 2min','Avg Alert Time'],['50+','Cities Covered']].map(([n,l]) => (
            <div key={l} className="hero-stat">
              <div className="hero-stat-num">{n}</div>
              <div className="hero-stat-label">{l}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="features">
        <div style={{textAlign:'center',marginBottom:'16px'}}>
          <div className="section-label">Core Technology</div>
          <div className="section-title">Built for <span style={{color:'var(--red)'}}>Emergencies</span></div>
        </div>
        <div className="features-grid">
          {features.map((f,i) => (
            <div key={i} className={`feature-card anim-up anim-d${Math.min(i+1,5)}`}>
              <span className="feature-icon">{f.icon}</span>
              <div className="feature-title">{f.title}</div>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
      <div style={{padding:'60px 24px',textAlign:'center',borderTop:'1px solid var(--border2)'}}>
        <div className="section-label">How It Works</div>
        <div className="section-title" style={{marginBottom:'40px'}}>
          Three Steps to <span style={{color:'var(--red)'}}>Save a Life</span>
        </div>
        <div style={{display:'flex',gap:'32px',maxWidth:'900px',margin:'0 auto',flexWrap:'wrap',justifyContent:'center'}}>
          {[
            ['1','Hospital Creates Request','Blood group, urgency level, location, and units needed are submitted.'],
            ['2','AI Finds Best Donors','Matching algorithm scores all compatible, available donors by proximity and history.'],
            ['3','Instant Alerts Sent','Real-time Socket.io notifications reach matched donors within seconds.'],
          ].map(([num,title,desc]) => (
            <div key={num} style={{flex:'1',minWidth:'240px',padding:'28px',background:'var(--s1)',borderRadius:'var(--r-lg)',border:'1px solid var(--border2)'}}>
              <div style={{fontFamily:'var(--font-d)',fontSize:'52px',color:'var(--red)',lineHeight:1}}>{num}</div>
              <div style={{fontWeight:'700',fontSize:'16px',margin:'12px 0 8px'}}>{title}</div>
              <p style={{fontSize:'14px',color:'var(--muted)',lineHeight:1.6}}>{desc}</p>
            </div>
          ))}
        </div>
        <button className="btn btn-primary btn-lg mt-4" style={{marginTop:'40px'}} onClick={() => onNav('auth')}>
          Start Saving Lives →
        </button>
      </div>
      <div style={{padding:'20px 24px',textAlign:'center',borderTop:'1px solid var(--border2)'}}>
        <p style={{fontSize:'12px',color:'var(--dim)'}}>BloodBridge AI • Emergency Donor Matching System • Demo Credentials in README</p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// AUTH PAGE
// ═══════════════════════════════════════════════════════════════
function AuthPage({ onLogin }) {
  const [tab, setTab] = useState('login');
  const [role, setRole] = useState('donor');
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ name:'', email:'', password:'', phone:'', blood_group:'O+' });
  const toast = useToast();

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const quickFill = (email, password) => setForm(f => ({ ...f, email, password }));

  const submit = async () => {
    if (!form.email || !form.password) { toast('Email and password required', 'error'); return; }
    setLoading(true);
    try {
      const url  = tab === 'login' ? '/api/auth/login' : '/api/auth/register';
      const body = tab === 'login' ? { email: form.email, password: form.password }
                                   : { ...form, role };
      const res  = await api.post(url, body);
      if (res.token) {
        localStorage.setItem('bb_token', res.token);
        toast(`Welcome, ${res.user.name}! 🩸`, 'success');
        onLogin(res.user);
      } else {
        toast(res.error || 'Authentication failed', 'error');
      }
    } catch(e) { toast('Network error. Is the server running?', 'error'); }
    setLoading(false);
  };

  const roles = [
    { id:'donor',    icon:'🩸', label:'Donor' },
    { id:'patient',  icon:'🏥', label:'Patient' },
    { id:'hospital', icon:'🏨', label:'Hospital' },
  ];

  const demoLogins = [
    { label:'Admin',    email:'admin@bloodbridge.org',    pw:'admin123',   role:'admin'    },
    { label:'Donor',    email:'alice@donor.com',          pw:'pass123',    role:'donor'    },
    { label:'Hospital', email:'hospital@citygeneral.com', pw:'hosp123',    role:'hospital' },
    { label:'Patient',  email:'patient@example.com',      pw:'patient123', role:'patient'  },
  ];

  return (
    <div className="auth-wrap">
      <div className="auth-box anim-up">
        <div style={{textAlign:'center',marginBottom:'28px'}}>
          <div style={{fontSize:'40px',marginBottom:'8px'}}>🩸</div>
          <div style={{fontFamily:'var(--font-d)',fontSize:'26px',letterSpacing:'2px'}}>
            BLOOD<span style={{color:'var(--red)'}}>BRIDGE</span>
          </div>
          <div style={{fontSize:'12px',color:'var(--muted)',marginTop:'4px',letterSpacing:'.5px'}}>Emergency Donor Network</div>
        </div>

        <div className="auth-tabs">
          <div className={`auth-tab ${tab==='login'?'active':''}`} onClick={() => setTab('login')}>Sign In</div>
          <div className={`auth-tab ${tab==='register'?'active':''}`} onClick={() => setTab('register')}>Register</div>
        </div>

        {tab === 'register' && (
          <>
            <div className="form-group">
              <label>Select Role</label>
              <div className="role-grid">
                {roles.map(r => (
                  <div key={r.id} className={`role-btn ${role===r.id?'selected':''}`} onClick={() => setRole(r.id)}>
                    <div className="role-btn-icon">{r.icon}</div>
                    <div className="role-btn-name">{r.label}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="form-group">
              <label>Full Name</label>
              <input className="input" placeholder="Your full name" value={form.name} onChange={e => set('name', e.target.value)} />
            </div>
          </>
        )}
        <div className="form-group">
          <label>Email</label>
          <input className="input" type="email" placeholder="you@example.com" value={form.email} onChange={e => set('email', e.target.value)} />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input className="input" type="password" placeholder="••••••••" value={form.password} onChange={e => set('password', e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()} />
        </div>
        {tab === 'register' && role === 'donor' && (
          <>
            <div className="form-group">
              <label>Blood Group</label>
              <select className="input" value={form.blood_group} onChange={e => set('blood_group', e.target.value)}>
                {bloodGroups.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Phone</label>
              <input className="input" placeholder="+91 98765 43210" value={form.phone} onChange={e => set('phone', e.target.value)} />
            </div>
          </>
        )}
        <button className="btn btn-primary w-full btn-lg" onClick={submit} disabled={loading}>
          {loading ? <span className="spinner"/> : (tab === 'login' ? '🔐 Sign In' : '🚀 Create Account')}
        </button>

        {tab === 'login' && (
          <div style={{marginTop:'20px'}}>
            <div style={{fontSize:'11px',color:'var(--dim)',textAlign:'center',marginBottom:'10px',letterSpacing:'1px',textTransform:'uppercase'}}>Quick Demo Login</div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'6px'}}>
              {demoLogins.map(d => (
                <button key={d.label} className="btn btn-ghost btn-sm" style={{fontSize:'12px'}}
                  onClick={() => quickFill(d.email, d.pw)}>
                  {d.label === 'Admin' ? '⚙️' : d.label === 'Donor' ? '🩸' : d.label === 'Hospital' ? '🏥' : '👤'} {d.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// DONOR DASHBOARD
// ═══════════════════════════════════════════════════════════════
function DonorDashboard({ user, onSocketEvent }) {
  const [tab, setTab] = useState('overview');
  const [donor, setDonor] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({});
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const [dRes, rRes] = await Promise.all([api.get('/api/donors/profile'), api.get('/api/requests')]);
      if (!dRes.error) { setDonor(dRes); setEditForm(dRes); }
      if (!rRes.error && Array.isArray(rRes)) setRequests(rRes);
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!onSocketEvent) return;
    const handler = (ev, data) => {
      if (ev === 'new_request') {
        setRequests(r => {
          const exists = r.find(x => x.id === data.request.id);
          return exists ? r : [data.request, ...r];
        });
        toast(`🚨 New emergency: ${data.request.blood_group} blood needed! Score: ${data.match_score}`, 'warning', 8000);
      }
    };
    onSocketEvent(handler);
    return () => onSocketEvent(null);
  }, []);

  const toggleAvailability = async () => {
    const res = await api.patch('/api/donors/availability', { availability: !donor.availability });
    if (res.availability !== undefined) {
      setDonor(d => ({ ...d, availability: res.availability }));
      toast(res.availability ? '✅ You are now Available' : '⏸️ Marked as Unavailable', res.availability ? 'success' : 'info');
    }
  };

  const respond = async (reqId, action) => {
    const res = await api.post(`/api/requests/${reqId}/respond`, { action });
    if (res.status === 'ok') {
      toast(action === 'accept' ? '✅ Request Accepted! Hospital has been notified.' : 'Request rejected.', action === 'accept' ? 'success' : 'info');
      setRequests(r => r.map(x => x.id === reqId ? { ...x, _responded: action } : x));
    } else {
      toast(res.error || 'Error responding', 'error');
    }
  };

  const saveProfile = async () => {
    const res = await api.put('/api/donors/profile', editForm);
    if (!res.error) { setDonor(res); setEditMode(false); toast('Profile updated!', 'success'); }
    else toast(res.error, 'error');
  };

  if (loading) return <div className="page-loader"><div className="spinner"/></div>;
  if (!donor) return <div className="empty"><span className="empty-icon">😕</span><span className="empty-text">Donor profile not found. Please re-login.</span></div>;

  const tabs = [
    { id:'overview', icon:'🏠', label:'Overview' },
    { id:'requests', icon:'🚨', label:`Requests ${requests.length > 0 ? `(${requests.length})` : ''}` },
    { id:'profile',  icon:'👤', label:'Profile'  },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div style={{padding:'16px 20px 8px',fontSize:'11px',fontWeight:'700',letterSpacing:'1.5px',textTransform:'uppercase',color:'var(--dim)'}}>Donor Portal</div>
        {tabs.map(t => (
          <div key={t.id} className={`sidebar-item ${tab===t.id?'active':''}`} onClick={() => setTab(t.id)}>
            <span className="sidebar-icon">{t.icon}</span>{t.label}
          </div>
        ))}
        <div style={{flex:1}}/>
        <div style={{padding:'16px 20px',borderTop:'1px solid var(--border2)'}}>
          <div style={{display:'flex',alignItems:'center',gap:'10px'}}>
            <div className="blood-badge" style={{width:'36px',height:'36px',fontSize:'11px'}}>{donor.blood_group}</div>
            <div>
              <div style={{fontSize:'13px',fontWeight:'600'}}>{donor.name?.split(' ')[0]}</div>
              <div style={{fontSize:'11px',color:'var(--muted)'}}>{donor.total_donations} donations</div>
            </div>
          </div>
        </div>
      </aside>

      <main className="main">
        {tab === 'overview' && (
          <div className="anim-fade">
            <div className="section-hdr">
              <div className="section-hdr-title">Donor Overview</div>
              <div className="flex items-center gap-2">
                <span style={{fontSize:'13px',color:'var(--muted)'}}>Availability</span>
                <div className={`avail-toggle ${donor.availability?'on':'off'}`} onClick={toggleAvailability}>
                  <div className="avail-knob"/>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:'16px',marginBottom:'24px'}}>
              {[
                { icon:'🩸', num: donor.blood_group, label:'Blood Group',    color:'var(--red)'    },
                { icon:'✅', num: donor.total_donations, label:'Total Donations', color:'var(--green)'  },
                { icon:'❤️', num: (donor.total_donations||0)*3, label:'Lives Saved',    color:'var(--red-l)'  },
                { icon:'📡', num: requests.length, label:'Matched Requests',color:'var(--blue)'   },
              ].map((s,i) => (
                <div key={i} className="stat-card">
                  <div className="stat-icon" style={{background:`${s.color}20`}}>{s.icon}</div>
                  <div className="stat-num" style={{color:s.color}}>{s.num}</div>
                  <div className="stat-label">{s.label}</div>
                </div>
              ))}
            </div>

            {/* Status Card */}
            <div className={`card ${donor.availability ? 'card-glow' : ''}`} style={{marginBottom:'24px'}}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {donor.availability ? <div className="live-dot"/> : <div style={{width:'8px',height:'8px',borderRadius:'50%',background:'var(--muted)'}}/>}
                  <div>
                    <div style={{fontWeight:'700',fontSize:'16px'}}>{donor.availability ? '🟢 Available for Donation' : '🔴 Currently Unavailable'}</div>
                    <div style={{fontSize:'13px',color:'var(--muted)',marginTop:'3px'}}>
                      {donor.availability ? 'You will receive emergency alerts' : 'You will not receive new requests'}
                    </div>
                  </div>
                </div>
                <button className={`btn ${donor.availability ? 'btn-danger' : 'btn-success'} btn-sm`} onClick={toggleAvailability}>
                  {donor.availability ? 'Go Unavailable' : 'Go Available'}
                </button>
              </div>
            </div>

            {/* Recent Requests */}
            <div className="section-hdr"><div className="section-hdr-title">Matched Requests</div></div>
            {requests.length === 0 ? (
              <div className="empty"><span className="empty-icon">📭</span><span className="empty-text">No matched requests yet. Stay available!</span></div>
            ) : requests.slice(0,3).map(r => <RequestCardDonor key={r.id} req={r} onRespond={respond} />)}
          </div>
        )}

        {tab === 'requests' && (
          <div className="anim-fade">
            <div className="section-hdr">
              <div className="section-hdr-title">Emergency Requests</div>
              <span className="badge badge-red">{requests.length} matched</span>
            </div>
            {requests.length === 0 ? (
              <div className="empty"><span className="empty-icon">📭</span><span className="empty-text">No emergency requests matched to you.</span></div>
            ) : requests.map(r => <RequestCardDonor key={r.id} req={r} onRespond={respond} />)}
          </div>
        )}

        {tab === 'profile' && (
          <div className="anim-fade">
            <div className="section-hdr">
              <div className="section-hdr-title">Donor Profile</div>
              <button className="btn btn-outline btn-sm" onClick={() => setEditMode(e => !e)}>
                {editMode ? 'Cancel' : '✏️ Edit'}
              </button>
            </div>
            <div className="card">
              <div className="flex items-center gap-4" style={{marginBottom:'24px'}}>
                <div className="blood-badge blood-badge-lg">{donor.blood_group}</div>
                <div>
                  <div style={{fontWeight:'700',fontSize:'18px'}}>{donor.name}</div>
                  <div style={{fontSize:'13px',color:'var(--muted)',marginTop:'3px'}}>{donor.email}</div>
                  <div style={{marginTop:'6px'}}>
                    <span className={`badge badge-${donor.availability ? 'green' : 'muted'}`}>
                      {donor.availability ? '● Available' : '● Unavailable'}
                    </span>
                  </div>
                </div>
              </div>

              {editMode ? (
                <>
                  <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'16px'}}>
                    <div className="form-group">
                      <label>Name</label>
                      <input className="input" value={editForm.name||''} onChange={e => setEditForm(f => ({...f,name:e.target.value}))} />
                    </div>
                    <div className="form-group">
                      <label>Phone</label>
                      <input className="input" value={editForm.phone||''} onChange={e => setEditForm(f => ({...f,phone:e.target.value}))} />
                    </div>
                    <div className="form-group">
                      <label>Blood Group</label>
                      <select className="input" value={editForm.blood_group||'O+'} onChange={e => setEditForm(f => ({...f,blood_group:e.target.value}))}>
                        {bloodGroups.map(g => <option key={g} value={g}>{g}</option>)}
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Last Donation</label>
                      <input className="input" type="date" value={(editForm.last_donation||'').slice(0,10)} onChange={e => setEditForm(f => ({...f,last_donation:e.target.value}))} />
                    </div>
                    <div className="form-group">
                      <label>Latitude</label>
                      <input className="input" type="number" step="0.0001" value={editForm.lat||''} onChange={e => setEditForm(f => ({...f,lat:parseFloat(e.target.value)}))} />
                    </div>
                    <div className="form-group">
                      <label>Longitude</label>
                      <input className="input" type="number" step="0.0001" value={editForm.lng||''} onChange={e => setEditForm(f => ({...f,lng:parseFloat(e.target.value)}))} />
                    </div>
                  </div>
                  <button className="btn btn-primary" onClick={saveProfile}>💾 Save Profile</button>
                </>
              ) : (
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'16px'}}>
                  {[
                    ['📞 Phone', donor.phone || '—'],
                    ['🩸 Blood Group', donor.blood_group],
                    ['💉 Total Donations', donor.total_donations],
                    ['📅 Last Donation', donor.last_donation ? donor.last_donation.slice(0,10) : 'Never'],
                    ['📍 Location', `${donor.lat?.toFixed(4)}, ${donor.lng?.toFixed(4)}`],
                  ].map(([k,v]) => (
                    <div key={k} style={{background:'var(--s2)',borderRadius:'var(--r-sm)',padding:'14px'}}>
                      <div style={{fontSize:'11px',color:'var(--dim)',letterSpacing:'.8px',textTransform:'uppercase',marginBottom:'4px'}}>{k}</div>
                      <div style={{fontSize:'14px',fontWeight:'600',fontFamily:'var(--font-m)'}}>{v}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function RequestCardDonor({ req, onRespond }) {
  const myResponse = req._responded || req.matched_donors?.find(m => m.response)?.response;
  return (
    <div className={`req-card ${req.urgency} mb-3`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span>{urgencyEmoji(req.urgency)}</span>
          <span className={`badge badge-${urgencyColor(req.urgency)}`}>{req.urgency.toUpperCase()}</span>
          <span className="badge badge-muted">{req.blood_group}</span>
        </div>
        <span className={`badge badge-${statusColor(req.status)}`}>{req.status}</span>
      </div>
      <div style={{fontWeight:'700',fontSize:'16px',marginBottom:'4px'}}>{req.hospital_name}</div>
      <div style={{fontSize:'13px',color:'var(--muted)',marginBottom:'12px'}}>
        {req.units} unit(s) needed • {relTime(req.created_at)}
        {req.description && ` • ${req.description}`}
      </div>
      {myResponse ? (
        <div className={`badge badge-${myResponse==='accept'?'green':'muted'}`}>
          {myResponse === 'accept' ? '✅ You Accepted' : '❌ You Rejected'}
        </div>
      ) : req.status !== 'closed' ? (
        <div className="flex gap-2">
          <button className="btn btn-success btn-sm" onClick={() => onRespond(req.id, 'accept')}>✅ Accept</button>
          <button className="btn btn-ghost btn-sm" onClick={() => onRespond(req.id, 'reject')}>✕ Decline</button>
        </div>
      ) : null}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// HOSPITAL DASHBOARD
// ═══════════════════════════════════════════════════════════════
function HospitalDashboard({ user }) {
  const [tab, setTab] = useState('requests');
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedReq, setSelectedReq] = useState(null);
  const [socketCb, setSocketCb] = useState(null);
  const toast = useToast();
  const [form, setForm] = useState({
    blood_group:'O+', units:'1', urgency:'high',
    hospital_name: user.name, lat:'12.9716', lng:'77.5946', description:''
  });

  const load = async () => {
    setLoading(true);
    const res = await api.get('/api/requests');
    if (Array.isArray(res)) setRequests(res);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  // Socket updates
  useEffect(() => {
    const handleWs = (ev, data) => {
      if (ev === 'donor_accepted' && data.request_id) {
        setRequests(rs => rs.map(r => r.id === data.request_id ? {
          ...r,
          accepted_donors: [...(r.accepted_donors||[]).filter(x => x.user_id !== data.donor.user_id), data.donor],
          status: data.request_status || r.status
        } : r));
        toast(`🎉 ${data.donor.name} accepted your blood request!`, 'success', 6000);
      }
      if (ev === 'request_updated') {
        setRequests(rs => rs.map(r => r.id === data.id ? data : r));
      }
    };
    window._bbHospitalHandler = handleWs;
  }, []);

  const setF = (k,v) => setForm(f => ({...f,[k]:v}));
  const createRequest = async () => {
    if (!form.blood_group || !form.units || !form.hospital_name) { toast('Fill required fields','error'); return; }
    const res = await api.post('/api/requests', {
      ...form, units: parseInt(form.units), lat: parseFloat(form.lat), lng: parseFloat(form.lng)
    });
    if (res.id) {
      setRequests(rs => [res, ...rs]);
      setShowForm(false);
      toast(`🚨 Request created! ${res.matched_donors?.length || 0} donors notified.`, 'success', 7000);
      setForm(f => ({...f, blood_group:'O+', units:'1', urgency:'high', description:''}));
    } else {
      toast(res.error || 'Error creating request', 'error');
    }
  };

  const closeRequest = async (id) => {
    const res = await api.patch(`/api/requests/${id}/status`, { status: 'closed' });
    if (!res.error) { setRequests(rs => rs.map(r => r.id === id ? {...r, status:'closed'} : r)); toast('Request closed.', 'info'); }
  };

  const pending   = requests.filter(r => r.status === 'pending');
  const matched   = requests.filter(r => r.status === 'matched');
  const closed    = requests.filter(r => r.status === 'closed');

  const tabs = [
    { id:'requests', icon:'🚨', label:'Live Requests' },
    { id:'create',   icon:'➕', label:'New Request'   },
    { id:'history',  icon:'📋', label:'History'       },
  ];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div style={{padding:'16px 20px 8px',fontSize:'11px',fontWeight:'700',letterSpacing:'1.5px',textTransform:'uppercase',color:'var(--dim)'}}>Hospital Portal</div>
        {tabs.map(t => (
          <div key={t.id} className={`sidebar-item ${tab===t.id?'active':''}`} onClick={() => setTab(t.id)}>
            <span className="sidebar-icon">{t.icon}</span>{t.label}
          </div>
        ))}
        <div style={{flex:1}}/>
        <div style={{padding:'16px 20px',borderTop:'1px solid var(--border2)',fontSize:'12px',color:'var(--muted)'}}>
          <div style={{marginBottom:'4px',fontWeight:'600',color:'var(--text)'}}>{user.name}</div>
          <div>{user.email}</div>
        </div>
      </aside>

      <main className="main">
        {/* Stats */}
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))',gap:'16px',marginBottom:'24px'}}>
          {[
            { icon:'📋', num: requests.length, label:'Total Requests',  color:'var(--blue)'   },
            { icon:'⏳', num: pending.length,   label:'Pending',         color:'var(--yellow)' },
            { icon:'✅', num: matched.length,   label:'Matched',         color:'var(--green)'  },
            { icon:'🔒', num: closed.length,    label:'Closed',          color:'var(--muted)'  },
          ].map((s,i) => (
            <div key={i} className="stat-card">
              <div className="stat-icon" style={{background:`${s.color}20`}}>{s.icon}</div>
              <div className="stat-num" style={{color:s.color}}>{s.num}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        {tab === 'requests' && (
          <div className="anim-fade">
            <div className="section-hdr">
              <div className="section-hdr-title">Live Requests</div>
              <button className="btn btn-primary btn-sm" onClick={() => setTab('create')}>+ New Request</button>
            </div>
            {loading ? <div className="page-loader"><div className="spinner"/></div> :
              requests.length === 0 ? (
                <div className="empty">
                  <span className="empty-icon">📭</span>
                  <span className="empty-text">No requests yet. Create your first emergency request.</span>
                  <button className="btn btn-primary" onClick={() => setTab('create')}>Create Request</button>
                </div>
              ) : requests.map(r => (
                <HospitalRequestCard key={r.id} req={r} onClose={closeRequest} onSelect={setSelectedReq} />
              ))
            }
          </div>
        )}

        {tab === 'create' && (
          <div className="anim-fade">
            <div className="section-hdr"><div className="section-hdr-title">Create Emergency Request</div></div>
            <div className="card" style={{maxWidth:'640px'}}>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'16px'}}>
                <div className="form-group">
                  <label>Blood Group *</label>
                  <select className="input" value={form.blood_group} onChange={e => setF('blood_group', e.target.value)}>
                    {bloodGroups.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Units Required *</label>
                  <input className="input" type="number" min="1" max="10" value={form.units} onChange={e => setF('units', e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Urgency Level *</label>
                  <select className="input" value={form.urgency} onChange={e => setF('urgency', e.target.value)}>
                    <option value="critical">🚨 Critical</option>
                    <option value="high">⚠️ High</option>
                    <option value="medium">🔵 Medium</option>
                    <option value="low">🟢 Low</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Hospital Name *</label>
                  <input className="input" value={form.hospital_name} onChange={e => setF('hospital_name', e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Latitude</label>
                  <input className="input" type="number" step="0.0001" value={form.lat} onChange={e => setF('lat', e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Longitude</label>
                  <input className="input" type="number" step="0.0001" value={form.lng} onChange={e => setF('lng', e.target.value)} />
                </div>
              </div>
              <div className="form-group">
                <label>Description</label>
                <input className="input" placeholder="Additional details about the request..." value={form.description} onChange={e => setF('description', e.target.value)} />
              </div>
              <div style={{background:'var(--s2)',borderRadius:'var(--r-md)',padding:'14px',marginBottom:'20px',fontSize:'13px',color:'var(--muted)',lineHeight:'1.6'}}>
                <strong style={{color:'var(--text)'}}>🤖 AI Matching:</strong> When you submit, our algorithm will instantly find compatible donors within 50km, ranked by match score (distance + availability + donation history).
              </div>
              <div className="flex gap-2">
                <button className="btn btn-primary" onClick={createRequest}>🚨 Create & Notify Donors</button>
                <button className="btn btn-ghost" onClick={() => setTab('requests')}>Cancel</button>
              </div>
            </div>
          </div>
        )}

        {tab === 'history' && (
          <div className="anim-fade">
            <div className="section-hdr"><div className="section-hdr-title">Request History</div></div>
            {closed.length === 0 ? (
              <div className="empty"><span className="empty-icon">📋</span><span className="empty-text">No closed requests yet.</span></div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr>
                    <th>Blood</th><th>Units</th><th>Urgency</th><th>Matched</th><th>Status</th><th>Created</th>
                  </tr></thead>
                  <tbody>
                    {[...requests].reverse().map(r => (
                      <tr key={r.id}>
                        <td><span className="blood-badge" style={{width:'32px',height:'32px',fontSize:'10px'}}>{r.blood_group}</span></td>
                        <td>{r.units}</td>
                        <td><span className={`badge badge-${urgencyColor(r.urgency)}`}>{r.urgency}</span></td>
                        <td>{r.accepted_donors?.length || 0}/{r.units}</td>
                        <td><span className={`badge badge-${statusColor(r.status)}`}>{r.status}</span></td>
                        <td style={{color:'var(--muted)'}}>{relTime(r.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      {selectedReq && (
        <div className="modal-bg" onClick={() => setSelectedReq(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">Request Details</div>
              <span className="modal-close" onClick={() => setSelectedReq(null)}>✕</span>
            </div>
            <RequestDetailModal req={selectedReq} />
          </div>
        </div>
      )}
    </div>
  );
}

function HospitalRequestCard({ req, onClose, onSelect }) {
  return (
    <div className={`req-card ${req.urgency} mb-3`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex gap-2 items-center">
          <span>{urgencyEmoji(req.urgency)}</span>
          <span className={`badge badge-${urgencyColor(req.urgency)}`}>{req.urgency.toUpperCase()}</span>
          <div className="blood-badge" style={{width:'32px',height:'32px',fontSize:'10px'}}>{req.blood_group}</div>
        </div>
        <div className="flex gap-2 items-center">
          <span className={`badge badge-${statusColor(req.status)}`}>{req.status}</span>
          {req.status !== 'closed' && <button className="btn btn-ghost btn-sm" onClick={() => onClose(req.id)}>Close</button>}
        </div>
      </div>

      <div style={{fontWeight:'700',fontSize:'16px',marginBottom:'4px'}}>{req.hospital_name}</div>
      <div style={{fontSize:'13px',color:'var(--muted)',marginBottom:'12px'}}>
        {req.blood_group} • {req.units} unit(s) needed • {relTime(req.created_at)}
        {req.description && ` • "${req.description}"`}
      </div>

      {/* Accepted donors */}
      {req.accepted_donors?.length > 0 && (
        <div style={{background:'rgba(46,204,113,.08)',border:'1px solid rgba(46,204,113,.2)',borderRadius:'var(--r-md)',padding:'12px',marginBottom:'12px'}}>
          <div style={{fontSize:'12px',fontWeight:'700',color:'var(--green)',marginBottom:'8px'}}>
            ✅ {req.accepted_donors.length}/{req.units} Donor(s) Accepted
          </div>
          {req.accepted_donors.map((d,i) => (
            <div key={i} style={{fontSize:'13px',color:'var(--text)',display:'flex',gap:'8px',alignItems:'center',marginTop:'4px'}}>
              <span>👤</span><span>{d.name}</span>
              <span className="badge badge-red" style={{fontSize:'10px'}}>{d.blood_group}</span>
              {d.phone && <span style={{color:'var(--muted)',fontSize:'12px'}}>{d.phone}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Progress */}
      <div style={{marginBottom:'12px'}}>
        <div className="flex justify-between mb-1" style={{fontSize:'12px',color:'var(--muted)'}}>
          <span>Donor Response</span>
          <span>{req.accepted_donors?.length || 0}/{req.units} accepted</span>
        </div>
        <div className="progress-wrap">
          <div className="progress-bar" style={{
            width: `${Math.min(100, ((req.accepted_donors?.length||0)/req.units)*100)}%`,
            background: req.status === 'matched' ? 'var(--green)' : 'var(--red)'
          }}/>
        </div>
      </div>

      <div className="flex gap-2">
        <button className="btn btn-ghost btn-sm" onClick={() => onSelect(req)}>
          👁 View {req.matched_donors?.length || 0} Matched Donors
        </button>
      </div>
    </div>
  );
}

function RequestDetailModal({ req }) {
  return (
    <div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'12px',marginBottom:'20px'}}>
        {[
          ['Blood Group', req.blood_group],
          ['Units', req.units],
          ['Urgency', req.urgency],
          ['Status', req.status],
          ['Hospital', req.hospital_name],
          ['Created', relTime(req.created_at)],
        ].map(([k,v]) => (
          <div key={k} style={{background:'var(--s2)',borderRadius:'var(--r-sm)',padding:'12px'}}>
            <div style={{fontSize:'11px',color:'var(--dim)',marginBottom:'3px',letterSpacing:'.8px',textTransform:'uppercase'}}>{k}</div>
            <div style={{fontSize:'14px',fontWeight:'600'}}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{marginBottom:'16px',fontWeight:'700',fontSize:'14px'}}>
        Matched Donors ({req.matched_donors?.length || 0})
      </div>
      {(req.matched_donors || []).slice(0,8).map((d,i) => (
        <div key={i} className="donor-card mb-2">
          <div style={{width:'36px',height:'36px',borderRadius:'50%',background:'var(--s4)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:'14px'}}>
            {String.fromCodePoint(0x1F464)}
          </div>
          <div style={{flex:1}}>
            <div style={{fontWeight:'600',fontSize:'14px',marginBottom:'2px'}}>{d.name}</div>
            <div style={{fontSize:'12px',color:'var(--muted)',display:'flex',gap:'8px'}}>
              <span>📍 {d.distance_km} km</span>
              <span>💉 {d.total_donations} donations</span>
              {d.response && <span className={`badge badge-${d.response==='accept'?'green':'muted'}`} style={{padding:'0 6px',fontSize:'10px'}}>{d.response}</span>}
            </div>
            <div className="score-bar mt-1"><div className="score-fill" style={{width:`${d.match_score}%`}}/></div>
          </div>
          <div style={{textAlign:'right'}}>
            <div className="blood-badge" style={{width:'32px',height:'32px',fontSize:'10px'}}>{d.blood_group}</div>
            <div style={{fontSize:'11px',color:'var(--muted)',marginTop:'4px'}}>{d.match_score}%</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ADMIN DASHBOARD
// ═══════════════════════════════════════════════════════════════
function AdminDashboard({ user }) {
  const [tab, setTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [reqs, setReqs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    const [sRes, uRes, rRes] = await Promise.all([
      api.get('/api/admin/stats'),
      api.get('/api/admin/users'),
      api.get('/api/admin/requests'),
    ]);
    if (!sRes.error) setStats(sRes);
    if (Array.isArray(uRes)) setUsers(uRes);
    if (Array.isArray(rRes)) setReqs(rRes);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const toggleUser = async (uid) => {
    const res = await api.patch(`/api/admin/users/${uid}/toggle`);
    if (res.id) {
      setUsers(us => us.map(u => u.id === uid ? { ...u, is_active: res.is_active } : u));
      toast(res.is_active ? 'User activated' : 'User deactivated', 'info');
    }
  };

  const tabs = [
    { id:'overview',  icon:'📊', label:'Overview'  },
    { id:'users',     icon:'👥', label:'Users'      },
    { id:'requests',  icon:'🚨', label:'Requests'   },
    { id:'logs',      icon:'📋', label:'System Logs'},
  ];

  const filteredUsers = users.filter(u =>
    !search || u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.role.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="layout">
      <aside className="sidebar">
        <div style={{padding:'16px 20px 8px',fontSize:'11px',fontWeight:'700',letterSpacing:'1.5px',textTransform:'uppercase',color:'var(--dim)'}}>Admin Panel</div>
        {tabs.map(t => (
          <div key={t.id} className={`sidebar-item ${tab===t.id?'active':''}`} onClick={() => setTab(t.id)}>
            <span className="sidebar-icon">{t.icon}</span>{t.label}
          </div>
        ))}
        <div style={{flex:1}}/>
        <div style={{padding:'16px 20px',borderTop:'1px solid var(--border2)'}}>
          <button className="btn btn-ghost btn-sm w-full" onClick={load}>🔄 Refresh</button>
        </div>
      </aside>

      <main className="main">
        {loading && !stats ? (
          <div className="page-loader"><div className="spinner"/></div>
        ) : (
          <>
            {tab === 'overview' && stats && (
              <div className="anim-fade">
                <div className="section-hdr"><div className="section-hdr-title">System Overview</div><span className="flex items-center gap-2"><div className="live-dot"/><span style={{fontSize:'12px',color:'var(--green)'}}>Live</span></span></div>

                <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))',gap:'16px',marginBottom:'28px'}}>
                  {[
                    { icon:'👥', num: stats.users,              label:'Total Users',      color:'var(--blue)'   },
                    { icon:'🩸', num: stats.donors,             label:'Registered Donors',color:'var(--red)'    },
                    { icon:'✅', num: stats.available_donors,   label:'Available Now',    color:'var(--green)'  },
                    { icon:'📋', num: stats.total_requests,     label:'Total Requests',   color:'var(--yellow)' },
                    { icon:'⏳', num: stats.pending,            label:'Pending',          color:'var(--orange)' },
                    { icon:'🎯', num: `${stats.fulfillment_rate}%`, label:'Fulfillment Rate',color:'var(--green)'  },
                  ].map((s,i) => (
                    <div key={i} className={`stat-card anim-up anim-d${Math.min(i+1,5)}`}>
                      <div className="stat-icon" style={{background:`${s.color}20`}}>{s.icon}</div>
                      <div className="stat-num" style={{color:s.color,fontSize:'32px'}}>{s.num}</div>
                      <div className="stat-label">{s.label}</div>
                    </div>
                  ))}
                </div>

                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'20px'}}>
                  {/* Blood Group Distribution */}
                  <div className="card">
                    <div style={{fontWeight:'700',marginBottom:'20px',fontSize:'14px',letterSpacing:'.5px'}}>🩸 Blood Group Distribution</div>
                    <div className="bar-chart">
                      {Object.entries(stats.blood_group_stats||{}).sort((a,b)=>b[1]-a[1]).map(([bg,count]) => {
                        const max = Math.max(...Object.values(stats.blood_group_stats));
                        return (
                          <div key={bg} className="bar-row">
                            <span className="bar-label">{bg}</span>
                            <div className="bar-wrap">
                              <div className="bar-fill" style={{width:`${(count/max)*100}%`}}/>
                            </div>
                            <span className="bar-count">{count}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Request Status */}
                  <div className="card">
                    <div style={{fontWeight:'700',marginBottom:'20px',fontSize:'14px',letterSpacing:'.5px'}}>📊 Request Analytics</div>
                    {[
                      { label:'Pending',  val: stats.pending,  color:'var(--yellow)', icon:'⏳' },
                      { label:'Matched',  val: stats.matched,  color:'var(--green)',  icon:'✅' },
                      { label:'Closed',   val: stats.closed,   color:'var(--muted)',  icon:'🔒' },
                    ].map(s => (
                      <div key={s.label} style={{display:'flex',alignItems:'center',gap:'12px',marginBottom:'14px'}}>
                        <span style={{fontSize:'16px'}}>{s.icon}</span>
                        <span style={{width:'70px',fontSize:'13px',color:'var(--muted)'}}>{s.label}</span>
                        <div style={{flex:1,height:'12px',background:'var(--s3)',borderRadius:'6px',overflow:'hidden'}}>
                          <div style={{height:'100%',borderRadius:'6px',background:s.color,width:`${stats.total_requests?((s.val/stats.total_requests)*100):0}%`,transition:'width 1s'}}/>
                        </div>
                        <span style={{fontFamily:'var(--font-m)',fontSize:'13px',width:'24px',textAlign:'right'}}>{s.val}</span>
                      </div>
                    ))}
                    <div style={{marginTop:'16px',paddingTop:'16px',borderTop:'1px solid var(--border2)',display:'flex',gap:'20px'}}>
                      {[['🔔',stats.total_notifications,'Notifications'],['📋',stats.recent_logs?.length||0,'Log Entries']].map(([i,n,l]) => (
                        <div key={l}>
                          <div style={{fontSize:'11px',color:'var(--dim)',letterSpacing:'.8px',textTransform:'uppercase'}}>{i} {l}</div>
                          <div style={{fontFamily:'var(--font-m)',fontSize:'18px',fontWeight:'700',marginTop:'4px'}}>{n}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {tab === 'users' && (
              <div className="anim-fade">
                <div className="section-hdr">
                  <div className="section-hdr-title">User Management</div>
                  <span className="badge badge-muted">{users.length} total</span>
                </div>
                <div className="form-group" style={{marginBottom:'16px',maxWidth:'320px'}}>
                  <input className="input" placeholder="🔍 Search users..." value={search} onChange={e => setSearch(e.target.value)} />
                </div>
                <div className="table-wrap">
                  <table>
                    <thead><tr>
                      <th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Action</th>
                    </tr></thead>
                    <tbody>
                      {filteredUsers.map(u => (
                        <tr key={u.id}>
                          <td style={{fontWeight:'600'}}>{u.name}</td>
                          <td style={{color:'var(--muted)',fontFamily:'var(--font-m)',fontSize:'12px'}}>{u.email}</td>
                          <td><span className={`badge badge-${u.role==='admin'?'red':u.role==='donor'?'green':u.role==='hospital'?'blue':'muted'}`}>{u.role}</span></td>
                          <td><span className={`badge badge-${u.is_active?'green':'muted'}`}>{u.is_active?'Active':'Inactive'}</span></td>
                          <td style={{color:'var(--muted)',fontSize:'12px'}}>{relTime(u.created_at)}</td>
                          <td>
                            {u.role !== 'admin' && (
                              <button className={`btn btn-sm ${u.is_active ? 'btn-ghost' : 'btn-success'}`}
                                style={{padding:'4px 10px',fontSize:'11px'}} onClick={() => toggleUser(u.id)}>
                                {u.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {tab === 'requests' && (
              <div className="anim-fade">
                <div className="section-hdr">
                  <div className="section-hdr-title">All Blood Requests</div>
                  <span className="badge badge-muted">{reqs.length} total</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead><tr>
                      <th>Blood</th><th>Hospital</th><th>Units</th><th>Urgency</th><th>Matched</th><th>Accepted</th><th>Status</th><th>Created</th>
                    </tr></thead>
                    <tbody>
                      {reqs.map(r => (
                        <tr key={r.id}>
                          <td><span className="blood-badge" style={{width:'30px',height:'30px',fontSize:'10px'}}>{r.blood_group}</span></td>
                          <td style={{fontWeight:'600',maxWidth:'160px'}} className="truncate">{r.hospital_name}</td>
                          <td>{r.units}</td>
                          <td><span className={`badge badge-${urgencyColor(r.urgency)}`}>{r.urgency}</span></td>
                          <td style={{fontFamily:'var(--font-m)'}}>{r.matched_donors?.length||0}</td>
                          <td style={{fontFamily:'var(--font-m)',color:'var(--green)'}}>{r.accepted_donors?.length||0}</td>
                          <td><span className={`badge badge-${statusColor(r.status)}`}>{r.status}</span></td>
                          <td style={{color:'var(--muted)',fontSize:'12px'}}>{relTime(r.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {tab === 'logs' && stats && (
              <div className="anim-fade">
                <div className="section-hdr">
                  <div className="section-hdr-title">System Activity Logs</div>
                  <button className="btn btn-ghost btn-sm" onClick={load}>🔄 Refresh</button>
                </div>
                <div style={{display:'flex',flexDirection:'column',gap:'8px'}}>
                  {(stats.recent_logs||[]).slice().reverse().map((log,i) => (
                    <div key={i} style={{background:'var(--s2)',borderRadius:'var(--r-sm)',padding:'12px 16px',display:'flex',gap:'12px',alignItems:'center',borderLeft:'2px solid var(--border)'}}>
                      <span style={{fontSize:'18px'}}>
                        {log.action==='login'?'🔐':log.action==='register'?'🆕':log.action==='create_request'?'🚨':log.action==='donor_respond'?'✅':'📋'}
                      </span>
                      <div style={{flex:1}}>
                        <span style={{fontFamily:'var(--font-m)',fontSize:'12px',color:'var(--red-l)',fontWeight:'600'}}>{log.action}</span>
                        {log.details && <span style={{fontSize:'12px',color:'var(--muted)',marginLeft:'8px'}}>{JSON.stringify(log.details)}</span>}
                      </div>
                      <span style={{fontSize:'11px',color:'var(--dim)',fontFamily:'var(--font-m)'}}>{relTime(log.timestamp)}</span>
                    </div>
                  ))}
                  {(!stats.recent_logs || stats.recent_logs.length === 0) && (
                    <div className="empty"><span className="empty-icon">📋</span><span className="empty-text">No logs yet.</span></div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ROOT APP
// ═══════════════════════════════════════════════════════════════
function App() {
  const [user, setUser]         = useState(null);
  const [page, setPage]         = useState('landing');
  const [notifications, setNotifications] = useState([]);
  const [wsHandler, setWsHandler] = useState(null);
  const toast = useToast();

  // Restore session
  useEffect(() => {
    const token = localStorage.getItem('bb_token');
    if (token) {
      api.get('/api/auth/me').then(res => {
        if (!res.error) {
          setUser(res);
          setPage(res.role === 'admin' ? 'admin' : res.role === 'donor' ? 'donor' : res.role === 'hospital' ? 'hospital' : 'hospital');
          loadNotifications();
        }
      }).catch(() => {});
    }
  }, []);

  const loadNotifications = async () => {
    const res = await api.get('/api/notifications');
    if (Array.isArray(res)) setNotifications(res);
  };

  // Socket events
  const onSocketEvent = useCallback((ev, data) => {
    if (ev === 'new_request') {
      loadNotifications();
      if (wsHandler) wsHandler(ev, data);
    }
    if (ev === 'donor_accepted') {
      loadNotifications();
      if (window._bbHospitalHandler) window._bbHospitalHandler(ev, data);
      if (wsHandler) wsHandler(ev, data);
    }
    if (['request_created','request_updated'].includes(ev)) {
      if (window._bbHospitalHandler) window._bbHospitalHandler(ev, data);
      if (wsHandler) wsHandler(ev, data);
    }
  }, [wsHandler]);

  useSocket(user, onSocketEvent);

  const handleLogin = (u) => {
    setUser(u);
    setPage(u.role === 'admin' ? 'admin' : u.role === 'donor' ? 'donor' : 'hospital');
    loadNotifications();
  };

  const handleLogout = () => {
    localStorage.removeItem('bb_token');
    setUser(null);
    setPage('landing');
    setNotifications([]);
    toast('Logged out. See you soon! 👋', 'info');
  };

  return (
    <div className="app">
      <Navbar user={user} onLogout={handleLogout} onNav={setPage} notifications={notifications} />
      {page === 'landing' && <LandingPage onNav={setPage} />}
      {page === 'auth'    && <AuthPage onLogin={handleLogin} />}
      {page === 'donor'   && user && <DonorDashboard user={user} onSocketEvent={cb => setWsHandler(() => cb)} />}
      {page === 'hospital'&& user && <HospitalDashboard user={user} />}
      {page === 'admin'   && user && <AdminDashboard user={user} />}
      {!user && page !== 'landing' && page !== 'auth' && <AuthPage onLogin={handleLogin} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MOUNT
// ═══════════════════════════════════════════════════════════════
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <ToastProvider>
    <App />
  </ToastProvider>
);
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return Response(FRONTEND, mimetype='text/html')

# Health check
@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'BloodBridge AI',
        'users': len(db.users),
        'donors': len(db.donors),
        'requests': len(db.blood_requests),
        'timestamp': _now()
    }), 200

# ─────────────────────────────────────────────────────────────────
# STARTUP - Production Ready Server
# ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Use eventlet for better WebSocket support
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        pass
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║   🩸 BloodBridge AI — Emergency Blood Donor Matching System      ║
╠══════════════════════════════════════════════════════════════════╣
║  Server:    http://localhost:5000                                 ║
║  Health:    http://localhost:5000/api/health                     ║
╠══════════════════════════════════════════════════════════════════╣
║  DEMO LOGINS:                                                    ║
║    Admin:    admin@bloodbridge.org  / admin123                   ║
║    Donor:    alice@donor.com        / pass123   (O+)             ║
║    Hospital: hospital@citygeneral.com / hosp123                  ║
║    Patient:  patient@example.com    / patient123                 ║
╚══════════════════════════════════════════════════════════════════╝
""")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)