# 🏏 IPL Prediction Platform

A production-oriented backend system for a Cricbuzz-style cricket analytics platform that provides real-time match predictions, win probability, and live data processing.

---

## 🚀 Key Features

- Live match data integration
- Win probability prediction engine
- Ball-by-ball and over-by-over insights
- FastAPI-based backend
- Modular architecture with services, providers, and repositories
- PostgreSQL-ready schema for analytics

---

## 🏗️ System Architecture

- API Layer → FastAPI routes
- Services Layer → Business logic
- Providers Layer → External API integrations
- Repositories Layer → Data access abstraction
- Prediction Engine → Rule-based now, ML-ready later
- Cache Layer → In-memory TTL caching

---

## 📂 Project Structure

```text
src/ipl_predictor/
├── api/
├── services/
├── providers/
├── repositories/
├── prediction/
├── ml/
├── cache/
├── db/


🛠️ Tech Stack
Python
FastAPI
PostgreSQL
CricAPI / CricketData
In-memory caching
⚙️ Environment Setup

Create a .env file:
LIVE_PROVIDER=cricapi
CRICAPI_BASE_URL=https://api.cricapi.com/v1
CRICAPI_API_KEY=your_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/ipl_predictor
REDIS_URL=
CACHE_TTL_LIVE_SECONDS=15
CACHE_TTL_SEASON_SECONDS=300
LIVE_POLL_SECONDS=20
▶️ Run Locally
pip install -r requirements.txt
uvicorn src.ipl_predictor.api.app:app --reload
Open:

http://127.0.0.1:8000
http://127.0.0.1:8000/docs
📈 Future Improvements
Replace rule-based engine with ML model
Add frontend dashboard
Deploy on cloud
Add authentication and rate limiting
