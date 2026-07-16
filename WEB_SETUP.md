# Web Frontend Setup Guide

## Problem Solved: Backend Proxy Connection Error

### The Issue
```
Failed to proxy http://localhost:8000/api/auth/login Error: connect ECONNREFUSED 127.0.0.1:8000
```

**Root Cause**: Next.js frontend (WSL) trying to connect to backend (GCP VM) via `localhost:8000`, but no SSH tunnel was forwarding the port.

### Architecture
```
GCP VM (34.50.83.29)
├─ FastAPI Backend :8000 ✓
├─ PostgreSQL :5432 ✓
└─ Docker Compose

    ↑ SSH Tunnel (8000:localhost:8000)
    
WSL 2 Local Machine
├─ Next.js Frontend :3000
└─ SSH Tunnel Endpoint :8000
```

---

## Quick Start

### One-Command Setup (Recommended)
```bash
cd /home/iqbal/my-project/stock-engine-prediction-v2
make web-frontend-dev-with-tunnel
```

This automatically:
1. ✓ Checks SSH tunnel status
2. ✓ Starts tunnel if needed
3. ✓ Starts Next.js dev server
4. ✓ Opens http://localhost:3000

### Manual Setup

**Terminal 1: Start SSH Tunnel**
```bash
make ssh-tunnel
# or: ssh -L 8000:localhost:8000 gcp-vm-hamboo -N -f
```

**Terminal 2: Start Next.js**
```bash
cd web-frontend
npm install
npm run dev
```

---

## Makefile Commands

| Command | Purpose |
|---------|---------|
| `make ssh-tunnel` | Start SSH port forwarding (8000→VM) |
| `make ssh-tunnel-check` | Verify tunnel is running |
| `make ssh-tunnel-stop` | Stop SSH tunnel |
| `make web-frontend-dev-with-tunnel` | Auto-setup tunnel + start Next.js |
| `make web-tunnel-status` | Show tunnel/app/backend status |
| `make web-frontend-stop` | Stop Next.js server |

---

## Troubleshooting

### "Connection refused" on localhost:8000
```bash
make ssh-tunnel-check
# If not running:
make ssh-tunnel
```

### Next.js not responding
```bash
# Kill and restart
make web-frontend-stop
npm run dev
```

### SSH tunnel disconnected (timeout)
```bash
make ssh-tunnel-stop
make ssh-tunnel
```

### Check all services
```bash
make web-tunnel-status
```

---

## Configuration

### Environment Variables
- `BACKEND_URL`: API base URL (default: `http://localhost:8000`)
- `NEXT_PUBLIC_BACKEND_URL`: Public backend URL

### API Rewrites
See [next.config.ts](web-frontend/next.config.ts):
```typescript
rewrites() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL 
    ?? process.env.BACKEND_URL 
    ?? "http://localhost:8000";
  return [
    { source: "/api/:path*", destination: `${backendUrl}/api/:path*` }
  ];
}
```

---

## How It Works

1. **Browser Request**: `http://localhost:3000/api/auth/login`
2. **Next.js Proxy** (via next.config.ts): Rewrites to `http://localhost:8000/api/auth/login`
3. **SSH Tunnel**: `localhost:8000` → `gcp-vm-hamboo:8000` (via SSH)
4. **Backend**: Responds with JWT token
5. **Next.js**: Returns response to browser

---

## Development Workflow

### Start Everything
```bash
make web-frontend-dev-with-tunnel
```

### Code Editing
- Edit files in `web-frontend/app/` or `web-frontend/components/`
- Next.js auto-reloads on save
- Visit `http://localhost:3000`

### Test Login
```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Kikan","password":"password123"}'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "tier": "pro",
  "user_id": 4
}
```

---

## Production Build

```bash
# Build optimized bundle
npm run build

# Test production build locally
npm start

# Will be available at http://localhost:3000
```

---

## SSH Configuration

Requires `~/.ssh/config`:
```
Host gcp-vm-hamboo
    HostName 34.50.83.29
    User hamboo
    IdentityFile ~/.ssh/gcp_key
```

And SSH key at `~/.ssh/gcp_key` with proper permissions (600).

---

## Related Files

- [web-frontend/README.md](web-frontend/README.md) - Frontend setup
- [web-frontend/next.config.ts](web-frontend/next.config.ts) - API proxy config
- [Makefile](Makefile) - Build commands (lines 88-130)
- Main docs: [README.md](README.md)
