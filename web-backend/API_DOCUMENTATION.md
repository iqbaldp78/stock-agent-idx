# Hamboo AI Stock Trading API Documentation

## Overview

This directory contains complete API documentation for the Hamboo AI Stock Trading system:
- **openapi.yaml** - OpenAPI 3.0 specification (Swagger)
- **Hamboo_AI_API.postman_collection.json** - Postman collection for API testing

## Quick Start

### 1. Swagger/OpenAPI Documentation

The OpenAPI specification can be viewed using any Swagger viewer:

#### Option A: SwaggerUI (Online)
```bash
# Visit https://editor.swagger.io/
# Then: File -> Import URL
# Paste your local file path or host it on a server
```

#### Option B: Local Swagger UI (Docker)
```bash
docker run -p 8080:8080 -e SWAGGER_JSON=/openapi.yaml \
  -v $(pwd)/openapi.yaml:/openapi.yaml \
  swaggerapi/swagger-ui
```

Visit: http://localhost:8080

#### Option C: VS Code Extension
Install "OpenAPI (Swagger) Editor" extension in VS Code and open `openapi.yaml` directly.

### 2. Postman Collection

#### Import the Collection
1. Open Postman
2. Click "Import" button
3. Select "Upload Files"
4. Choose `Hamboo_AI_API.postman_collection.json`

#### Setup Environment Variables
1. Create a new Environment in Postman
2. Add variables:
   - `base_url` = `http://localhost:8000` (or your API server)
   - `token` = *(leave empty initially)*

#### Get Authentication Token
1. First, register a new user:
   - POST `/api/auth/register`
   - Body: `{"username": "testuser", "password": "testpass"}`
   
2. Or login with existing user:
   - POST `/api/auth/login`
   - Body: `{"username": "testuser", "password": "testpass"}`
   - Copy the `access_token` from response

3. Set the token in Postman environment:
   - Environment -> Select your environment
   - Set `token` = `<copied_access_token>`

## API Endpoints by Category

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user info

### Portfolio Management
- `GET /api/portfolio/paper` - Get paper trading portfolio
- `POST /api/portfolio/trade` - Execute trade (BUY/SELL)
- `GET /api/portfolio/holdings` - Get all holdings
- `POST /api/portfolio/holdings/add` - Add new holding
- `GET /api/portfolio/transactions` - Get transaction history

### Trading Operations
- `GET /api/trading/summary` - Get trading summary
- `POST /api/trading/topup` - Add balance
- `POST /api/trading/reset` - Reset wallet
- `POST /api/trading/buy` - Buy stock
- `POST /api/trading/sell` - Sell stock
- `POST /api/trading/cancel-pending` - Cancel pending order
- `GET /api/trading/equity-history` - Get equity progression
- `POST /api/trading/auto-invest-all` - Auto-invest in all top picks
- `POST /api/trading/auto-invest-single` - Auto-invest in single signal
- `POST /api/trading/check-tpsl` - Check and execute TP/SL

### Analytics & Signals
- `GET /api/signals/top-picks` - Get AI top picks
- `GET /api/performance/history` - Get performance history
- `GET /api/stats` - Get market statistics
- `GET /api/ai/performance-metrics` - Get AI performance metrics

### Bandarmologi Analysis
- `GET /api/bandarmologi/{ticker}` - Get broker accumulation analysis for a ticker

### IHSG Predictions
- `GET /api/ihsg` - Get IHSG market predictions

### DCA Strategy
- `GET /api/portfolio/dca/strategies` - Get active DCA strategies
- `POST /api/portfolio/dca/create-signal` - Create DCA from signal
- `POST /api/portfolio/dca/create-manual` - Create DCA manually
- `POST /api/portfolio/dca/calculate-levels` - Calculate DCA entry levels
- `POST /api/portfolio/dca/deactivate` - Deactivate strategy
- `GET /api/portfolio/dca/recommend-timing` - Get DCA timing recommendation
- `GET /api/portfolio/dca/ai-recommend-entry` - Get AI entry recommendation

## Common Workflows

### Workflow 1: Login and Get Portfolio
```
1. POST /api/auth/login
   - Get access_token from response
   
2. Set Authorization header with token
   - Authorization: Bearer <access_token>
   
3. GET /api/portfolio/paper
   - Returns wallet and holdings
```

### Workflow 2: Execute a Trade
```
1. (Login and get token)

2. POST /api/trading/buy
   {
     "ticker": "BBCA",
     "lot": 1,
     "price": 9500.0,
     "tp1": 10000.0,
     "stop_loss": 9000.0
   }

3. GET /api/trading/summary
   - Verify position is created
```

