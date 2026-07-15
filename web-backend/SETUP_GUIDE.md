## 📚 API Documentation Setup Guide

### Files Created

✅ **openapi.yaml** (400+ lines)
   - Complete OpenAPI 3.0 specification
   - All 40+ endpoints documented
   - Request/response schemas
   - Authentication details

✅ **Hamboo_AI_API.postman_collection.json** (500+ lines)
   - Ready-to-import Postman collection
   - Organized by 7 functional categories
   - Pre-configured base_url and token variables
   - Example request bodies included

✅ **API_DOCUMENTATION.md** (400+ lines)
   - Comprehensive guide with examples
   - cURL, Python, and JavaScript examples
   - Common workflows documented
   - Schema definitions
   - Troubleshooting section

---

### 🚀 Quick Start (Choose One)

#### Option 1: Postman (Recommended for Testing)
```bash
# 1. Open Postman
# 2. File → Import
# 3. Choose: Hamboo_AI_API.postman_collection.json
# 4. Set Environment Variables:
#    - base_url = http://localhost:8000
#    - token = (empty, will fill after login)
# 5. Go to Auth → Login User
# 6. Copy access_token to environment variable
# 7. Try other endpoints!
```

#### Option 2: Swagger UI (Online Viewer)
```bash
# Visit: https://editor.swagger.io/
# Then: File → Import URL
# Paste the openapi.yaml file content
```

#### Option 3: Local Swagger UI (Docker)
```bash
docker run -p 8080:8080 \
  -e SWAGGER_JSON=/openapi.yaml \
  -v $(pwd)/web-backend/openapi.yaml:/openapi.yaml \
  swaggerapi/swagger-ui
  
# Visit: http://localhost:8080
```

---

### 📊 API Coverage Summary

**40+ Endpoints Documented:**

| Category | Count | Key Endpoints |
|----------|-------|---------------|
| Authentication | 3 | Register, Login, Get Me |
| Portfolio | 5 | Get Paper Portfolio, Holdings, Transactions |
| Trading | 9 | Buy, Sell, Cancel, TP/SL Check, Auto-Invest |
| Signals | 4 | Top Picks, Performance, Stats, AI Metrics |
| Bandarmologi | 1 | Get Broker Analysis |
| IHSG | 1 | Get IHSG Predictions |
| DCA Strategy | 7 | Create, Calculate, Deactivate |

---

### 🔧 Environment Setup

**Postman Environment Variables:**
```json
{
  "base_url": "http://localhost:8000",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Headers (Auto-added for auth endpoints):**
```
Authorization: Bearer {{token}}
Content-Type: application/json
```

---

### 📝 Example Workflows

**Workflow 1: Quick Test**
```
1. Health Check (GET /)
2. Get Top Picks (GET /api/signals/top-picks)
3. Get Market Stats (GET /api/stats)
   (No auth needed!)
```

**Workflow 2: Full Trading Flow**
```
1. Register/Login (POST /api/auth/register or /login)
2. Get Portfolio (GET /api/portfolio/paper)
3. Buy Stock (POST /api/trading/buy)
4. Check Summary (GET /api/trading/summary)
5. Auto Close TP/SL (POST /api/trading/check-tpsl)
```

**Workflow 3: Analysis Only**
```
1. Get Top Picks (GET /api/signals/top-picks)
2. Get Bandarmologi (GET /api/bandarmologi/BBCA)
3. Get IHSG Forecast (GET /api/ihsg)
4. Get Performance (GET /api/performance/history)
```

---

### 🔑 Testing Credentials

For testing, use any username/password:
```json
{
  "username": "testuser",
  "password": "testpass123"
}
```

The API auto-creates wallets for new users with 100M starting capital.

---

### ✨ Key Features Documented

**Authentication**
- JWT Bearer token auth
- Auto token generation on register/login
- 24-hour token expiry

**Portfolio Management**
- Paper trading wallet
- Multiple holdings
- Transaction history
- DCA strategies

**AI Features**
- Top picks with confidence scores
- Bandarmologi broker analysis
- IHSG market predictions
- Performance metrics

**Auto-Trading**
- Auto-invest all signals
- Auto-invest single signal
- Auto TP/SL execution
- DCA level calculation

---

### 📖 Files Location

```
web-backend/
├── openapi.yaml ........................... Swagger/OpenAPI spec
├── Hamboo_AI_API.postman_collection.json .. Postman collection
├── API_DOCUMENTATION.md ................... Full documentation
└── main.py ............................... API implementation
```

---

### 🎯 Next Steps

1. **Import** Postman collection (easiest)
2. **Register/Login** to get auth token
3. **Test** health endpoint first (GET /)
4. **Explore** different API categories
5. **Read** API_DOCUMENTATION.md for details

---

### 💡 Pro Tips

- Use Postman's "Save Response" to compare outputs
- Create test data scripts in "Tests" tab
- Export responses as curl commands
- Use Pre-request Scripts for dynamic test data

---

**Status**: ✅ Complete  
**Total Endpoints**: 40+  
**Last Updated**: 2026-07-15
