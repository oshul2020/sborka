CREATE TABLE  IF NOT EXISTS 'route'(
	route_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	route_title TEXT NOT NULL,
	route_open INTEGER NOT NULL,
	route_start INTEGER NOT NULL,
	route_close INTEGER NOT NULL,
	route_days INTEGER NOT NULL,
	route_status INTEGER NOT NULL,
	route_bus TEXT,
	route_driver TEXT,
	route_contact TEXT,
	route_info TEXT,
	route_stops TEXT NOT NULL
);
	
CREATE TABLE  IF NOT EXISTS 'user'(
   user_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
   user_title TEXT NOT NULL UNIQUE,
   user_status INTEGER NOT NULL DEFAULT 0,
   user_account INTEGER DEFAULT 0,
   user_hash TEXT NOT NULL UNIQUE,
   user_info TEXT
);

CREATE TABLE  IF NOT EXISTS 'trip'(
	trip_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
	trip_time INTEGER NOT NULL,
	trip_status INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	route_id INTEGER NOT NULL,
	admin_id INTEGER,
	trip_stop TEXT,
	trip_message TEXT,
	FOREIGN KEY(user_id) REFERENCES user(user_id),
	FOREIGN KEY(route_id) REFERENCES route(route_id),
	FOREIGN KEY(admin_id) REFERENCES user(user_id)
);

CREATE TABLE  IF NOT EXISTS 'log'(
   log_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
   log_action INTEGER NOT NULL,
   log_time INTEGER NOT NULL,
   log_info TEXT, 
   user_id INTEGER NOT NULL,
   FOREIGN KEY(user_id) REFERENCES user(user_id)
);

CREATE TABLE  IF NOT EXISTS 'syslog'(
   syslog_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
   syslog_action INTEGER NOT NULL,
   syslog_time INTEGER NOT NULL,
   syslog_info TEXT, 
   user_id INTEGER NOT NULL,
   FOREIGN KEY(user_id) REFERENCES user(user_id)
);

INSERT INTO user (user_title, user_hash, user_status, user_account, user_info) VALUES 
	("Шуляк Александр", "95f44e0321ed96ba9d2961a54daab05e", "4", "0", "dev");

INSERT INTO route (route_title, route_open, route_start, route_close, route_days, 
		route_status, route_bus, route_driver, route_contact, route_info, route_stops) VALUES
		('название', '00:00:00.000000', '00:00:00.000000', '00:00:00.000000', 0, 0, 'модель', 
		'водитель', 'контакт', '', 'Остановка1');	