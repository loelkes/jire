FROM python:3.8-alpine

WORKDIR /usr/src/app


RUN pip install Flask
RUN pip install gunicorn

COPY setup.py .
COPY jire ./jire
COPY main.py .
COPY run.sh .
RUN mkdir log
RUN python setup.py install

EXPOSE 8080
ENTRYPOINT ["./run.sh"]
