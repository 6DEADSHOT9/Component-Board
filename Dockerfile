FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./
COPY templates ./templates
COPY static ./static
COPY data ./data
COPY public ./public
RUN useradd --uid 10001 --create-home board
USER board
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --preload --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 90 app:app"]
