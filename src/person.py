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
QUEUE_CONTACT_NOTIFICATIONS = 'contact_notifications_queue'
ROUTING_KEY_POSITION = 'position'
GRID_SIZE = 10  # Grid size (can be changed to 1000x1000)
USERNAME = 'guest'
PASSWORD = 'guest'

auth = HTTPBasicAuth(USERNAME, PASSWORD)
positions = {}  # Dictionary to track positions of all people

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

def print_contact_notification(payload, person_name):
    """Format and print the contact notification message."""
    if payload['person'] == person_name:
        print(f"You made contact with {payload['contact_person']} at {payload['timestamp']} @ {tuple(payload['location'])}")
    elif payload['contact_person'] == person_name:
        print(f"You made contact with {payload['person']} at {payload['timestamp']} @ {tuple(payload['location'])}")

def consume_contact_notifications(person_name):
    """Consume contact notifications from the contact_notifications queue."""
    consume_url = f'{RABBITMQ_API_URL}/queues/%2F/{QUEUE_CONTACT_NOTIFICATIONS}/get'
    
    try:
        response = requests.post(
            consume_url, 
            auth=auth, 
            json={
                'count': 1,
                'ackmode': 'ack_requeue_false',  # Changed to not requeue automatically
                'encoding': 'auto'
            }
        )
        
        if response.status_code == 200 and response.json():
            message = response.json()[0]
            payload = json.loads(message['payload'])
            
            # Check if this message is relevant for this person
            if payload['person'] == person_name or payload['contact_person'] == person_name:
                # Print the notification
                print_contact_notification(payload, person_name)
            else:
                # If message isn't for this person, requeue it
                publish_url = f'{RABBITMQ_API_URL}/exchanges/%2F/{EXCHANGE_NAME}/publish'
                requeue_message = {
                    'properties': {},
                    'routing_key': 'contact-notifications',
                    'payload': message['payload'],
                    'payload_encoding': 'string'
                }
                requests.post(publish_url, auth=auth, headers={'content-type': 'application/json'}, 
                            json=requeue_message)
                    
    except requests.exceptions.RequestException as e:
        print(f"Error while consuming notifications: {e}")

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
            # Check for contact notifications
            consume_contact_notifications(person)

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