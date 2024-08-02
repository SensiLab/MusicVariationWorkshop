## Celery
Run Celery using the following command:

`celery -A main.celery worker --loglevel=info --without-gossip --pool=solo`