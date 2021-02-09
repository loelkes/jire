FROM python:3.9-slim AS compile-image

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /opt/venv

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc

COPY setup.py .

RUN pip install Flask
RUN python setup.py install

FROM python:3.9-alpine AS build-image

WORKDIR /opt/venv
COPY --from=compile-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY jire ./jire
COPY main.py .
COPY run.sh .
RUN mkdir log
RUN mkdir data
RUN pip install gunicorn

EXPOSE 8080
ENTRYPOINT ["./run.sh"]
