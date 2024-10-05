#!/usr/bin/env python
import requests
import sys
import json
from requests.auth import HTTPBasicAuth
import time
import uuid

# Configuration
RABBITMQ_HOST = 'localhost'
RABBITMQ_API_PORT = '15672'  # Default port for RabbitMQ API
RABBITMQ_API_URL = f'http://{RABBITMQ_HOST}:{RABBITMQ_API_PORT}/api'
EXCHANGE_NAME = 'contact_tracing'
ROUTING_KEY_QUERY = 'query'
ROUTING_KEY_RESPONSE = 'query-response'
QUEUE_RESPONSE = 'query_response_queue'
USERNAME = 'guest'
PASSWORD = 'guest'

auth = HTTPBasicAuth(USERNAME, PASSWORD)

def publish_query(person):
    """Send the query to RabbitMQ."""
    headers = {'content-type': 'application/json'}
    query_id = str(uuid.uuid4())  # Unique query ID for this request
    message = {
        'properties': {},
        'routing_key': ROUTING_KEY_QUERY,
        'payload': json.dumps({
            'query_id': query_id,  # Include the unique query ID
            'query_person': person
        }),
        'payload_encoding': 'string'
    }

    publish_url = f'{RABBITMQ_API_URL}/exchanges/%2F/{EXCHANGE_NAME}/publish'
    
    response = requests.post(publish_url, auth=auth, headers=headers, data=json.dumps(message))
    
    if response.status_code != 200:
        print(f"Failed to send query for {person}: {response.text}")
        sys.exit(1)

    return query_id  # Return the query ID for further use

def get_response(expected_query_id):
    """Retrieve response for the specified query ID."""
    url = f'{RABBITMQ_API_URL}/queues/%2F/{QUEUE_RESPONSE}/get'
    headers = {'content-type': 'application/json'}
    
    while True:
        response = requests.post(url, auth=auth, headers=headers, data=json.dumps({"count": 1, "ackmode": "ack_requeue_false", "encoding": "auto"}))
        
        if response.status_code == 200:
            if response.json():
                message = response.json()[0]
                body = json.loads(message['payload'])
                
                # Check if this response matches the expected query ID
                if body.get('query_id') == expected_query_id:
                    formatted_response = format_response(body)  # Get the formatted response
                    print(formatted_response)  # Print the formatted response
                    sys.exit(0)  # Exit immediately after printing the response
                # Ignore messages with mismatched IDs
            # Retry if there's no response yet
            time.sleep(1)
        else:
            print(f"Failed to get message from queue: {response.text}")
            break

def format_response(body):
    """Format the response for readability."""
    contacts = body.get('contacts')
    output = ""

    if contacts is None or contacts == 'no contact':
        output += "No contacts found.\n"
    else:
        output += "Contact history:\n"
        for contact_name, contact_details in contacts.items():
            output += f"- {contact_name}:\n"
            output += f"  Total encounters: {contact_details['count']}\n"
            output += f"  Locations:\n"
            for location in contact_details['locations']:
                # Ensure location is in the format you want to display
                if isinstance(location, list) and len(location) == 3:
                    x, y, timestamp = location
                    output += f"    - Position: ({x}, {y}) at {timestamp}\n"
    return output.strip()  # Remove trailing newlines

def query_person(person):
    """Query contact history of a person via RabbitMQ HTTP API."""
    expected_query_id = publish_query(person)  # Publish the query and get the ID
    get_response(expected_query_id)  # Get the formatted response and exit

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python query.py <person_identifier>")
        sys.exit(1)

    person_identifier = sys.argv[1].lower()
    query_person(person_identifier)