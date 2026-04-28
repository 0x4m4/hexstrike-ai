-- Create role if missing (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'clair') THEN
    CREATE ROLE clair WITH LOGIN PASSWORD 'clair';
  END IF;
END$$;

-- Create database if missing (must be outside a transaction)
SELECT 'CREATE DATABASE clair OWNER clair'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'clair') \gexec
