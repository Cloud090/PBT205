# PBT205
Usage for chat application

# install rabbitmq-server on Linux
sudo apt install rabbitmq-server

# start rabbitmq server
service rabbitmq-server start

# on browser go to URL
http://localhost:15672  -login with guest:guest

# on a terminal -run the file server.py   - will start waiting for clients to send messages
python3 server.py

# on another terminal -run the file client.py  - client can type and send  messages.
python3 client.py

# Messages from the client are sent to the server and  will be displayed in the terminal running server.py

