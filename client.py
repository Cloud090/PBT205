# import libraries
import pika
import json
import sys
import time
import threading
import uuid
import os

# create variables
username = None
connection = None
channel = None
username_valid = False
username_check_complete = False
our_correlation_id = None
username_responses = []
shutdown_event = threading.Event()

# send message function - checks for empty messages, checks if the channel is closed, formats the message and publishes the message
def send_message(channel, routing_key, message, is_system=False):
    if message.strip() == "" and not is_system:
        print("Empty message. Please type something.")
        return

    if channel.is_closed:
        print("Channel is closed, unable to send message.")
        return

    timestamp = time.strftime('%H:%M:%S', time.localtime())
    body = json.dumps({
        'sender': username if not is_system else 'SYSTEM',
        'message': message,
        'timestamp': timestamp,
        'is_system': is_system
    })
    channel.basic_publish(exchange='chat_exchange', routing_key=routing_key, body=body)
    if not is_system:
        print(f"[{timestamp}] {username}: {message}")   # prints time, username and message

# receive message function - decoding the JSON message body, extracts sender, message, timestamp and system flag and prints the message locally.
def receive_messages(channel, method, properties, body):
    data = json.loads(body)
    sender = data['sender']
    message = data['message']
    timestamp = data['timestamp']
    is_system = data.get('is_system', False)

    if sender != username:
        
        if is_system:
            print(f"[{timestamp}] {message}")
        else:
            print(f"[{timestamp}] {sender}: {message}")

# start receiving messages function - consuming messages from the given queue, handles exceptions

def start_receiving_messages(channel, queue_name):
    try:
        channel.basic_consume(queue=queue_name, on_message_callback=receive_messages, auto_ack=True)
        channel.start_consuming()
    except pika.exceptions.ChannelClosedByBroker as e:
        print(f"Channel closed by broker: {e}")  # prints error message
    except pika.exceptions.ChannelWrongStateError:
        print("Channel is closed, unable to consume messages.") # prints error message
    except Exception as e:
        print(f"An error occurred: {e}")  # prints error message

# check username function - declaring the queue, generates a unique ID for each user, defines a callback function, sends a message with username and check username request to the broker and waits for a response and  evaluates the response.
def check_username(channel):
    global username_valid, username_check_complete, username_responses, our_correlation_id
    result = channel.queue_declare(queue='', exclusive=True)
    response_queue = result.method.queue

    our_correlation_id = str(uuid.uuid4())

    def on_response(ch, method, props, body):
        global username_valid, username_check_complete, username_responses
        if props.correlation_id == our_correlation_id:
            response = body.decode()
            username_responses.append(response)

    channel.basic_consume(queue=response_queue, on_message_callback=on_response, auto_ack=True)

    
    channel.basic_publish(
        exchange='',
        routing_key='checkUsername_durable',
        properties=pika.BasicProperties(
            reply_to=response_queue,
            correlation_id=our_correlation_id
        ),
        body=json.dumps({'sender': username, 'message': 'check_username'})
    )
    
    timeout = 5  # 5 seconds timeout
    start_time = time.time()

    while time.time() - start_time < timeout:
        connection.process_data_events(time_limit=0.1)
        if username_responses:
            break

    username_check_complete = True
    # check for valid username
    if not username_responses:
        username_valid = True
    else:
        username_valid = all(response == '1' for response in username_responses)

    if not username_valid:
        print("Username is already taken. Please restart and try another one.") # prints error message if username is already taken
        shutdown_event.set()
        connection.close()
        sys.exit(1)
    else:
        send_message(channel, "chat.general\n", f"{username} has joined the chat room.", is_system=True)  # message user has joined the room

# handle username function - decodes the JSON message body, extracts the requested username and  compares the user ID to see if a response is required.
def handle_username_check(channel, method, properties, body):
    global our_correlation_id
    data = json.loads(body)
    requested_username = data['sender']
    

    # Only respond if this is not our own request
    if properties.correlation_id != our_correlation_id:
        response = '0' if requested_username.lower() == username.lower() else '1'
        channel.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=response
        )
    else:
       print("Connecting to the chat room!") # prints message connecting to the chat room
        
# main function - 
def main():
    global username, connection, channel
    # checks correct command is entered including the username
    if len(sys.argv) != 2:
        print("Usage: python client.py <Username>")
        sys.exit(1)

    username = sys.argv[1].lower()
    #  connection to rabbitmq
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()     
    # declares topic exchange
    channel.exchange_declare(exchange='chat_exchange', exchange_type='topic')
    result = channel.queue_declare('', exclusive=True)
    queue_name = result.method.queue

    # bind the queue to the chat-general routing key
    channel.queue_bind(exchange='chat_exchange', queue=queue_name, routing_key="chat.general")

    # Use the new durable queue for username checks
    username_check_queue = 'checkUsername_durable'
    try:
        # declares a queue name
        channel.queue_declare(queue=username_check_queue, durable=True)
    except pika.exceptions.ChannelClosedByBroker as e:
        # verifies username available
        if e.reply_code == 406 and 'inequivalent arg' in str(e):
            print(f"Warning: Queue '{username_check_queue}' already exists with different properties. Using existing queue.")
            # Reopen the channel as it was closed due to the exception
            channel = connection.channel()
        else:
            raise  # Re-raise the exception if it's not the one we're expecting
    # start consuming messages
    channel.basic_consume(queue=username_check_queue, on_message_callback=handle_username_check, auto_ack=True)

    check_username(channel)

    receive_thread = threading.Thread(target=start_receiving_messages, args=(channel, queue_name), daemon=True)
    receive_thread.start()
    print("Welcome to the chat room\nType exit to leave the chat room!") # print welcome message and info on how to exit program
    try:
        while True:
            # thread for receiving messages
            print("Enter Message: ", end='')
            message = input()
            if message.strip() == "exit":  # code to execute program exit when user types exit
               send_message(channel, "chat.general", f"{username} has left the chat room", is_system=True)
               shutdown_event.set()
               print(f"\n{username} has exited the chat room") # prints user has left the room
               break
            elif message.strip():
                send_message(channel, "chat.general", message)
    except KeyboardInterrupt:
        # sends a system message indicating the user has left the room
        send_message(channel, "chat.general", f"{username} has left the chat room", is_system=True)
        shutdown_event.set()
        connection.close() # close connection
        sys.exit() # exit program

if __name__ == '__main__':
    main()

