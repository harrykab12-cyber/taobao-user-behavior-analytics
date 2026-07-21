FROM apache/superset:4.1.2

USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.10 \
    && python -c "import psycopg2; print(psycopg2.__version__)"
USER superset
