FROM python:3.12-alpine3.20


EXPOSE 7777/tcp

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check --no-compile -r requirements.txt

COPY pywsgi.py ./
COPY plex.py ./
COPY plex_tmsid.csv/ ./

CMD ["python3","pywsgi.py"]
