from sqlalchemy import Table, Column, Integer, DateTime, Time, String, MetaData, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from flask import flash, session
import importlib, datetime

Base = declarative_base()

class Route(Base):
	__tablename__ = 'route'
	id = Column('route_id', Integer, primary_key=True)
	title = Column('route_title', String)
	open = Column('route_open', Time)
	start = Column('route_start', Time)
	close = Column('route_close', Time)
	days = Column('route_days', Integer)
	status = Column('route_status', Integer)
	bus = Column('route_bus', String)
	driver = Column('route_driver', String)
	contact = Column('route_contact', String)
	info = Column('route_info', String)
	stops = Column('route_stops', String)
	
	ACTIVE, CLOSE = 0, 1
	statuses = ('активный', 'закрыт')
	
	def get_stops(self):
		return self.stops.split(';')
		
	def serialize(self):
		return {'id': self.id, 'title': self.title, 
			'open': self.open.strftime('%H:%M'), 
			'start': self.start.strftime('%H:%M'), 
			'close': self.close.strftime('%H:%M'),
			'days': self.days, 'status': self.status, 
			'stops': self.stops,
			'bus': self.bus, 'driver': self.driver, 'contact': self.contact, 'info': self.info}
		
	def __repr__(self):
		return self.title

class User(Base):
	__tablename__ = 'user'
	id = Column('user_id', Integer, primary_key=True)
	title = Column('user_title', String)
	status = Column('user_status', Integer)
	account = Column('user_account', Integer)
	hash = Column('user_hash', String)
	info = Column('user_info', String)
	
	HIDE, PASS, ADMIN, SUPER, DEV = 0, 1, 2, 3, 4
	statuses = ('скрыть', 'пассажир', 'админ', 'супер', 'dev')
	
	def serialize(self):
		return {'id': self.id, 'title': self.title, 'status': self.status, 
		'account': self.account, 'info': self.info}
	
	def __repr__(self):
		names = self.title.split()
		if len(names) == 1:
			return self.title
		
		return f'{names[0]} {names[1][0]}.'	

class Trip(Base):
	__tablename__ = 'trip'
	id = Column('trip_id', Integer, primary_key=True)
	status = Column('trip_status', Integer)
	time = Column('trip_time', DateTime)
	route_id = Column('route_id', Integer, ForeignKey('route'))
	user_id = Column(Integer, ForeignKey('user.user_id'))
	admin_id = Column(Integer, ForeignKey('user.user_id'))
	stop = Column('trip_stop', String)
	message = Column('trip_message', String)
	route = relationship('Route')
	user = relationship('User', foreign_keys=[user_id])
	admin = relationship('User', foreign_keys=[admin_id])
	
	OK, CANCEL = 0, 1
	statuses = ('\u2714', '\u2718')

	def serialize(self):
		result = {'id': self.id, 'status': self.status, 'time': self.time, 
			'route':self.route_id,'user': self.user_id, 'admin': self.admin_id,
			'stop':self.stop, 'message':self.message}		
	
	
class Syslog(Base):
	__tablename__ = 'syslog'
	id = Column('syslog_id', Integer, primary_key=True)
	action = Column('syslog_action', Integer)
	time = Column('syslog_time', DateTime)
	user_id = Column('user_id', Integer, ForeignKey('user'))
	info = Column('syslog_info', String)
	user = relationship('User')
	LOGIN, CRUD, PASSW = 0, 1, 2
	actions = ('вход', 'изменение табл.', 'смена пароля')

	def serialize(self):
		result = {'id': self.id, 'action': self.action, 'time': self.time, 
			'info': self.info, 'user_id': self.user_id}
		
		if self.user:
			result['user'] = self.user.serialize()
		
		return result
		
class Log(Base):
	__tablename__ = 'log'
	id = Column('log_id', Integer, primary_key=True)
	action = Column('log_action', Integer)
	time = Column('log_time', DateTime)
	user_id = Column('user_id', Integer, ForeignKey('user'))
	info = Column('log_info', String)
	user = relationship('User')
	WRITEOFF, CANCEL, PAY = 0, 1, 2
	actions = ('поездка', 'отмена', 'оплата', )

	def serialize(self):
		result = {'id': self.id, 'action': self.action, 'time': self.time, 
			'info': self.info, 'user_id': self.user_id}
		
		if self.user:
			result['user'] = self.user.serialize()
		
		return result		
 
def crudPost(db, request, className):
	columns = request.form.to_dict()
	id = columns.pop('id')
	cmd = columns.pop('cmd')
	
			
	lib = importlib.import_module('Sborka.bus.entity')
	Entity = getattr(lib, className)
	try:
		
		if cmd == 'delete':
			entity = db.query(Entity).get(id)
			db.delete(entity)
			message = 'Запись удалена'
				
		else:
			if cmd == 'insert':	
				entity = Entity()
				db.add(entity)
				message = f' Запись ({entity.__class__.__name__}) добавлена'
		
			elif cmd == 'update':	
				entity = db.query(Entity).get(id)
				message = f'Запись ({entity.__class__.__name__}) изменена'
	
			for column, value in columns.items():
				attr = getattr(Entity, column)
				
				if 'Time' in attr.type.__class__.__name__:
					value = datetime.datetime.strptime(value, '%H:%M').time()
			
				setattr(entity, column, value)	
		
		log = Syslog()
		log.action = Syslog.CRUD 
		log.user_id = session['bus_user'].id
		log.time = datetime.datetime.now()
		log.info = message
		
		db.add(log)		
		db.commit()
		flash(message, category='success')
	
	except Exception as e:	
		#flash(e.orig, category='danger')
		flash(e, category='danger')
		db.rollback()

			 