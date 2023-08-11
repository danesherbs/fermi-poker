FROM python:3.10
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
ENV FLASK_APP=app.py
CMD ["gunicorn", "-w", "4", "app:app", "-b", "0.0.0.0:8000"]
