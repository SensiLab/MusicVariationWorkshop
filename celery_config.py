from kombu import Exchange, Queue

# Celery configuration
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'  # Use the Redis result backend
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'  # Use Redis as the message broker

# Define a Celery task queue
CELERY_QUEUES = (
    Queue('file_processing_queue', Exchange('file_processing_queue'), routing_key='file_processing_queue'),
)

# Specify the task queue for tasks
CELERY_DEFAULT_QUEUE = 'file_processing_queue'
CELERY_DEFAULT_ROUTING_KEY = 'file_processing_queue'
CELERY_DEFAULT_EXCHANGE = 'file_processing_queue'
CELERY_DEFAULT_DELIVERY_MODE = 'transient'
