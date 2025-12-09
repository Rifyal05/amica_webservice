SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'nama_db' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS nama_db;
DROP ROLE IF EXISTS username;

CREATE ROLE username WITH LOGIN PASSWORD 'password';

CREATE DATABASE amica_db OWNER username;