### Workflow 3: Get AI Recommendations
```
1. GET /api/signals/top-picks
   - Get latest AI recommendations
   
2. GET /api/bandarmologi/{ticker}
   - Get broker accumulation analysis
   
3. GET /api/ihsg
   - Get market direction prediction
```

### Workflow 4: Auto-Trading with DCA
```
1. GET /api/signals/top-picks
   - Select a signal with signal_id
   
2. POST /api/portfolio/dca/create-signal
   {
     "signal_id": 123,
     "total_budget": 10000000,
     "dca_count": 5
   }

3. GET /api/portfolio/dca/strategies
   - Monitor active strategies
```

## Authentication

### Token Format
JWT Bearer token format: `Bearer <your_jwt_token>`

### Headers
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### Token Expiry
- Tokens expire after 24 hours (1440 minutes)
- Re-login to get a fresh token

## Request Examples

### Example 1: Buy a Stock
```bash
curl -X POST http://localhost:8000/api/trading/buy \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "BBCA",
    "lot": 1,
    "price": 9500.0,
    "tp1": 10000.0,
    "stop_loss": 9000.0
  }'
```

### Example 2: Get Bandarmologi Analysis
```bash
curl -X GET http://localhost:8000/api/bandarmologi/BBCA
```

### Example 3: Get Top AI Picks
```bash
curl -X GET http://localhost:8000/api/signals/top-picks
```

## Response Format

All API responses follow this format:

### Success Response
```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful"
}
```

### Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Status Codes
- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Server Error

## Testing the API

### Using cURL
```bash
# Health check
curl http://localhost:8000/

# Get top picks (no auth needed)
curl http://localhost:8000/api/signals/top-picks

# Authenticated endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/trading/summary
```

### Using Python
```python
import requests

# Login
auth_response = requests.post(
    'http://localhost:8000/api/auth/login',
    json={'username': 'user123', 'password': 'pass123'}
)
token = auth_response.json()['access_token']

# Get portfolio
headers = {'Authorization': f'Bearer {token}'}
portfolio = requests.get(
    'http://localhost:8000/api/portfolio/paper',
    headers=headers
)
print(portfolio.json())
```

### Using JavaScript
```javascript
// Login
const loginResp = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user123',
    password: 'pass123'
  })
});
const { access_token } = await loginResp.json();

// Get portfolio
const portfolioResp = await fetch('http://localhost:8000/api/portfolio/paper', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const portfolio = await portfolioResp.json();
console.log(portfolio);
```

## API Schema Definitions

### Wallet Object
```json
{
  "cash": 100000000.0,
  "invested": 5000000.0,
  "pnl": 250000.0
}
```

### Holding Object
```json
{
  "id": 1,
  "ticker": "BBCA",
  "avg_cost": 9500.0,
  "shares": 1000,
  "current_price": 9600.0,
  "value": 9600000.0,
  "pnl_pct": 1.05,
  "status": "ACTIVE",
  "created_at": "2026-07-15T10:00:00Z"
}
```

### Top Pick Object
```json
{
  "id": 123,
  "ticker": "BBCA",
  "action": "BUY",
  "confidence_score": 85.5,
  "current_price": 9500.0,
  "entry_price": 9400.0,
  "reasoning": "Strong bandarmologi accumulation by major brokers",
  "target_1": 10000.0,
  "target_2": 10500.0,
  "target_3": 11000.0,
  "stop_loss": 9000.0,
  "entry_low": 9300.0,
  "entry_high": 9500.0,
  "run_date": "2026-07-15T09:00:00 WIB"
}
```

## Rate Limiting

Current API has no rate limiting configured. For production use, implement rate limiting at the server level.

## Error Handling

### Common Errors

**401 Unauthorized**
- Invalid or expired token
- Solution: Get a new token via login

**400 Bad Request**
- Missing required fields
- Invalid request format
- Insufficient funds for trading
- Solution: Check request body and parameters

**500 Server Error**
- Database connection issue
- Internal server error
- Solution: Check server logs

## Support & Resources

- API Server: http://localhost:8000 (dev) | https://api.hamboo.app (prod)
- Swagger UI: http://localhost:8000/docs (if enabled)
- Issues: Report bugs via ticket system

## File Structure

```
web-backend/
├── openapi.yaml                    # OpenAPI 3.0 specification
├── Hamboo_AI_API.postman_collection.json  # Postman collection
├── README.md                       # This file
└── main.py                         # API implementation
```

## Next Steps

1. **Import** the Postman collection
2. **Set up** environment variables (base_url, token)
3. **Test** endpoints starting with health check
4. **Authenticate** with register or login
5. **Explore** different API endpoints

---

**Last Updated**: 2026-07-15
**API Version**: 1.0.0
**Status**: Production Ready
