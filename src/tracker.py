#!/usr/bin/env python
import requests
import json
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, HTTPError, RequestException
import threading
import signal
import sys
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional
import logging
from contextlib import contextmanager
from create import create_exchange_and_queues

# Configuration
@dataclass
class Config:
    """
    Configuration class that loads and stores all necessary RabbitMQ connection and queue settings.
    Uses environment variables for security so username & password is not in code file
    """
    # Load environment variables from .env file
    def __init__(self, env_path: Optional[str] = None):
        # Load environment variables from specified path or default to .env
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
            
        # Required credentials with secure fallbacks
        self.USERNAME = os.getenv('RABBITMQ_USERNAME')
        self.PASSWORD = os.getenv('RABBITMQ_PASSWORD')
        
        # Validate required credentials
        if not self.USERNAME or not self.PASSWORD:
            raise ValueError("Missing required credentials. Please check your .env file.")
        
        # Optional configuration with defaults
        self.RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
        self.RABBITMQ_API_PORT = os.getenv('RABBITMQ_API_PORT', '15672')
        self.EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'contact_tracing')
        self.QUEUE_POSITION = os.getenv('QUEUE_POSITION', 'position_queue')
        self.QUEUE_QUERY = os.getenv('QUEUE_QUERY', 'query_queue')
        self.QUEUE_RESPONSE = os.getenv('QUEUE_RESPONSE', 'query_response_queue')
        self.ROUTING_KEY_CONTACT_NOTIFICATIONS = os.getenv('ROUTING_KEY_CONTACT_NOTIFICATIONS', 'contact-notifications')
        self.QUEUE_CONTACT_NOTIFICATIONS = os.getenv('QUEUE_CONTACT_NOTIFICATIONS', 'contact_notifications_queue')
    
    @property
    def api_url(self) -> str:
        return f'http://{self.RABBITMQ_HOST}:{self.RABBITMQ_API_PORT}/api'
    
    def validate(self) -> bool:
        """Validate the configuration and return True if valid"""
        try:
            assert self.USERNAME, "USERNAME is required"
            assert self.PASSWORD, "PASSWORD is required"
            assert self.RABBITMQ_HOST, "RABBITMQ_HOST is required"
            assert self.RABBITMQ_API_PORT, "RABBITMQ_API_PORT is required"
            return True
        except AssertionError as e:
            logging.error(f"Configuration validation failed: {str(e)}")
            return False

