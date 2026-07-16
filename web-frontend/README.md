# Web Frontend - Stock Agent IDX

This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Architecture

- **Frontend**: Next.js 15+ with TypeScript
- **Backend**: FastAPI running on GCP VM (port 8000)
- **Proxy**: Next.js rewrites API calls via SSH tunnel
- **Authentication**: JWT-based with auth context

## Getting Started

### Prerequisites

- Node.js 18+
- SSH access to `gcp-vm-hamboo` (configured in `~/.ssh/config`)
- Backend running on VM (port 8000)

### Quick Start (Recommended)

Use the Makefile commands from the project root:

```bash
# Start both SSH tunnel and Next.js dev server
make web-frontend-dev-with-tunnel
```

This will:
1. Check and start SSH tunnel if not running
2. Start Next.js dev server on `http://localhost:3000`
3. Auto-proxy API calls to backend via SSH tunnel

### Manual Setup

If you prefer to manage SSH tunnel and Next.js separately:

**Terminal 1 - Start SSH tunnel:**
```bash
make ssh-tunnel
# or manually:
ssh -L 8000:localhost:8000 gcp-vm-hamboo -N -f
```

**Terminal 2 - Start Next.js:**
```bash
cd web-frontend
npm install
npm run dev
```

## Usage

### Development

```bash
# Run dev server with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### SSH Tunnel Management

```bash
# Check tunnel status
make ssh-tunnel-check

# Check all services (tunnel, Next.js, backend)
make web-tunnel-status

# Stop tunnel
make ssh-tunnel-stop
```

### Environment Variables

- `BACKEND_URL`: Backend API base URL (defaults to `http://localhost:8000`)
- `NEXT_PUBLIC_BACKEND_URL`: Public-facing backend URL

## Troubleshooting

### "Connection refused" on localhost:8000

The SSH tunnel isn't running. Start it with:
```bash
make ssh-tunnel
# or
ssh -L 8000:localhost:8000 gcp-vm-hamboo -N -f
```

### Next.js won't start

Kill existing Next.js process and restart:
```bash
make web-frontend-stop
npm run dev
```

### SSH tunnel keeps disconnecting

Try reconnecting:
```bash
make ssh-tunnel-stop
make ssh-tunnel
```

### Backend returns 500 error

Backend might have connection issues to PostgreSQL on VM. Check backend logs on VM.

## Project Structure

```
web-frontend/
├── app/                 # Next.js app directory
├── components/          # React components
├── lib/                 # Utilities and API client
├── styles/              # CSS modules
├── public/              # Static assets
├── next.config.ts       # Next.js config with API rewrites
└── package.json         # Dependencies
```

## API Proxy Configuration

See [next.config.ts](./next.config.ts) for proxy rewrites:
- `/api/auth/*` → Backend `/api/auth/*`
- `/api/*` → Backend `/api/*`

All API calls go through the SSH tunnel to the VM backend.

## Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Learn Next.js](https://nextjs.org/learn)
- Project docs: [README.md](../README.md)
