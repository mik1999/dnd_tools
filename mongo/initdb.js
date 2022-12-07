print('MongoDB: start initializing');

db = db.getSiblingDB('dnd');

db.createCollection('user_potions');

db.user_potions.createIndex( { name: 'text', user: 'text'}, { unique: true } );

print('MongoDB: finished initializing');
