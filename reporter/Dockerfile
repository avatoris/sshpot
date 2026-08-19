FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Ownership is baked in here rather than via a chown in an entrypoint
# because Docker copies this path's ownership into the reporter-state
# named volume the first time it's created.
RUN useradd -m -u 10001 reporter \
    && mkdir -p /data/state \
    && chown -R reporter:reporter /data /app

USER reporter

CMD ["python", "-m", "app.main"]
