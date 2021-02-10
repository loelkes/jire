# Jire: Reservation System for Jitsi Meet

From [github.com/jitsi/jicofo](https://github.com/jitsi/jicofo/blob/master/doc/reservation.md):

It is possible to connect Jicofo to external conference reservation system using REST API. Before new Jitsi-meet conference is created reservation system will be queried for room availability. The system is supposed to return positive or negative response which also contains conference duration. Jicofo will enforce conference duration and if the time limit is exceeded the conference will be terminated. If any authentication system is enabled then user's identity will be included in the reservation system query.

Jire does this for you.

![Screenshot of the configuration interface](screenshot.png)

## Features
* Create room reservations
* System checks for overlapping reservations and conferences

### To be implemented
* Edit or reschedule a reservation
* Allow users to login and and manage their own conferences

_Note:_ Conferences created without a reservation are set to a duration of 6 hours by default.

## Run with Docker

```
docker build -t jire:latest .
docker run -v "$(pwd)"/log:/opt/venv/log "$(pwd)"/data:/opt/venv/data -p 8080:8080 jire:latest
```

### Configure Jitsi Meet

If you use [docker-jitsi-meet](https://github.com/jitsi/docker-jitsi-meet) you need to change the following lines in `.env`:

```
JICOFO_RESERVATION_ENABLED=true
JICOFO_RESERVATION_REST_BASE_URL=<url-to-your-jire>
```

If you want to add Jire to your existing docker-jitsi-meet setup you could use the following compose file:

```
version: '3'

services:
  jire:
    image: jire:latest
    restart: unless-stopped
    volumes:
      - ./log:/opt/venv/log
      - ./data:/opt/venv/data
    ports:
      - 127.0.0.1:8080:8080
    environment:
      - PUBLIC_URL=https://meet.example.com

networks:
    default:
        external:
            name: jitsi-meet_meet.jitsi
```

And set the endpoint in `.env` with
```
JICOFO_RESERVATION_REST_BASE_URL=http://jire:8080
```

Restart jicofo and you're good to go.

## Run with gunicorn

```
pip install gunicorn
exec gunicorn -b :8080 main:app
```

## Development

This is a work in progress, pull requests are welcome.

Install with `python setup.py develop` and run with `flask run`.
