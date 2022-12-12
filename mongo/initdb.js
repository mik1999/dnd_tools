print('MongoDB: start initializing');

db = db.getSiblingDB('dnd');

db.createCollection('user_potions');

db.user_potions.createIndex( { 'name': 1, 'user': 1}, { unique: true } );

print('MongoDB: finished initializing');
