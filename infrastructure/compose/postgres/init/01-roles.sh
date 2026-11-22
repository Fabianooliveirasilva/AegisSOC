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
-- Never let a failing password statement reach the server log (SEC-03):
-- no statement text on errors, no statement logging, terse client errors.
SET log_min_error_statement = panic;
SET log_statement = none;
\set VERBOSITY terse
\set owner_pw `cat /run/secrets/postgres_owner_password`
\set app_pw `cat /run/secrets/postgres_app_password`

CREATE ROLE aegis_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'owner_pw';
CREATE ROLE aegis_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  PASSWORD :'app_pw';

CREATE DATABASE aegissoc OWNER aegis_owner;

-- Only the two application roles may connect (SR-27, SEC-06). Superusers are
-- unaffected. statement_timeout is deliberately left to S1-T04.
REVOKE CONNECT ON DATABASE aegissoc FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
GRANT CONNECT ON DATABASE aegissoc TO aegis_owner, aegis_app;

\connect aegissoc
ALTER SCHEMA public OWNER TO aegis_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SQL

echo "01-roles: roles aegis_owner, aegis_app and database aegissoc created"
