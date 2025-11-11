.PHONY: up down migrate seed test clean

up:
	docker-compose up -d

down:
	docker-compose down

migrate:
	alembic upgrade head

seed:
	python -m cli.seed

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

