# Automation dashboard + GenAI chat proxy (Symphony OpenAI gateway)
FROM python:3.12-slim

WORKDIR /app

# Static site + proxy script only (no secrets baked in)
COPY index.html ./
COPY assets ./assets
COPY data ./data
COPY scripts/dashboard-server.py ./scripts/dashboard-server.py

ENV DASHBOARD_HOST=0.0.0.0
ENV DASHBOARD_PORT=8765
ENV OPENAI_API_BASE=https://ai-api.symphonyretailai.com
ENV OPENAI_MODEL=gpt-4.1

EXPOSE 8765

# OPENAI_KEY must be provided at runtime (env / compose / -e)
CMD ["python3", "scripts/dashboard-server.py"]
