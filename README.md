# PBT205 - Contact Tracing

## Prerequisites

1. Docker Desktop Must be installed
   - This app was tested & developed with docker engine v27.2.0

2. You must install the rabbitmq image by running:
   ```bash
   docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4.0-management
   ```

3. The docker rabbitmq container must be running before trying to run the application
   - Can take 15 - 60 seconds for rabbitmq to startup

4. Python must be installed

## Instructions

The person application simulates the movement on the 10 x 10 grid. To run the application you must do the following (so long as prerequisites are met):

1. Clone the application from github:
   ```bash
   # Default clone to user folder
   git clone https://github.com/Cloud090/PBT205.git
   
   # Or clone to custom directory
   git clone https://github.com/Cloud090/PBT205.git [desired_clone_directory_here]
   ```

2. Open the projected directory in CMD
   - By default: `cd PBT205`
   - Or enter whatever directory you cloned it to

3. Switch to the James branch:
   ```bash
   git checkout James
   ```

4. To ensure the code is pulled from github:
   ```bash
   git pull
   ```

5. For all applications you can use **CTRL + C** to exit

6. BEFORE running any applications you must activate venv on windows:
   ```bash
   .\venv\scripts\activate
   ```
   - If you do not run venv it will return a not found error

### Person Application

1. Command format:
   ```bash
   python src\person.py [person-name] [speed]
   ```
   - person-name: name of the actor
   - speed: how fast they move (1 is faster - 10 slowest)
   - Example: `python src\person.py James 2`

2. It will print the coordinates everytime it moves & send it over rabbitmq
3. It is recommended to run at least 3+ people

### Tracker Application

1. Command:
   ```bash
   python src\tracker.py
   ```

2. Once run it will wait for messages from the person application & will keep track of all contacts
3. This only needs to be run once whilst running the person applications

### Query Application

1. Command usage:
   ```bash
   python src\query.py [person-name]
   ```
   Example: `python src\query.py James`

2. It will output a list of who, where, when and how many times the queried person has come into contact with specific people
3. This only needs to run every so often