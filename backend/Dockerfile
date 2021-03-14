FROM python:3.8

WORKDIR /app

RUN python -m pip install --upgrade pip
COPY ./requirements.txt /app
RUN pip install -r requirements.txt

# Development
RUN pip install watchdog[watchmedo]

COPY . .

EXPOSE 80

#CMD ["python3", "main.py"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--reload-dir", "/app"]