UV := UV_CACHE_DIR=/tmp/.uv-cache uv

.PHONY: install sync dev deploy test

install: sync

sync:
	$(UV) sync

dev:
	$(UV) run pywrangler dev

deploy:
	$(UV) run pywrangler deploy

test:
	$(UV) run pytest -q

