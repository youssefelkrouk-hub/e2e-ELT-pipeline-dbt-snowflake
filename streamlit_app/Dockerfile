# ============================================================
# Dockerfile — streamlit_app
# ============================================================
# Image de base légère Python 3.11
FROM python:3.11-slim

# Métadonnées
LABEL maintainer="sales-pipeline-team"
LABEL description="Streamlit dashboard — Sales Data Pipeline"

# Utilisateur non-root pour la sécurité
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Répertoire de travail
WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Répertoire des CSV (sera monté en volume)
RUN mkdir -p /app/data

# Propriété à l'utilisateur non-root
RUN chown -R appuser:appgroup /app

# Passer à l'utilisateur non-root
USER appuser

# Port Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Point d'entrée
ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
