.PHONY: install run test migrate

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

test:
	python -m pytest

migrate:
	python -m alembic -c alembic.ini upgrade head