# PBT205

# Required software 
- Python3.6+
- install Pika libary  (pip install pika)
- install RabbitMQ

# Two main scripts
- Sending orders (sendOrder.py)
- Processing orders (exchange.py)


                -- # Running the trade system --

# Sending Oders

- python3 sendOrder.py <username> <host> <action> --quantity <quantity> <price>

-- example: python3 sendOrder.py user1 localhost BUY --quantity 100 150.0

Parameters:
<username>: The username of the user sending the order (e.g., user1, user2).
<host>: The RabbitMQ server host (usually localhost).
<action>: The action to perform (BUY or SELL).
--quantity <quantity>: The quantity of stock to buy or sell.
<price>: The price per unit of stock.
 
 

# Processing Orders (open a new terminal)

- Navigate to the project directory ( cd PBT205 )
- python3 exchange.py 

 This script will process any orders sent through the Orders exchange and display the output in the terminal. 






