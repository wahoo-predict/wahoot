# Docker Setup for Local Net Testing

## Permission Issues

If you see `permission denied while trying to connect to the docker API`, you have two options:

### Option 1: Fix Permissions (Recommended)

Add your user to the docker group:

```bash
cd ~/wahoonet
./fix_docker_permissions.sh
```

Then **log out and log back in** (or run `newgrp docker`).

After that, you can run docker commands without sudo.

### Option 2: Use Sudo (Quick Fix)

The `start_local_chain.sh` script will automatically try sudo if regular docker fails.

Or manually run with sudo:

```bash
sudo docker ps -a
sudo ./start_local_chain.sh
```

## Verify Docker Access

```bash
# Should work without sudo after fixing permissions
docker ps

# Or with sudo
sudo docker ps
```

## Start Local Chain

After fixing permissions:

```bash
cd ~/wahoonet
./start_local_chain.sh
```

## Check Container Status

```bash
# Without sudo (after fixing permissions)
docker ps | grep local_chain

# Or with sudo
sudo docker ps | grep local_chain
```

## View Logs

```bash
docker logs -f local_chain
# Or with sudo:
sudo docker logs -f local_chain
```

