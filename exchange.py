import pika
import sys
import json

# Define an order book to store incoming orders
order_book = {
    'BUY': [],
    'SELL': []
}

def match_order(order):
    """Matches incoming orders with those in the order book."""
    global order_book
    
    username, side, quantity, price, stock_symbol = order
    quantity = int(quantity)  # Ensure quantity is an integer
    price = float(price)      # Ensure price is a float
    
    # Determine the opposite side of the order (BUY matches SELL and vice versa)
    opposite_side = 'SELL' if side == 'BUY' else 'BUY'
    
    # Check for matching orders in the order book on the opposite side
    for existing_order in order_book[opposite_side]:
        existing_username, existing_side, existing_quantity, existing_price, existing_stock_symbol = existing_order
        existing_quantity = int(existing_quantity)
        existing_price = float(existing_price)
        
        # Determine if a trade is possible
        if (side == 'BUY' and price >= existing_price) or (side == 'SELL' and price <= existing_price):
            # A match is found, handle partial or full match
            trade_quantity = min(quantity, existing_quantity)  # Match the minimum quantity
            trade_price = existing_price  # Use the price of the existing order

            # Publish the trade
            publish_trade(username, existing_username, stock_symbol, trade_price, trade_quantity)

            # Update quantities in order book
            if trade_quantity == existing_quantity:
                # Full match, remove the existing order
                order_book[opposite_side].remove(existing_order)
            else:
                # Partial match, update the remaining quantity of the existing order
                existing_order[2] = existing_quantity - trade_quantity

            # Decrease the quantity of the new order
            quantity -= trade_quantity

            if quantity == 0:
                return  # Full match
    
    # If no full match, add remaining quantity to the order book
    if quantity > 0:
        order[2] = quantity  # Update the quantity before adding it
        order_book[side].append(order)

def publish_trade(buyer, seller, stock_symbol, price, quantity):
    """Publishes trade information to the 'trades' topic."""
    try:
        # Connect to RabbitMQ middleware
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        # Declare the Trades exchange (durable)
        channel.exchange_declare(exchange='Trades', exchange_type='direct', durable=True)

        # Create the trade message
        trade_message = json.dumps({
            'buyer': buyer,
            'seller': seller,
            'stock_symbol': stock_symbol,
            'price': price,
            'quantity': quantity
        })

        # Publish the message to the 'Trades' exchange
        channel.basic_publish(exchange='Trades', routing_key='trades', body=trade_message)
        print(f"[x] Trade published: {trade_message}")

        # Close the connection
        connection.close()
    except pika.exceptions.AMQPError as e:
        print(f"Error publishing trade: {e}")

def callback(ch, method, properties, body):
    """Handles incoming orders from the 'orders' topic."""
    order = json.loads(body.decode())  # Decode the incoming order
    match_order(order)

def consume_orders(middleware_endpoint):
    """Consumes orders from the 'orders' topic and processes them."""
    try:
        # Connect to RabbitMQ middleware
        connection = pika.BlockingConnection(pika.ConnectionParameters(middleware_endpoint))
        channel = connection.channel()

        # Declare the Orders exchange (durable)
        channel.exchange_declare(exchange='Orders', exchange_type='topic', durable=True)

        # Declare a temporary queue for the current session
        result = channel.queue_declare('', exclusive=True, durable=False)
        queue_name = result.method.queue

        # Bind the queue to the Orders exchange using the routing key 'order.new'
        channel.queue_bind(exchange='Orders', queue=queue_name, routing_key='order.new')

        print(' [*] Waiting for orders. To exit press CTRL+C')

        # Start consuming orders
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError as e:
        print(f"Error: Unable to connect to RabbitMQ at {middleware_endpoint}. Details: {e}")
        sys.exit(1)
    except pika.exceptions.AMQPError as e:
        print(f"Error with RabbitMQ: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure that the middleware endpoint argument is provided
    if len(sys.argv) != 2:
        print("Usage: python exchange.py <middleware_endpoint>")
        sys.exit(1)

    # Set the middleware endpoint from the command-line argument
    middleware_endpoint = sys.argv[1]

    # Start consuming orders from the provided RabbitMQ endpoint
    consume_orders(middleware_endpoint)
