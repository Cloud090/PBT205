#!/usr/bin/env python
import requests
import json
import uuid
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, HTTPError

# Configuration
RABBITMQ_HOST = 'localhost'
RABBITMQ_API_PORT = '15672'  # Default port for RabbitMQ API
RABBITMQ_API_URL = f'http://{RABBITMQ_HOST}:{RABBITMQ_API_PORT}/api'
EXCHANGE_NAME = 'contact_tracing'
QUEUE_POSITION = 'position_queue'
QUEUE_QUERY = 'query_queue'
QUEUE_RESPONSE = 'query_response_queue'
USERNAME = 'guest'
PASSWORD = 'guest'

# Global state: tracking positions, contacts, and locations
positions = {}  # {person: (x, y)}
contacts = {}   # {person: {other_person: {count: int, locations: [(x, y, timestamp), ...]}}}

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

def publish_message(queue_name, routing_key, message):
    """Publish a message to a specific queue."""
    headers = {'content-type': 'application/json'}
    publish_data = {
        'properties': {},
        'routing_key': routing_key,
        'payload': json.dumps(message),
        'payload_encoding': 'string'
    }
    publish_url = f'{RABBITMQ_API_URL}/exchanges/%2F/{EXCHANGE_NAME}/publish'
    requests.post(publish_url, auth=auth, headers=headers, data=json.dumps(publish_data))

def consume_message(queue_name):
    """Consume a message from a specific queue."""
    consume_url = f'{RABBITMQ_API_URL}/queues/%2F/{queue_name}/get'
    
    for attempt in range(5):  # Retry up to 5 times
        try:
            response = requests.post(consume_url, auth=auth, json={'count': 1, 'ackmode': 'ack_requeue_false', 'encoding': 'auto', 'truncate': 50000})
            response.raise_for_status()  # Raise an error for bad responses
            
            if response.status_code == 200 and response.json():
                return response.json()[0]['payload']
            return None
        
        except ConnectionError as e:
            print(f"Connection error on attempt {attempt + 1}: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
        
        except HTTPError as e:
            print(f"HTTP error occurred: {e}")
            break  # Stop retrying on HTTP errors

    print("Max retries exceeded for consuming message.")
    return None

def track_position():
    """Consume and process position updates."""
    message = consume_message(QUEUE_POSITION)
    if message:
        message = json.loads(message)
        person = message['person'].lower()  # Convert to lowercase
        new_position = (message['x'], message['y'])

        print(f"Tracking {person} at {new_position}")

        previous_position = positions.get(person, None)
        positions[person] = new_position

        for other_person, other_position in positions.items():
            if other_person != person and other_position == new_position:
                print(f"{person} has come into contact with {other_person}")

                if person not in contacts:
                    contacts[person] = {}
                if other_person not in contacts[person]:
                    contacts[person][other_person] = {'count': 0, 'locations': []}

                if other_person not in contacts:
                    contacts[other_person] = {}
                if person not in contacts[other_person]:
                    contacts[other_person][person] = {'count': 0, 'locations': []}

                contacts[person][other_person]['count'] += 1
                contacts[other_person][person]['count'] += 1
                
                timestamp = datetime.now().isoformat()
                contacts[person][other_person]['locations'].append((new_position[0], new_position[1], timestamp))
                contacts[other_person][person]['locations'].append((new_position[0], new_position[1], timestamp))

        print(f"Updated contacts: {contacts}")

def handle_query():
    """Consume and handle query requests."""
    message = consume_message(QUEUE_QUERY)
    if message:
        message = json.loads(message)
        query_id = message['query_id']  # Fetch the unique query ID
        query_person = message['query_person'].strip().lower()  # Updated key name
        print(f"Received query for: {query_person} with ID: {query_id}")  # Log the received query

        contact_dict = contacts.get(query_person, {})

        if contact_dict:
            formatted_contacts = {
                other_person: {
                    'count': info['count'],
                    'locations': info['locations']
                } for other_person, info in contact_dict.items()
            }
            response = {
                'query_id': query_id,  # Use the same query ID in response
                'contacts': formatted_contacts
            }
        else:
            response = {
                'query_id': query_id,  # Use the same query ID in response
                'contacts': 'no contact'
            }

        # Publish response
        publish_message(QUEUE_RESPONSE, 'query-response', response)  # Using the existing publish_message
        print(f"Response published for {query_person} with ID: {query_id}: {response}")  # Log the response published

def main():
    # Setup RabbitMQ exchange and queues
    create_exchange_and_queues()

    print("Tracker is running. Waiting for position and query updates.")

    try:
        while True:
            # Track positions
            track_position()

            # Handle queries
            handle_query()
            
            time.sleep(1)  # Optional delay to avoid overwhelming the API
    except KeyboardInterrupt:
        print(f"Exited")

if __name__ == "__main__":
    main()