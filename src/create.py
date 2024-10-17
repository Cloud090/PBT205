#!/usr/bin/env python
import requests
import random
import time
import json
import sys
from requests.auth import HTTPBasicAuth

# Configuration
RABBITMQ_HOST = 'localhost'
RABBITMQ_API_PORT = '15672'  # Default port for RabbitMQ API
RABBITMQ_API_URL = f'http://{RABBITMQ_HOST}:{RABBITMQ_API_PORT}/api'
EXCHANGE_NAME = 'contact_tracing'
QUEUE_POSITION = 'position_queue'
QUEUE_QUERY = 'query_queue'
QUEUE_RESPONSE = 'query_response_queue'
ROUTING_KEY_POSITION = 'position'
GRID_SIZE = 10  # Grid size (can be changed to 1000x1000)
USERNAME = 'guest'
PASSWORD = 'guest'

auth = HTTPBasicAuth(USERNAME, PASSWORD)

def create_exchange_and_queues():
    """Create exchange and queues via RabbitMQ HTTP API."""
    headers = {'content-type': 'application/json'}

    # Create the exchange
    exchange_data = {
        'type': 'topic',
        'durable': True
    }
    exchange_url = f'{RABBITMQ_API_URL}/exchanges/%2F/{EXCHANGE_NAME}'
    requests.put(exchange_url, auth=auth, headers=headers, data=json.dumps(exchange_data))

    # Create position queue
    position_queue_data = {'durable': True}
    position_queue_url = f'{RABBITMQ_API_URL}/queues/%2F/{QUEUE_POSITION}'
    requests.put(position_queue_url, auth=auth, headers=headers, data=json.dumps(position_queue_data))

    # Create query queue
    query_queue_data = {'durable': True}
    query_queue_url = f'{RABBITMQ_API_URL}/queues/%2F/{QUEUE_QUERY}'
    requests.put(query_queue_url, auth=auth, headers=headers, data=json.dumps(query_queue_data))

    # Create query response queue
    response_queue_data = {'durable': True}
    response_queue_url = f'{RABBITMQ_API_URL}/queues/%2F/{QUEUE_RESPONSE}'
    requests.put(response_queue_url, auth=auth, headers=headers, data=json.dumps(response_queue_data))

    # Bind the queues to the exchange with the appropriate routing keys
    bind_data = {'routing_key': 'position'}
    bind_url = f'{RABBITMQ_API_URL}/bindings/%2F/e/{EXCHANGE_NAME}/q/{QUEUE_POSITION}'
    requests.post(bind_url, auth=auth, headers=headers, data=json.dumps(bind_data))

    bind_data = {'routing_key': 'query'}
    bind_url = f'{RABBITMQ_API_URL}/bindings/%2F/e/{EXCHANGE_NAME}/q/{QUEUE_QUERY}'
    requests.post(bind_url, auth=auth, headers=headers, data=json.dumps(bind_data))

    bind_data = {'routing_key': 'query-response'}
    bind_url = f'{RABBITMQ_API_URL}/bindings/%2F/e/{EXCHANGE_NAME}/q/{QUEUE_RESPONSE}'
    requests.post(bind_url, auth=auth, headers=headers, data=json.dumps(bind_data))