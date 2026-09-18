# Imagem do painel de hanseníase de PE. Segue o padrão dos irmãos da família Cenários+ — mesma
# base, mesmo healthcheck, mesmo jeito de subir —, com uma diferença: os dados
# entram por volume e não por `COPY`. São 209 MB que mudam por extração nova,
# não por commit; dentro da imagem, trocar o dado exigiria rebuild.
FROM python:3.13-slim

WORKDIR /app

# Dependências de sistema:
#   curl     → healthcheck
#   libgomp1 → DuckDB usa OpenMP para paralelizar
# geopandas não precisa de GDAL do sistema: pyogrio, shapely e pyproj trazem
# GDAL, GEOS e PROJ nas próprias wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Do lock, não do requirements.txt: aquele declara faixas (`streamlit>=1.40`) e
# dois builds do mesmo commit poderiam subir versões diferentes. O lock tem as
# versões exatas com que a suíte passa.
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY app.py .
COPY src/ src/
COPY assets/ assets/
COPY .streamlit/ .streamlit/

EXPOSE 8501

# O caminho do healthcheck inclui o subcaminho: sob `baseUrlPath`, o Streamlit
# serve `/cenarios/hansepe/_stcore/health` e a raiz responde 404. O painel irmão
# de Recife ficou meses com healthcheck vermelho por causa disso.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8501/cenarios/hansepe/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.baseUrlPath=cenarios/hansepe", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=true", \
    "--browser.gatherUsageStats=false"]
