PYTHON := env/bin/python
PIP := env/bin/pip


$(PYTHON):
	rm -rf env
	virtualenv -p python3 env

$(PIP): $(PYTHON)

install: $(PIP)
	$(PIP) install -r requirements.txt

acquisition-preview:
	bash ./bin/start-acquisition-preview.sh $(tmp)

.PHONY: acquisition-preview
