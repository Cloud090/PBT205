import pika
import sys
import json

class OrderNode:
    # Representing an order in the Binary Search Tree (BST)
    def __init__(self, order):
        self.order = order # The actual order
        self.left = None # Pointer to left child
        self.right = None # Pointer to the right child

class OrderBook:
    # Order book implemented in BST
    def __init__(self):
        self.root = None # Root of the BST

    def insert(self, order):
        try:
            price = float(order['price'])
            if price <= 0:
                raise ValueError("Price must be positive")
            if self.root is None:
                self.root = OrderNode(order)
            else:
                self._insert_rec(self.root, order)
        except (KeyError, ValueError) as e:
            print(f"Error inserting order: {e}")
            return False
        return True

    def _insert_rec(self, node, order):
        # Helper method for recursive insertion
        price = float(order['price'])
        if price < float(node.order['price']):
            if node.left is None:
                node.left = OrderNode(order) # Inserts new node on the left
            else:
                self._insert_rec(node.left, order) # Recur tp the left
        else:
            if node.right is None:
                node.right = OrderNode(order) # Insert new node on the right
            else:
                self._insert_rec(node.right, order) # Recur to the right
    
    def search(self, price):
        # Search for the best matching order
        return self._search_rec(self.root, price)

    def _search_rec(self, node, price):
        # Helper method for recursive search
        if node is None:
            return None # Price not found
        if float(node.order['price']) == price:
            return node.order # Exact match found
        elif float(node.order['price']) > price:
            return self._search_rec(node.left, price) # search left
        else:
            return self._search_rec(node.right, price) # Search right
        
    def delete(self, price):
        #Deletes an order at a specified price
        self.root, deleted_order = self._delete_rec(self.root, price)
        return deleted_order # return the deleted order

    def _delete_rec(self, node, price):
        # Helper method for recursive deletion
        if node is None:
            return node, None # Price not found
        if float(node.order['price']) == price:
            # Node with one child or no child
            if node.left is None:
                return node.right, node.order
            elif node.right is None:
                return node.left, node.order
            # Node with two children: get the inorder successor
            temp = self._min_value_node(node.right)
            node.order = temp.order # Copy the successor's content
            node.right, _ = self._delete_rec(node.right, float(temp.order['price'])) # Delete the inorder successor
            return node, temp.order
        elif float(node.order['price']) > price:
            node.left, deleted_order = self._delete_rec(node.left, price)
            return node, deleted_order # Return the current node
        else:
            node.right, deleted_order = self._delete_rec(node.right, price)
            return node, deleted_order # Return the current node
    
    def _min_value_node(self, node):
        # Finds the node with the minimum price in a given tree
        current = node
        while current.left is not None:
            current = current.left
        return current
    
    def in_order_traversal(self):
        # returns a list of orders in-order traversal
        return (self._in_order_rec(node.left) + [node.order] + self._in_order_rec(node.right))

    def _in_order_rec(self, node):
        # Helper method for in-order traversal
        return (self._in_order_rec(node.left) + [node.order] + self._in_order_rec(node.right)) if node else []

# Define an order book to store incoming orders
order_book = {
    'BUY': OrderBook(),
    'SELL': OrderBook()
}

def match_order(order):
    """Matches incoming orders with those in the order book."""
    global order_book
    
    try:
        # Extract values from the order
        username = order['username']
        side = order['side'].upper()
        quantity = int(order['quantity'])
        price = float(order['price'])
        stock_symbol = order.get('stock_symbol', 'XYZ')
    except (KeyError, ValueError, TypeError):
        print(f"Invalid order format: {order}")
        return

    print(f"Matching order: {order}")  # Debugging statement

    # Determine the opposite side of the order
    opposite_side = 'SELL' if side == 'BUY' else 'BUY'
    
    # Track if any match is found
    found_match = False
    
    # Search for potential matches
    matching_order = order_book[opposite_side].search(price)  # Look for matching orders

    # Check if a trade is possible
    if matching_order:
        existing_quantity = int(matching_order['quantity'])
        existing_price = float(matching_order['price'])

        print(f"Checking existing order: {existing_price}")  # Debugging statement

        # Determine if a trade is possible
        if (side == 'BUY' and price >= existing_price) or (side == 'SELL' and price <= existing_price):
            found_match = True  # A match is found
            trade_quantity = min(quantity, existing_quantity)
            trade_price = existing_price
            
            # Publish the trade with correct buyer and seller
            if side == 'BUY':
                publish_trade(username, matching_order['username'], stock_symbol, trade_price, trade_quantity)  # username is the buyer
            else:
                publish_trade(matching_order['username'], username, stock_symbol, trade_price, trade_quantity)  # username is the seller

            print(f"Trade published: {username} with {matching_order['username']} for {trade_quantity} @ ${trade_price}")  # Debugging statement

            # Update quantities in the order book
            if trade_quantity == existing_quantity:
                order_book[opposite_side].delete(existing_price)  # Remove matched order
            else:
                matching_order['quantity'] = existing_quantity - trade_quantity

            quantity -= trade_quantity

            if quantity == 0:
                return  # Full match

    # If there are remaining quantities, only add the order if no match was found
    if quantity > 0:
        if not found_match:  # Only add to the order book if no matches were found
            order['quantity'] = quantity  # Update the quantity before adding it
            order_book[side].insert(order)  
            print(f"Order added to book: {order}")  # Debugging statement
        else:
            print("Order partially matched; not adding to the book.")  # Debugging statement
    else:
        if not found_match:
            print("No match found; order not added to the book.")

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
    try:
        order = json.loads(body.decode())  # Decode the incoming order
        match_order(order)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to process order: {e}")

def consume_orders(middleware_endpoint):
    """Consumes orders from the 'orders' topic and processes them."""
    try:
        # Connect to RabbitMQ middleware
        connection = pika.BlockingConnection(pika.ConnectionParameters(middleware_endpoint))
        channel = connection.channel()

        channel.exchange_delete(exchange='Orders')

        # Declare the Orders exchange (durable)
        channel.exchange_declare(exchange='Orders', exchange_type='direct', durable=True)

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