# frut
Provide street navigation with driving fun in mind

## Overview

**frut** is a web application that finds the most enjoyable driving route between two locations by combining shortest-path routing with a curviness index called **frutidx**.

A higher frutidx means more (and sharper) corners — more driving fun.

## Architecture (AWS)

```
Browser ──HTTPS──► CloudFront ──► S3            (frontend: HTML/JS)
                              ──► API Gateway ──► Lambda (FastAPI backend)
```

- **Frontend** – static HTML/CSS/JS with [Leaflet.js](https://leafletjs.com/) map
- **Backend** – Python [FastAPI](https://fastapi.tiangolo.com/) deployed as AWS Lambda (via [Mangum](https://mangum.io/))
- **Routing** – [OSRM](http://project-osrm.org/) HTTP API (public demo server or self-hosted)
- **Infrastructure** – [AWS CDK](https://aws.amazon.com/cdk/) (Python)

## frutidx Algorithm

1. For each *section* (straight line between two consecutive route coordinates) compute its **bearing** (compass direction, 0–360°).
2. For each pair of adjacent sections compute the **absolute bearing difference** (0–180°).
3. The **frutidx of a section** = average of the bearing differences to its leading and following section.
   - First section: equals the difference to the following section only.
   - Last section: equals the difference to the leading section only.
4. The **total frutidx** of a route = sum of all per-section values.
5. The **frut score** = `weight × (total_frutidx / distance_km)` — higher is better.

Routes returned by the API are sorted by frut score (descending).

## Project Structure

```
frut/
├── backend/
│   ├── frut_calculator.py   # Core frutidx algorithm
│   ├── routing.py           # OSRM integration & route scoring
│   ├── app.py               # FastAPI application + Lambda handler
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── infrastructure/
│   ├── frut_stack.py        # AWS CDK stack
│   ├── app.py               # CDK entry point
│   └── requirements.txt
└── tests/
    └── test_frut_calculator.py
```

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
# API available at http://localhost:8000
```

### Frontend

Open `frontend/index.html` in a browser.  
Set `window.FRUT_API_BASE = 'http://localhost:8000'` before loading `app.js`, or serve both from the same origin.

### Tests

```bash
pip install pytest
pytest tests/ -v
```

## Deployment (AWS CDK)

```bash
cd infrastructure
pip install -r requirements.txt
cdk bootstrap   # first time only
cdk deploy
```

The stack outputs the CloudFront URL (frontend + API) after a successful deployment.

### Configuration

| Environment variable | Default | Description |
|---|---|---|
| `OSRM_BASE_URL` | `https://router.project-osrm.org` | OSRM instance base URL |
