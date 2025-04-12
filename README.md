# MCP Server Analysis System

A comprehensive system for analyzing MCP server data with a focus on evaluation and recommendations.

## Features

- Process raw crawled MCP server data to extract key metrics and information
- Display aggregated server information with quality scores
- Implement server clustering based on entity linking
- Evaluate servers on code quality, tool completeness, documentation quality, runtime stability, and business value
- Provide server recommendations based on user search criteria

## Project Structure

```
mcp-analysis-system/
├── backend/                # FastAPI backend
│   ├── app/                # Application code
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Data models
│   │   ├── services/       # Business logic
│   │   └── main.py         # Application entry point
│   ├── data/               # Data storage
│   ├── scripts/            # Utility scripts
│   └── pyproject.toml      # Python dependencies
└── frontend/               # React frontend
    ├── public/             # Static assets
    ├── src/                # Source code
    │   ├── components/     # React components
    │   ├── services/       # API services
    │   └── App.tsx         # Main application
    ├── package.json        # Node dependencies
    └── vite.config.ts      # Vite configuration
```

## Deployment Instructions

### Backend Deployment

1. Install Python 3.12+ and Poetry on your host
2. Clone the repository: `git clone <your-repo-url>`
3. Navigate to the backend directory: `cd mcp-analysis-system/backend`
4. Install dependencies: `poetry install`
5. Prepare the data: `poetry run python scripts/prepare_data.py`
6. Start the server: `poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000`
7. For production, use Gunicorn: `poetry run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`

### Frontend Deployment

1. Install Node.js and npm on your host
2. Navigate to the frontend directory: `cd mcp-analysis-system/frontend`
3. Install dependencies: `npm install`
4. Update the `.env` file with your backend URL: `VITE_API_URL=http://your-backend-host:8000/api`
   - For authenticated access: `VITE_API_URL=https://user:password@your-backend-host/api`
5. Build the frontend: `npm run build`
6. Serve the built files using any static file server like Nginx or Apache

### Using Docker (alternative)

For containerized deployment, you can create Docker configurations:

1. Create a `Dockerfile` for the backend:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

COPY . /app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Create a `Dockerfile` for the frontend:
```dockerfile
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

3. Create a `docker-compose.yml` file:
```yaml
version: '3'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data:/app/data

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

4. Run with: `docker-compose up -d`

## Technology Stack

- **Backend**: FastAPI, Python 3.12, scikit-learn, NLTK, spaCy
- **Frontend**: React, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Data Processing**: Pandas, NumPy
- **Visualization**: t-SNE, PCA

## License

MIT
