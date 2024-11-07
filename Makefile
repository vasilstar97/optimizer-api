SOURCE_DIR = app

# packages installing and updating

venv: #then source .venv/bin/activate
	python3 -m venv .venv

install:
	pip install -r requirements.txt

update:
	pip install -r requirements.txt --upgrade

# formatting

lint:
	pylint ${SOURCE_DIR}

format:
	isort ${SOURCE_DIR}
	black ${SOURCE_DIR}

# running

fastapi:
	fastapi run --reload

compose-dev:
	docker compose -f "docker-compose.dev.yml" up --build
