FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y build-essential

# Poetry (if you're using it)
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install --no-root

COPY app/data/holdings.json app/data/holdings.json

# App code
COPY . .

CMD ["uvicorn", "app.server.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]