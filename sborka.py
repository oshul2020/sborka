# -*- coding: utf-8 -*-
from __future__ import with_statement
import locale
from flask import Flask, request
from flask_session import Session
from flask_mobility import Mobility
from tempfile import mkdtemp
import traceback
import datetime

# Blueprints
from Sborka.bus.api import app_bus

locale.setlocale(locale.LC_ALL, '')
app = Flask(__name__)
Mobility(app)
app.register_blueprint(app_bus)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.permanent_session_lifetime = datetime.timedelta(minutes=15)
Session(app)


@app.route("/")
def get_index():
	return f'{datetime.datetime.now()} a.sborka.ua'

@app.route("/buss")
def get_buss():
	return '<h1>bus</h1>'	
	
@app.after_request
def after_request(response):
	"""Disable caching"""
	response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
	response.headers["Expires"] = 0
	response.headers["Pragma"] = "no-cache"
	return response	
	
if __name__ == "__main__":
	app.run(host='0.0.0.0')
