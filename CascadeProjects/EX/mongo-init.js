// MongoDB initialization script for BloodBridge AI
db = db.getSiblingDB('bloodbridge');

// Create collections and indexes
db.createCollection('users');
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ role: 1 });

db.createCollection('donors');
db.donors.createIndex({ user_id: 1 });
db.donors.createIndex({ blood_group: 1 });
db.donors.createIndex({ availability: 1 });
db.donors.createIndex({ location: "2dsphere" });

db.createCollection('blood_requests');
db.blood_requests.createIndex({ requester_id: 1 });
db.blood_requests.createIndex({ blood_group: 1 });
db.blood_requests.createIndex({ status: 1 });
db.blood_requests.createIndex({ created_at: -1 });
db.blood_requests.createIndex({ location: "2dsphere" });

db.createCollection('notifications');
db.notifications.createIndex({ user_id: 1 });
db.notifications.createIndex({ created_at: -1 });

db.createCollection('logs');
db.logs.createIndex({ timestamp: -1 });
db.logs.createIndex({ user_id: 1 });
db.logs.createIndex({ action: 1 });

print('BloodBridge AI database initialized successfully');
