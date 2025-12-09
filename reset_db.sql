SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'amica_db' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS amica_db;
DROP ROLE IF EXISTS nama_role;

CREATE ROLE nama_role WITH LOGIN PASSWORD 'passwordnya';

CREATE DATABASE amica_db OWNER nama_role;