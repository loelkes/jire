#!/bin/sh
exec gunicorn -b :8080 main:app
