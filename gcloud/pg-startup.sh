#!/bin/bash
set -e
exec > >(tee -a /var/log/pg-setup.log) 2>&1

# Install PostgreSQL 18 from official repo
apt-get update
apt-get install -y gnupg2 lsb-release
echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
apt-get update
apt-get install -y postgresql-18

PG_CONF="/etc/postgresql/18/main/postgresql.conf"
PG_HBA="/etc/postgresql/18/main/pg_hba.conf"

# Listen on all interfaces
sed -i "s/^#\?listen_addresses\s*=.*/listen_addresses = '*'/" $PG_CONF

# Enable SSL with self-signed cert
sudo -u postgres openssl req -new -x509 -days 3650 -nodes \
  -out /etc/postgresql/18/main/server.crt \
  -keyout /etc/postgresql/18/main/server.key \
  -subj "/CN=multimodal-scout-db"
chmod 600 /etc/postgresql/18/main/server.key
chown postgres:postgres /etc/postgresql/18/main/server.key /etc/postgresql/18/main/server.crt
sed -i "s/^#\?ssl\s*=.*/ssl = on/" $PG_CONF

# Allow SSL password auth from any IP (firewall handles network restriction)
echo "hostssl all all 0.0.0.0/0 scram-sha-256" >> $PG_HBA

# Tune for e2-micro (0.25 vCPU, 1GB RAM)
echo "" >> $PG_CONF
echo "# e2-micro tuning" >> $PG_CONF
echo "shared_buffers = 128MB" >> $PG_CONF
echo "effective_cache_size = 512MB" >> $PG_CONF
echo "work_mem = 4MB" >> $PG_CONF
echo "maintenance_work_mem = 64MB" >> $PG_CONF
echo "max_connections = 20" >> $PG_CONF

systemctl restart postgresql
echo "=== PostgreSQL 18 Setup Complete ==="
