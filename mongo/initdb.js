print('MongoDB: start initializing');

db = db.getSiblingDB('dnd');

db.createCollection('user_potions');
db.user_potions.createIndex( { 'name': 1, 'user': 1}, { unique: true } );

db.createCollection('user_npcs');
db.user_npcs.createIndex( { 'name': 1, 'user': 1}, { unique: true } );
db.user_npcs.createIndex({'name': 'text'});

db.createCollection('user_npc_notes');

db.createCollection('resources_usage');

db.createCollection('user_info');

db.createCollection('games');

print('MongoDB: finished initializing');
