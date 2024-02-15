FROM python:3.12

WORKDIR /app

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY pywsgi.py ./
COPY plex.py ./
COPY plex_tmsid.csv/ ./

RUN echo $PATH
ENV PATH "/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.local/bin"
RUN echo $PATH

ENV PYTHONUNBUFFERED=1

EXPOSE 7777/tcp
CMD ["python3","pywsgi.py"]