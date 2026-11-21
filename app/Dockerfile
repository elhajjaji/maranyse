# MaranYSE — espace parents en conteneur Docker (pilote bureau-enfants via docker.sock)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        docker-cli openssl iproute2 ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY tableau.py style.py stats.py aide.py logique.py marque.py logiciels.py themes.py i18n.py ./
COPY i18n/ ./i18n/
COPY assets/ ./logo_web/

ENV MARANYSE_DATA_DIR=/data \
    PYTHONUNBUFFERED=1

VOLUME ["/data"]
EXPOSE 8080

CMD ["python3", "/app/tableau.py"]
