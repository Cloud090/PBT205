#!/usr/bin/env python
import requests # Importing librarys
import sys
import json
from requests.auth import HTTPBasicAuth
import time
from dotenv import load_dotenv
import uuid
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """
    Configuration class that loads and stores all necessary RabbitMQ connection and queue settings.
    Uses environment variables for security so username & password is not in code file
    """
    def __init__(self, env_path: Optional[str] = None):
        # Load environment variables from specified path or default to .env
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
            
        # Required credentials
        self.USERNAME = os.getenv('RABBITMQ_USERNAME')
        self.PASSWORD = os.getenv('RABBITMQ_PASSWORD')
        
        # RabbitMQ connection settings
        self.RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost') # Host where RabbitMQ server is running
        self.RABBITMQ_API_PORT = os.getenv('RABBITMQ_API_PORT', '15672') # Default RabbitMQ management API port

        # Exchange and routing configuration
        self.EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'contact_tracing') # Exchange for all contact tracing messages
        self.ROUTING_KEY_QUERY = os.getenv('ROUTING_KEY_QUERY', 'query') # Routing key for query requests
        self.ROUTING_KEY_RESPONSE = os.getenv('ROUTING_KEY_RESPONSE', 'query-response') # Routing key for query responses
        self.QUEUE_RESPONSE = os.getenv('QUEUE_RESPONSE', 'query_response_queue') # Queue name for receiving responses
    
    @property
    def api_url(self) -> str: # returns the base URL for the RabbitMQ HTTP API
        return f'http://{self.RABBITMQ_HOST}:{self.RABBITMQ_API_PORT}/api'

def publish_query(config: Config, person: str) -> str:
    """Send the query to RabbitMQ."""
    headers = {'content-type': 'application/json'}
    auth = HTTPBasicAuth(config.USERNAME, config.PASSWORD)
    query_id = str(uuid.uuid4())  # Generate unique ID to match response with request
    
    message = { # Message payload
        'properties': {},
        'routing_key': config.ROUTING_KEY_QUERY,
        'payload': json.dumps({
            'query_id': query_id,
            'query_person': person
        }),
        'payload_encoding': 'string'
    }
    
    publish_url = f'{config.api_url}/exchanges/%2F/{config.EXCHANGE_NAME}/publish'
    # Send request to RabbitMQ HTTP API
    response = requests.post(publish_url, auth=auth, headers=headers, data=json.dumps(message))
    
    if response.status_code != 200:
        print(f"Failed to send query for {person}: {response.text}")
        sys.exit(1)
        
    return query_id

def get_response(config: Config, expected_query_id: str):
    """Retrieve response for the specified query ID."""
    url = f'{config.api_url}/queues/%2F/{config.QUEUE_RESPONSE}/get'
    headers = {'content-type': 'application/json'}
    auth = HTTPBasicAuth(config.USERNAME, config.PASSWORD)
    
    while True:
        response = requests.post(
            url,
            auth=auth,
            headers=headers,
            data=json.dumps({
                "count": 1,
                "ackmode": "ack_requeue_false", # Remove message from queue after receiving
                "encoding": "auto"
            })
        )
        
        if response.status_code == 200:
            if response.json(): # If a message is returned
                message = response.json()[0]
                body = json.loads(message['payload'])
                
                # Check if this response matches the expected query ID
                if body.get('query_id') == expected_query_id:
                    formatted_response = format_response(body)
                    print(formatted_response)
                    sys.exit(0) # Exit successfully after printing response
            time.sleep(1) # Wait before next attempt
        else:
            print(f"Failed to get message from queue: {response.text}")
            break

def format_response(body: dict) -> str:
    # Formats the contact tracing response into a easily human-readable string.
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
                if isinstance(location, (list, tuple)) and len(location) == 3:
                    x, y, timestamp = location
                    output += f"    - Position: ({x}, {y}) at {timestamp}\n"
    
    return output.strip()

def query_person(config: Config, person: str):
    """Query contact history of a person via RabbitMQ HTTP API."""
    expected_query_id = publish_query(config, person)
    get_response(config, expected_query_id)

def main():
    #  Entry point of the script
    if len(sys.argv) != 2:
        print("Usage: python query.py <person_identifier>")
        sys.exit(1)

    try:
        config = Config() # Load configuration from environment
        person_identifier = sys.argv[1].lower()  # Convert to lowercase for consistency
        query_person(config, person_identifier)
    except KeyboardInterrupt:
        print("\nQuery interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()