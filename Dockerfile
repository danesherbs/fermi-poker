FROM python:3.10
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt
COPY . .
EXPOSE 8000
ENV FLASK_APP=app.py
CMD ["python", "app.py"]
