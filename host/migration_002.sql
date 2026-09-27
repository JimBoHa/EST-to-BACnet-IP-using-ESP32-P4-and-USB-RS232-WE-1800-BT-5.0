BEGIN IMMEDIATE;
ALTER TABLE events ADD COLUMN observed REAL;
UPDATE events SET observed=received;
PRAGMA user_version=2;
COMMIT;
