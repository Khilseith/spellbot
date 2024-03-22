FROM python:3.11.2

WORKDIR /spellbot

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

ENV TOKEN=$TOKEN

CMD ["python", "./src/main.py"]

