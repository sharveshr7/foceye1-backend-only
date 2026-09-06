# 🏥 FOCEYE Production Backend

Production-grade FastAPI, Supabase, Computer Vision & AI Telemetry Engine for Ophthalmic Vision Therapy and Clinical Diagnostics.

---

## 🚀 Tech Stack

- **API Layer**: FastAPI (Python 3.11+) + Uvicorn ASGI
- **Validation**: Pydantic v2
- **Auth & Database**: Supabase Auth (JWT) & Supabase PostgreSQL
- **Real-Time Streaming**: Native WebSockets (60 FPS Gaze Telemetry)
- **Scientific Eye Processing**: OpenCV + NumPy + SciPy (BCEA 68%/95%, I-VT Fixations)
- **Calibration Engine**: 9-Point Polynomial Surface Transform (NumPy / SciPy)
- **AI Diagnostics**: Google Gemini 1.5 Flash + Clinical Heuristic Engine
- **Reports**: ReportLab (Clinical Ophthalmic PDF Generation)
- **Container**: Docker + Render Cloud Blueprint

---

## 🛠️ Step 1: Database Setup (Supabase)

1. Create a project at [supabase.com](https://supabase.com).
2. Go to the **SQL Editor** tab in your Supabase Dashboard.
3. Copy the entire content of [`supabase_schema.sql`](./supabase_schema.sql) and click **Run**.
4. In **Project Settings -> API**, copy:
   - `Project URL` (`SUPABASE_URL`)
   - `anon public` key (`SUPABASE_KEY`)
   - `service_role secret` key (`SUPABASE_SERVICE_ROLE_KEY`)

---

## ⚙️ Step 2: Environment Configuration

Create `.env` based on `.env.example`:

```bash
cp .env.example .env
```

Fill in your actual production credentials:
```env
ENVIRONMENT=production
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=["https://your-frontend-domain.com","http://localhost:3000"]

# Supabase
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
JWT_SECRET=your-production-jwt-secret

# Google Gemini API
GEMINI_API_KEY=your-google-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
```

---

## 🚢 Step 3: Deployment on Render

### Option A: Using `render.yaml` Blueprint (Recommended)
1. Push this repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Connect your GitHub repository. Render will automatically detect [`render.yaml`](./render.yaml).
4. Enter your environment variables (`SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, etc.) when prompted.

### Option B: Manual Web Service
- **Environment**: `Python 3` or `Docker`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`

---

## 🧪 Local Testing & Verification

```bash
# Run pytest suite
python -m pytest tests

# Run local dev server
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`
