#!/usr/bin/env python
import requests
import random
import time
import json
import sys
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from dotenv import load_dotenv
import logging
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
from contextlib import contextmanager
from create import create_exchange_and_queues

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
        
        # Validate required credentials
        if not self.USERNAME or not self.PASSWORD:
            raise ValueError("Missing required credentials. Please check your .env file.")

        # Configuration
        self.RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
        self.RABBITMQ_API_PORT = os.getenv('RABBITMQ_API_PORT', '15672')  # Default port for RabbitMQ API
        self.EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'contact_tracing')
        self.QUEUE_POSITION = os.getenv('QUEUE_POSITION', 'position_queue')
        self.QUEUE_QUERY = 'query_queue'
        self.QUEUE_RESPONSE = 'query_response_queue'
        self.QUEUE_CONTACT_NOTIFICATIONS = os.getenv('QUEUE_CONTACT_NOTIFICATIONS', 'contact_notifications_queue')
        self.ROUTING_KEY_POSITION = os.getenv('ROUTING_KEY_POSITION', 'position')
        self.GRID_SIZE = int(os.getenv('GRID_SIZE', '10'))

        #timestamp format configuration
        self.TIMESTAMP_FORMAT = os.getenv('TIMESTAMP_FORMAT', '%d-%m-%Y %H:%M:%S')
    
    @property
    def api_url(self) -> str:
        return f'http://{self.RABBITMQ_HOST}:{self.RABBITMQ_API_PORT}/api'

class Person:
    def __init__(self, config: Config, person_identifier: str, move_speed: float):
        self.config = config
        self.person_identifier = person_identifier.lower()
        self.move_speed = move_speed
        self.auth = HTTPBasicAuth(config.USERNAME, config.PASSWORD)
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'person_{self.person_identifier}.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def error_handling(self, operation: str):
        """Context manager for consistent error handling"""
        try:
            yield
        except RequestException as e:
            self.logger.error(f"Request error during {operation}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during {operation}: {e}")

    def publish_position(self, x: int, y: int):
        """Publish the person's position to RabbitMQ via the HTTP API."""
        message = {
            'properties': {},
            'routing_key': self.config.ROUTING_KEY_POSITION,
            'payload': json.dumps({'person': self.person_identifier, 'x': x, 'y': y}),
            'payload_encoding': 'string'
        }
        
        publish_url = f'{self.config.api_url}/exchanges/%2F/{self.config.EXCHANGE_NAME}/publish'
        
        with self.error_handling("publishing position"):
            response = requests.post(
                publish_url,
                auth=self.auth,
                headers={'content-type': 'application/json'},
                json=message
            )
            response.raise_for_status()
            self.logger.info(f"Moved to ({x}, {y})")

    def print_contact_notification(self, payload: dict):
        """Format and print the contact notification message."""
        if payload['person'] == self.person_identifier:
            print(f"You made contact with {payload['contact_person']} at {payload['timestamp']} @ {tuple(payload['location'])}")
        elif payload['contact_person'] == self.person_identifier:
            print(f"You made contact with {payload['person']} at {payload['timestamp']} @ {tuple(payload['location'])}")

    def consume_contact_notifications(self):
        """Consume contact notifications from the contact_notifications queue."""
        consume_url = f'{self.config.api_url}/queues/%2F/{self.config.QUEUE_CONTACT_NOTIFICATIONS}/get'
        
        with self.error_handling("consuming notifications"):
            response = requests.post(
                consume_url,
                auth=self.auth,
                json={
                    'count': 1,
                    'ackmode': 'ack_requeue_false',
                    'encoding': 'auto'
                }
            )
            response.raise_for_status()
            
            if response.status_code == 200 and response.json():
                message = response.json()[0]
                payload = json.loads(message['payload'])
                
                # Check if this message is relevant for this person
                if payload['person'] == self.person_identifier or payload['contact_person'] == self.person_identifier:
                    self.print_contact_notification(payload)
                else:
                    # If message isn't for this person, requeue it
                    self.requeue_notification(message['payload'])

    def requeue_notification(self, payload: str):
        """Requeue a notification that wasn't meant for this person."""
        publish_url = f'{self.config.api_url}/exchanges/%2F/{self.config.EXCHANGE_NAME}/publish'
        
        message = {
            'properties': {},
            'routing_key': 'contact-notifications',
            'payload': payload,
            'payload_encoding': 'string'
        }
        
        with self.error_handling("requeuing notification"):
            response = requests.post(
                publish_url,
                auth=self.auth,
                headers={'content-type': 'application/json'},
                json=message
            )
            response.raise_for_status()

    def move(self):
        """Simulate the movement of a person on the grid."""
        x, y = random.randint(0, self.config.GRID_SIZE - 1), random.randint(0, self.config.GRID_SIZE - 1)
        self.logger.info(f"Starting at position ({x}, {y})")

        try:
            while True:
                # Random movement in any direction
                dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                x = max(0, min(x + dx, self.config.GRID_SIZE - 1))
                y = max(0, min(y + dy, self.config.GRID_SIZE - 1))

                # Publish the new position
                self.publish_position(x, y)
                
                # Check for contact notifications
                self.consume_contact_notifications()

                # Wait before next move
                time.sleep(self.move_speed)
                
        except KeyboardInterrupt:
            self.logger.info("Movement stopped by user")
            sys.exit(0)

def main():
    if len(sys.argv) != 3:
        print("Usage: python person.py <person_identifier> <move_speed>")
        sys.exit(1)

    try:
        config = Config()
        person_identifier = sys.argv[1]
        move_speed = float(sys.argv[2])
        
        # Initialize queues
        create_exchange_and_queues()
        
        # Create and run person
        person = Person(config, person_identifier, move_speed)
        person.move()
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()