#!/usr/bin/env python
import requests
import random
import time
import json
import sys
from requests.auth import HTTPBasicAuth
from create import create_exchange_and_queues

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

def publish_position(person, x, y):
    """Publish the person's position to RabbitMQ via the HTTP API."""
    headers = {'content-type': 'application/json'}
    message = {
        'properties': {},
        'routing_key': ROUTING_KEY_POSITION,
        'payload': json.dumps({'person': person, 'x': x, 'y': y}),
        'payload_encoding': 'string'
    }
    
    # Publish the message to the exchange
    publish_url = f'{RABBITMQ_API_URL}/exchanges/%2F/{EXCHANGE_NAME}/publish'
    response = requests.post(publish_url, auth=auth, headers=headers, data=json.dumps(message))
    
    if response.status_code == 200:
        print(f"{person} moved to ({x}, {y})")
    else:
        print(f"Failed to publish position for {person}: {response.text}")

def move_person(person, move_speed):
    """Simulate the movement of a person on the grid."""
    x, y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)

    try:
        while True:
            # Random movement in any direction
            dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
            x = max(0, min(x + dx, GRID_SIZE - 1))
            y = max(0, min(y + dy, GRID_SIZE - 1))

            # Publish the new position to RabbitMQ
            publish_position(person, x, y)

            # Wait before next move
            time.sleep(move_speed)
    except KeyboardInterrupt:
        print(f"Stopped movement for {person}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python person.py <person_identifier> <move_speed>")
        sys.exit(1)
    create_exchange_and_queues()
    person_identifier = sys.argv[1].lower()
    move_speed = float(sys.argv[2])
    
    move_person(person_identifier, move_speed)