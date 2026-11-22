#!/bin/sh
# AegisSOC S1-T12a - runs ONCE, on first initialisation of an empty data
# directory, as the `postgres` superuser (docker-entrypoint-initdb.d).
# Spec: docs/sprints/SPRINT_01.md S1-T04, docs/DATABASE_DESIGN.md section 6.
#
# Creates aegis_owner (migrations) and aegis_app (api/worker), the database
# `aegissoc` owned by aegis_owner, and tightens schema public (SR-27).
# Passwords come only from Docker secret files. They are read by psql itself
# (\set with backticks) so they never appear in this script's arguments or
# environment, and are never echoed.
set -eu

secrets=/run/secrets
for f in postgres_owner_password postgres_app_password; do
  if [ ! -s "$secrets/$f" ]; then
    echo "01-roles: missing or empty secret $f" >&2
    exit 1
  fi
done

psql -X -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<'SQL'
\set owner_pw `cat /run/secrets/postgres_owner_password`
\set app_pw `cat /run/secrets/postgres_app_password`

CREATE ROLE aegis_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'owner_pw';
CREATE ROLE aegis_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'app_pw';

CREATE DATABASE aegissoc OWNER aegis_owner;

\connect aegissoc
ALTER SCHEMA public OWNER TO aegis_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL

echo "01-roles: roles aegis_owner, aegis_app and database aegissoc created"
