import os
import secrets
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_bootstrap import Bootstrap
from .Conferences import Manager
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'default',
            'filename': 'log/flask.log'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi', 'file']
    }
})


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(16)
    # See https://pythonhosted.org/Flask-Bootstrap/configuration.html
    BOOTSTRAP_SERVE_LOCAL = True


app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)  # Cross-Site Request Forgery protection for forms.
Bootstrap(app)  # Bootstrap system
manager = Manager()

from jire import routes
