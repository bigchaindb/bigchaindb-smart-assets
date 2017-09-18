all: build init start

build:
	docker-compose build mdb
	docker-compose build bdb

init: reinit_db

start:
	docker-compose up -d bdb

restart: init start

drop_db:
	docker-compose stop mdb
	docker-compose rm -f mdb

start_db:
	docker-compose up -d mdb

run: init start

reinit_db: drop_db start_db
	sleep 1

stop:
	docker-compose down