class ContactTracker:
    def __init__(self, config: Config):
        self.config = config
        self.auth = HTTPBasicAuth(config.USERNAME, config.PASSWORD)
        self.shutdown_event = threading.Event()
        self.positions: Dict[str, Tuple[int, int]] = {}
        self.contacts: Dict[str, Dict[str, Dict[str, List]]] = {}
        self.setup_logging()
        try:
            create_exchange_and_queues()
        except Exception as e:
            self.logger.error(f"Failed to initialise queues: {e}")
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('contact_tracker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def error_handling(self, operation: str):
        """Context manager for consistent error handling"""
        try:
            yield
        except ConnectionError as e:
            if not self.shutdown_event.is_set():
                self.logger.error(f"Connection error during {operation}: {e}")
        except HTTPError as e:
            if not self.shutdown_event.is_set():
                self.logger.error(f"HTTP error during {operation}: {e.response.text}")
        except Exception as e:
            if not self.shutdown_event.is_set():
                self.logger.error(f"Unexpected error during {operation}: {e}")

    def consume_message(self, queue_name: str) -> Optional[dict]:
        """Consume a message with exponential backoff retry"""
        if self.shutdown_event.is_set():
            return None

        consume_url = f'{self.config.api_url}/queues/%2F/{queue_name}/get'
        
        for attempt in range(5):
            if self.shutdown_event.is_set():
                return None

            with self.error_handling(f"consuming message from {queue_name}"):
                response = requests.post(
                    consume_url,
                    auth=self.auth,
                    json={'count': 1, 'ackmode': 'ack_requeue_false', 'encoding': 'auto'}
                )
                response.raise_for_status()
                
                if response.status_code == 200 and response.json():
                    return response.json()[0]['payload']
                
                if attempt < 4:  # Don't sleep on last attempt
                    time.sleep(min(2 ** attempt, 30))  # Cap maximum delay at 30 seconds
                
        return None

    def publish_message(self, routing_key: str, message: dict):
        """Publish a message to RabbitMQ"""
        publish_url = f'{self.config.api_url}/exchanges/%2F/{self.config.EXCHANGE_NAME}/publish'
        
        payload = {
            'properties': {
                'delivery_mode': 2,
                'content_type': 'application/json'
            },
            'routing_key': routing_key,
            'payload': json.dumps(message),
            'payload_encoding': 'string'
        }

        with self.error_handling("publishing message"):
            response = requests.post(
                publish_url,
                auth=self.auth,
                headers={'content-type': 'application/json'},
                json=payload
            )
            response.raise_for_status()
            self.logger.debug(f"Published message: {message}")

    def record_contact(self, person1: str, person2: str, position: Tuple[int, int]):
        """Record a contact between two people and ensure both receive a notification"""
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        
        for p1, p2 in [(person1, person2), (person2, person1)]:
            if p1 not in self.contacts:
                self.contacts[p1] = {}
            if p2 not in self.contacts[p1]:
                self.contacts[p1][p2] = {'count': 0, 'locations': []}
                
            self.contacts[p1][p2]['count'] += 1
            self.contacts[p1][p2]['locations'].append((position[0], position[1], timestamp))

        # Publish notifications for both contacts in a single function call to avoid missing notifications
        self.publish_message(
            self.config.ROUTING_KEY_CONTACT_NOTIFICATIONS,
            {
                'person': person1,
                'contact_person': person2,
                'location': position,
                'timestamp': timestamp
            }
        )
        self.publish_message(
            self.config.ROUTING_KEY_CONTACT_NOTIFICATIONS,
            {
                'person': person2,
                'contact_person': person1,
                'location': position,
                'timestamp': timestamp
            }
        )

    def track_position(self):
        """Process a single position update"""
        message = self.consume_message(self.config.QUEUE_POSITION)
        if not message:
            return

        data = json.loads(message)
        person = data['person'].lower()
        new_position = (data['x'], data['y'])
        
        self.logger.info(f"Tracking {person} at {new_position}")
        self.positions[person] = new_position

        # Check for contacts at the same position
        for other_person, other_position in self.positions.items():
            if other_person != person and other_position == new_position:
                self.logger.info(f"Contact detected: {person} with {other_person} @ {new_position}")
                self.record_contact(person, other_person, new_position)

    def handle_query(self):
        """Handle a single query request"""
        message = self.consume_message(self.config.QUEUE_QUERY)
        if not message:
            return

        data = json.loads(message)
        query_id = data['query_id']
        query_person = data['query_person'].strip().lower()
        
        self.logger.info(f"Processing query {query_id} for {query_person}")
        
        contact_info = self.contacts.get(query_person, {})
        response = {
            'query_id': query_id,
            'contacts': contact_info if contact_info else 'no contact'
        }
        
        self.publish_message('query-response', response)
        self.logger.info(f"Query {query_id} processed and response sent")

    def run_thread(self, target, name):
        """Run a thread with proper exception handling"""
        try:
            while not self.shutdown_event.is_set():
                target()
                self.shutdown_event.wait(timeout=0.5)
        except Exception as e:
            if not self.shutdown_event.is_set():
                self.logger.error(f"Error in {name} thread: {e}")
                
    def shutdown(self):
        """Gracefully shutdown the tracker"""
        self.logger.info("Initiating shutdown sequence...")
        self.shutdown_event.set()

    def run(self):
        """Main execution method"""
        self.logger.info("Starting contact tracking system...")
        
        # Create threads
        position_thread = threading.Thread(
            target=lambda: self.run_thread(self.track_position, "position"),
            daemon=True
        )
        query_thread = threading.Thread(
            target=lambda: self.run_thread(self.handle_query, "query"),
            daemon=True
        )
        
        try:
            position_thread.start()
            query_thread.start()

            while not self.shutdown_event.is_set():
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()
            
            # Wait for threads to finish
            for thread, name in [(position_thread, "Position"), (query_thread, "Query")]:
                thread.join(timeout=2)
                if thread.is_alive():
                    self.logger.warning(f"{name} thread did not shutdown gracefully")
                else:
                    self.logger.info(f"{name} thread closed successfully")

def main():
    config = Config()
    tracker = ContactTracker(config)
    
    def signal_handler(signum, frame):
        tracker.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    tracker.run()

if __name__ == "__main__":
    main()