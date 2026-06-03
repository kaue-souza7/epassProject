FROM python:3.12-slim AS builder

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.12-slim AS runtime

WORKDIR /app
RUN groupadd -r epass && useradd -r -g epass epass

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

COPY . .

RUN mkdir -p storage && chown -R epass:epass storage
USER epass

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
