# How To Set Up Flask with MongoDB and Docker
[source](https://www.digitalocean.com/community/tutorials/how-to-set-up-flask-with-mongodb-and-docker)


## Steps
### Step 1 — Writing the Stack Configuration in Docker Compose
Setup the `docker-compose.yml`
- lets you define your application infrastructure as individual services
- the services can be connected to each other
- each can have a *volume* attached to it for persistent storage
- Volumes are stored in a part of the host filesystem managed by Docker (`/var/lib/docker/volumes` on Linux)
- data in volumes can be exported or shared with other applications
- [How to Share Data Between the Docker Container and the Host](https://www.digitalocean.com/community/tutorials/how-to-share-data-between-the-docker-container-and-the-host)

```bash
mkdir flaskapp
cd flaskapp
nano docker-compose.yml
```

#### `docker-compose.yml`
> **build**: defines the `context`of the build. In this case, the `app`folder that will contain the `Dockerfile`
> **container_name**: define a name for each container
> **image**: specifies the image name and what the Docker image will be tagged as
> **restart** defines how the container should be restarted - in this case is *unless-stopped*. This means your containers will only be stopped when the Docker Engine is stopped/restarted or when you explicitly stop the containers. The benefit of his is that the containers will start automatically once the Docker Engine is restarted or any error occurs.
> **environment** contains the envirtonment variables that are passed to the container.
> **volume** defines the volumes the service is using. In this case, `appdata` is mounted inside the container at the `/var/www` directory.
> **depends_on** defines a service that Flask depends on to function properly. In this case, the app will depend on `mongodb` since the `mongodb`acts as the database for your application. It ensures that the `flask`service only runs if the `mongodb`service is running.
> **networks** specifies `frontend`and `backend` as the networks the `flask`service will have access to.
> **command** define the command that will be executed when the container is started
> **mongod -auth** will disable logging into the MongoDB shell without credentials, which will secure MongoDB by requiring authentication
> **MONGO_INITDB_ROOT_USERNAME**, **MONGO_INITDB_ROOT_PASSWORD** create a root user with the given credentials

MongoDB stores its data in `/data/db` by default, thereore the data in the `/data/db` folder will be written to the named volume `mongodbdata` for persistence. 

The `mongoDB` does not expose any ports, so the service will only be accessible through the `backend` network

**Bridge networks** allow the containers to communicate with each other
```yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```
It was defined two networks - *frontend* and *backend* - for the services to connect to. 
- the frontend services, such as Nginx, will connect to the *frontend* network since it needs to be publicly accessible. 
- Back-end services, such as MongoDB, wll connect to the *backend* network to prevent unauthorized access to the service.

**Volumes**
```yml
. . .
volumes:
  mongodbdata:
    driver: local
  appdata:
    driver: local
  nginxdata:
    driver: local
```

The `volumes` section declares the volumes that the application will use to persist data. Here it's defined the volumes *mongodbdata*, *appdata*, *nginxdata* for persisting you MongoDB databases, Flask application data, and the Nginx web server logs, respectively.
- All of these volumes use a *local* driver to store the data locally.
- The volumes are used to persist this data sot that data like your MongoDB databases and Nginx webserver logs could be lost once you restart the containers

### Step 2 — Writing the Flask and Web Server Dockerfiles
You can build containers to run your appliactions from a file called *Dockerfile*
- is a tool that enables you to create custom images that you can use to install the software requiredd by your application and configure your containers based on your requirements
- You can push the custo images you create to Docker Hub or any private registry 


#### Dockerfile
- the *ENV* directive is used to define the environment variables for our group and user ID
-  Linux Standard Base (LSB) specifies that UIDs and GIDs 0-99 are statically allocated by the system. UIDs 100-999 are supposed to be allocated dynamically for system users and groups. UIDs 1000-59999 are supposed to be dynamically allocated for user accounts. Keeping this in mind you can safely assign a UID and GID of 1000, furthermore you can change the UID/GID by updating the GROUP_ID and USER_ID to match your requirements.

By default, Docker containers run as the root user

To mitigate this security risk, this will create a new user and group that will only have access to the /var/www directory.

This code will first use the addgroup command to create a new group named www. The -g flag will set the group ID to the ENV GROUP_ID=1000 variable that is defined earlier in the Dockerfile.

The adduser -D -u $USER_ID -G www www -s /bin/sh lines creates a www user with a user ID of 1000, as defined by the ENV variable. The -s flag creates the user’s home directory if it does not exist and sets the default login shell to /bin/sh. The -G flag is used to set the user’s initial login group to www, which was created by the previous command.

The USER command defines that the programs run in the container will use the www user. Gunicorn will listen on :5000, so you will open this port with the EXPOSE command.

Finally, the CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi"] line runs the command to start the Gunicorn server with four workers listening on port 5000. The number should generally be between 2–4 workers per core in the server, Gunicorn documentation recommends (2 x $num_cores) + 1 as the number of workers to start with.


### Step 3 — Configuring the Nginx Reverse Proxy
This Nginx Dockerfile uses an alpine base image, which is a tiny Linux distribution with a minimal attack surface built for security.

In the RUN directive you are installing nginx as well as creating symbolic links to publish the error and access logs to the standard error (/dev/stderr) and output (/dev/stdout). Publishing errors to standard error and output is a best practice since containers are ephemeral, doing this the logs are shipped to docker logs and from there you can forward your logs to a logging service like the Elastic stack for persistance. After this is done, commands are run to remove the default.conf and /var/cache/apk/* to reduce the size of the resulting image. Executing all of these commands in a single RUN decreases the number of layers in the image, which also reduces the size of the resulting image.

The COPY directive copies the app.conf web server configuration inside of the container. The EXPOSE directive ensures the containers listen on ports :80 and :443, as your application will run on :80 with :443 as the secure port.


```bash
mkdir nginx/conf.d
nano nginx/conf.d/app.conf
```

This will first define the upstream server, which is commonly used to specify a web or app server for routing or load balancing.

Your upstream server, app_server, defines the server address with the server directive, which is identified by the container name flask:5000.

The configuration for the Nginx web server is defined in the server block. The listen directive defines the port number on which your server will listen for incoming requests. The error_log and access_log directives define the files for writing logs. The proxy_pass directive is used to set the upstream server for forwarding the requests to http://app_server.


### Step 4 — Creating the Flask To-do API

The Flask(__name__) loads the application object into the application variable. Next, the code builds the MongoDB connection string from the environment variables using os.environ. Passing the application object in to the PyMongo() method will give you the mongo object, which in turn gives you the db object from mongo.db.



The condition __name__ == "__main__" is used to check if the global variable, __name__, in the module is the entry point to your program, is "__main__", then run the application. If the __name__ is equal to "__main__" then the code inside the if block will execute the app using this command application.run(host='0.0.0.0', port=ENVIRONMENT_PORT, debug=ENVIRONMENT_DEBUG).


Next, we get the values for the ENVIRONMENT_DEBUG and ENVIRONMENT_PORT from the environment variables using os.environ.get(), using the key as the first parameter and default value as the second parameter. The application.run() sets the host, port, and debug values for the application.


#### `app/wsgi.py`
The wsgi.py file creates an application object (or callable) so that the server can use it. Each time a request comes, the server uses this application object to run the application’s request handlers upon parsing the URL.

This wsgi.py file imports the application object from the app.py file and creates an application object for the Gunicorn server.


### Step 5 — Building and Running the Containers
Since the services are defined in a single file, you need to issue a single command to start the containers, create the volumes, and set up the networks. This command also builds the image for your Flask application and the Nginx web server. Run the following command to build the containers:

`docker-compose up -d`

When running the command for the first time, it will download all of the necessary Docker images, which can take some time. Once the images are downloaded and stored in your local machine, docker-compose will create your containers. The -d flag daemonizes the process, which allows it to run as a background process.




### Step 6 — Creating a User for Your MongoDB Database
By default, MongoDB allows users to log in without credentials and grants unlimited privileges.

To do this, you will need the root username and password that you set in the docker-compose.yml file environment variables MONGO_INITDB_ROOT_USERNAME and MONGO_INITDB_ROOT_PASSWORD for the mongodb service. In general, it’s better to avoid using the root administrative account when interacting with the database. Instead, you will create a dedicated database user for your Flask application, as well as a new database that the Flask app will be allowed to access.

To create a new user, first start an interactive shell on the mongodb container:

`docker exec -it mongodb bash`
- You use the docker exec command in order to run a command inside a running container along with the -it flag to run an interactive shell inside the container.

Once inside the container, log in to the MongoDB root administrative account:

`mongo -U mongodbuser -p`

You will be prompted for the password that you entered as the value for the MONGO_INITDB_ROOT_PASSWORD variable in the docker-compose.yml file. The password can be changed by setting a new value for the MONGO_INITDB_ROOT_PASSWORD in the mongodb service, in which case you will have to re-run the docker-compose up -d command.

`show dbs;`
The admin database is a special database that grants administrative permissions to users. If a user has read access to the admin database, they will have read and write permissions to all other databases. Since the output lists the admin database, the user has access to this database and can therefore read and write to all other databases.

Saving the first to-do note will automatically create the MongoDB database. MongoDB allows you to switch to a database that does not exist using the use database command. It creates a database when a document is saved to a collection. Therefore the database is not created here; that will happen when you save your first to-do note in the database from the API. Execute the use command to switch to the flaskdb database:

`use flaskdb`

Next, create a new user that will be allowed to access this database:

```js
db.createUser({user: 'flaskuser', pwd: 'your password', roles: [{role: 'readWrite', db: 'flaskdb'}]})
exit
```
Log in to the authenticated database with the following command:

`mongo -u flaskuser -p your password --authenticationDatabase flaskdb`




### Step 7 — Running the Flask To-do App
`curl -i http://your_server_ip`

The configuration for the Flask application is passed to the application from the docker-compose.yml file. The configuration regarding the database connection is set using the MONGODB_* variables defined in the environment section of the flask service.

To test everything out, create a to-do note using the Flask API. You can do this with a POST curl request to the /todo route:

`curl -i -H "Content-Type: application/json" -X POST -d '{"todo": "Dockerize Flask application with MongoDB backend"}' http://your_server_ip/todo`

You can list all of the to-do notes from MongoDB with a GET request to the /todo route:

`curl -i http://your_server_ip/todo`
