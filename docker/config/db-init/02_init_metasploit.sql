-- Create role if missing (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'msf') THEN
    CREATE ROLE msf WITH LOGIN PASSWORD 'msf';
  END IF;
END$$;

-- Create database if missing (must be outside a transaction)
SELECT 'CREATE DATABASE msf OWNER msf'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'msf') \gexec
