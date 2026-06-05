FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r epass && useradd -r -g epass epass

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .
RUN chmod +x /app/entrypoint.sh

RUN mkdir -p storage && chown -R epass:epass storage

USER epass

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
