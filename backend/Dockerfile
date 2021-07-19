FROM python:3.9

WORKDIR /app

RUN python -m pip install --upgrade pip
COPY ./requirements.txt /app
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]