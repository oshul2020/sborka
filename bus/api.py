from functools import wraps
import time
import re
import hashlib
import importlib
import json
from flask import Blueprint, render_template, request, redirect, session, flash, jsonify, get_template_attribute, g 
from flask_mobility.decorators import mobilized
from flask_sqlalchemy import BaseQuery
from sqlalchemy import create_engine, cast, Integer, or_, func, inspect, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.serializer import loads, dumps
from datetime import date, timedelta, datetime, time

from Sborka.bus.entity import crudPost, User, Syslog, Log, Route, Trip

dbBusPath = 'sqlite:////var/db/bus.db'
logsOnPage = 50

app_bus = Blueprint('app_bus', __name__, template_folder='bus_templates')

Base = declarative_base()

engine = create_engine(dbBusPath, connect_args={'check_same_thread': False},echo=False)
Base.metadata.create_all(engine)
db = Session(engine)
db.expire_on_commit = None


'''
@app_bus.context_processor
def inject_status():
	pass
'''

@event.listens_for(db, 'after_bulk_update')
def receive_after_bulk_update(update_context):
	pass

def clear_session():
	try:
		session.pop('bus_user', None)
	except:
		pass

def desktop_only(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if request.MOBILE:
			return redirect('/bus')
			
		return f(*args, **kwargs)
	return decorated_function

def super_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if session.get('bus_user') is None:
			return render_template('b_message.html', message='Необходимо войти в систему.')	 
		
		if session['bus_user'].status < User.SUPER:
			return render_template('b_message.html', message='Недостаточно прав.')	 	   
		
		return f(*args, **kwargs)
	return decorated_function

def admin_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if session.get('bus_user') is None:
			return render_template('b_message.html', message='Необходимо войти в систему.')	 
		
		if session['bus_user'].status < User.ADMIN:
			return render_template('b_message.html', message='Недостаточно прав.')	 	   
		
		return f(*args, **kwargs)
	return decorated_function
	
def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if session.get('bus_user') is None:
			return redirect('/bus/login')
			
		return f(*args, **kwargs)
	return decorated_function

@app_bus.route('/bus/test', methods=['GET', 'POST'])
@super_required
def b_test():
	
	return 'only for testing'


@app_bus.route('/bus/balance', methods=['GET', 'POST'])
@super_required
def b_balance():
	user = session['bus_user']
	now = datetime.now()
	q_users = db.query(User).filter(User.status > User.HIDE).order_by(User.title)
	
	if request.method == "POST":
		cmd = request.form.get('cmd')	
		if cmd == 'balance':
			client_id = request.form.get('user', type=int)
			amount = request.form.get('amount', type=int)
						
			client_account = db.query(User).get(client_id).account
			db.query(User).filter_by(id=client_id).update({'account': User.account - amount})
			l = Log()
			l.action = Log.PAY
			l.time = now
			l.user_id = client_id
			l.info = f'оплачено: {amount} поездки | кому: {user} | было: {client_account}'
			db.add(l)
			db.commit()
			
			if user.id == client_id:
				user.account -= amount
									
			users_list = get_template_attribute('b_balance.html', 'users_list')
			return users_list(users=q_users.all())
	
	return render_template('b_balance.html', users=q_users.all())
	
@app_bus.route('/bus/admin', methods=['GET', 'POST'])
@desktop_only
@super_required
def b_admin():	
	return render_template('b_admin.html', user = session['bus_user'])

@app_bus.route('/bus/route_content', methods=['GET', 'POST'])	
@login_required
def b_route_content():
	user = session['bus_user']
	now = datetime.now()
		
	if request.method == "POST":
		cmd = request.form.get('cmd')	
		if cmd == 'add':
			route_id = request.form.get('route_id', type=int)
			route = db.query(Route).get(route_id)
			clients = request.form.getlist('users[]', type=int)	
						
			for client_id in clients:
				t = Trip()
				t.time = now
				t.status = Trip.OK
				t.route_id = route_id
				t.user_id = client_id
				t.admin_id = user.id
				
				db.add(t)
				client = db.query(User).get(client_id)
				before = client.account
				client.account = User.account + 1
					
				l = Log()
				l.action = Log.WRITEOFF
				l.time = now
				l.user_id = client_id
				l.info = f'№{t.route.id} {t.route.title} | добавил: {user} | было: {before}'
				db.add(l)
				
				if user.id == client_id:
					user.account += 1
			
			db.commit()
				
		elif cmd == 'cancel':
			trip_id = request.form.get('trip_id', type=int)
			t = db.query(Trip).get(trip_id)
			t.status = Trip.CANCEL
			t.admin_id = user.id
			route = t.route
			
			l = Log()
			l.action = Log.CANCEL
			l.time = now
			l.user_id = t.user.id
			l.info = f'№{route.id} {route.title} | отменил: {user} | было: {t.user.account}'

			db.add(l)
			db.query(User).filter_by(id=t.user.id).update({'account': User.account - 1})
			
			db.commit()
			
			if user.id == t.user.id:
				user.account -= 1
			
		trips = db.query(Trip).filter(func.DATE(Trip.time) == now.date())	\
				.filter(Trip.route_id == route.id)	\
				.order_by(Trip.status)	\
				.all()
	
		cnt = get_template_attribute('b_content_widget.html', 'content')
		return cnt(route, trips, user)	
	
	else:
		route_id = request.args.get('route', type=int)
		route = db.query(Route).get(route_id)
		
	trips = db.query(Trip).filter(func.DATE(Trip.time) == now.date())	\
		.filter(Trip.route_id == route.id)	\
		.order_by(Trip.status)	\
		.all()

	return render_template('b_content.html', route=route, trips = trips, user=user)	


@app_bus.route('/bus/password', methods=['GET', 'POST'])	
@login_required
def b_password():
	if request.method == "POST":
		old_passw = request.form.get('old_password')
		new_passw = request.form.get('new_password')
		
		if not new_passw:
			return render_template('b_message.html', message='не указан новый пароль')
		
		if new_passw == old_passw:
			return render_template('b_message.html', message='нечего менять')		
		
		user = db.query(User).get(session['bus_user'].id)	
		old_hash = hashlib.md5(old_passw.encode('utf-8')).hexdigest()
		if user.hash != old_hash:
			return render_template('b_message.html', message='не верный старый пароль')
		
		user.hash = hashlib.md5(new_passw.encode('utf-8')).hexdigest()

		log = Syslog()
		log.action = Syslog.PASSW 
		log.user_id = user.id
		log.time = datetime.now()
						
		try:
			log.info = 'успешно'
			db.add(log)	
			db.commit()

		except Exception as e:
			print(e)
			db.rollback()
			log.info = 'ошибка: совпадение паролей'
			db.add(log)	
			db.commit()
			return render_template('b_message.html', message='не изменен. попробуйте другой пароль')
		
		return render_template('b_message.html', message='пароль успешно изменен')
	
	
	cmd = request.args.get('cmd')
	if cmd and cmd=='temp':
		return render_template('b_password_temp.html')
		
	return render_template('b_password.html')

@app_bus.route('/bus/payment', methods=['GET', 'POST'])	
@login_required
def b_payment():	
	user = session['bus_user']
	payments = db.query(Log) \
		.filter(Log.user_id == user.id) \
		.filter(Log.action == Log.PAY) \
		.order_by(Log.id.desc()) \
		.all()
	
	return render_template('b_payment.html', payments=payments)	
	'''
	query = BaseQuery(Trip, db).filter(Trip.user_id == user.id).order_by(Trip.id.desc())

	if request.method == "GET":
		return render_template('b_history.html', paginate=query.paginate(1, 10))
				
	page = request.form.get('page', type=int)
	paginate= query.paginate(page, 10)
	rows = get_template_attribute('b_history_table.html', 'rows')
	return rows(paginate)
	'''
	
@app_bus.route('/bus/history', methods=['GET', 'POST'])	
@login_required
def b_history():	
	user = session['bus_user']
	query = BaseQuery(Trip, db).filter(Trip.user_id == user.id).order_by(Trip.id.desc())

	if request.method == "GET":
		return render_template('b_history.html', paginate=query.paginate(1, 10))
				
	page = request.form.get('page', type=int)
	paginate= query.paginate(page, 10)
	rows = get_template_attribute('b_history_table.html', 'rows')
	return rows(paginate)
	
@app_bus.route('/bus/trip', methods=['GET', 'POST'])	
@login_required
def b_trip():
	if request.method == "POST":
		now = datetime.now()
		cmd = request.form.get('cmd')
		route_id = request.form.get('route', type=int)
		user = session['bus_user']
		stop = request.form.get('stop')
		message = request.form.get('message')
			
		trip = db.query(Trip).filter(func.DATE(Trip.time) == now.date())	\
			.filter(Trip.route_id == route_id)	\
			.filter(Trip.user_id == user.id)	\
		.first()
		
		if trip:
			if trip.status == Trip.CANCEL:
				return render_template('b_trip.html', show='cancel', trip=trip)
			
			elif trip.status == Trip.OK:
				return render_template('b_trip.html', show='info', trip=trip)
			
		t = Trip()
		t.time = now
		t.status = Trip.OK
		t.route_id = route_id
		t.user_id = user.id
		t.stop = stop
		t.message = message.strip()[:50]
		
		db.add(t)
		db.query(User).filter_by(id=user.id).update({'account': User.account + 1})
			
		info = [f'№{t.route.id} {t.route.title} | ',]
		if t.stop:
			info.append(f'остановка: {t.stop} | ')
			
		if t.message:
			info.append(f'сообщение: {t.message} | ')
		
		info.append(f'было: {user.account}')
		
		l = Log()
		l.action = Log.WRITEOFF
		l.time = now
		l.user_id = user.id
		l.info = ''.join(info)
		db.add(l)
		db.commit()
		
		user.account += 1
		
		trips = db.query(Trip)	\
			.filter(Trip.user_id == user.id)	\
			.order_by(Trip.id.desc()).limit(5).all()

		return redirect('/bus/history')
	
@app_bus.route('/bus', methods=['GET', 'POST'])
@login_required
def b_index():
	now = datetime.now()
	day = now.weekday()
	now_time = now.time()
	next = None
	
	user = db.query(User).get(session['bus_user'].id)
			
	routes = db.query(Route).filter(Route.status == Route.ACTIVE)	\
							.filter(Route.open <= now_time) \
							.filter(now_time <= Route.close) \
							.filter(Route.days.op('&')(1 << day) != 0) \
							.all()
	if len(routes) == 0:
		next = db.query(Route).filter(Route.status == Route.ACTIVE)	\
							.filter(Route.days.op('&')(1 << day) != 0) \
							.filter(Route.start > now_time) \
							.order_by(Route.start) \
							.first()
	
	return render_template('b_main.html', routes=routes, next=next, user=user, time=now)

	
@app_bus.route('/bus/route', methods=['GET', 'POST'])
@desktop_only
@super_required
def b_route():
	if request.method == "POST":
		crudPost(db, request, 'Route')
	
	return render_template('b_route.html', 
		routes= db.query(Route).all(), statuses=Route.statuses)
	
	
@app_bus.route('/bus/user', methods=['GET', 'POST'])
@desktop_only
@super_required
def b_user():
	if request.method == "POST":
		status = request.form.get('status', type=int)
		if status <= session['bus_user'].status:
			crudPost(db, request, 'User')
	
	return render_template('b_user.html', users=db.query(User)
		.filter(User.status <= session['bus_user'].status).all(),
		current_user = session['bus_user'])
	

@app_bus.route("/bus/logout", methods=["GET", "POST"])
@login_required
def b_logout():
	clear_session()
	return render_template('b_message.html', message='сессия закрыта')	
	
@app_bus.route("/bus/login", methods=["GET", "POST"])
def b_login():
	clear_session()
		
	if request.method == "POST":
		passw = request.form.get('password')
		hash = hashlib.md5(passw.encode('utf-8')).hexdigest()
		try:
			user = db.query(User).filter(User.hash == hash).one()
			session['bus_user'] = user
			session['desktop'] = not request.MOBILE
			
			'''
			agent = re.findall(r'\(.*?\)', request.headers.get('User-Agent'))
			log = Syslog()
			log.action = Syslog.LOGIN 
			log.user_id = user.id
			log.time = datetime.now()
			log.info = f'{agent[0]} ip:{request.remote_addr}'
			db.add(log)
			db.commit()
			'''
			
			return redirect('/bus')	
					
		except Exception as e:
			return render_template('b_message.html', message='пользователь не определен')
	else:
		return render_template('b_login.html')
		
@app_bus.route('/bus/jdata', methods=['POST'])
@admin_required
def b_jdata():
	cmd = request.form.get('cmd')
		
	if cmd == 'info':
		entity = request.form.get('entity')
		id = request.form.get('id')
		lib = importlib.import_module('Sborka.bus.entity')
		Entity = getattr(lib, entity)
		return	jsonify(db.query(Entity).get(id).serialize())			
	
	if cmd == '!route_pass':
		route_id = request.form.get('route_id')
			
		query = db.query(User)
		query = query.join(Trip, Trip.user_id==User.id)	
		query = query.filter(User.status != User.HIDE)
		query = query.filter(Trip.route_id == route_id)
		query = query.filter(func.DATE(Trip.time) == datetime.now().date())
		route_users = query.subquery()

		users = db.query(User).outerjoin(route_users, route_users.c.user_id == User.id)	\
			.filter(route_users.c.user_id==None).all()
		
		data = {}
		for user in users:
			data[user.title] = user.id
			
		return jsonify(data)	

@app_bus.route('/bus/syslog', methods=['GET', 'POST'])
@super_required
@desktop_only
def b_syslog():
	query = BaseQuery(Syslog, db).order_by(Syslog.id.desc())
	if request.method == "GET":
		return render_template('b_log.html', paginate=query.paginate(1, logsOnPage), log='syslog')
				
	page = request.form.get('page', type=int)
	paginate= query.paginate(page, logsOnPage)
	table = get_template_attribute('b_log_table.html', 'table')
	return table(paginate)			

@app_bus.route('/bus/log', methods=['GET', 'POST'])
@admin_required
@desktop_only
def b_log():
	query = BaseQuery(Log, db).order_by(Log.id.desc())
	if request.method == "GET":
		return render_template('b_log.html', paginate=query.paginate(1, logsOnPage), log='log')
				
	page = request.form.get('page', type=int)
	paginate= query.paginate(page, logsOnPage)
	table = get_template_attribute('b_log_table.html', 'table')
	return table(paginate)
	
@app_bus.app_template_filter()
def days(val):
	days = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')
	result = []
	for i in range(0,7):
		check = 1 & (int(val) >> i);
		if check == 1:
			result.append(days[i])

	return ','.join(result)				

		
@app_bus.route('/bus/routes', methods=['GET', 'POST'])
def b_routes():
	return render_template('b_routes.html', 
		routes= db.query(Route).filter(Route.status == Route.ACTIVE).all())
			
	
