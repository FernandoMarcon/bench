# Docker Essentials

- Docker Images
```bash
docker images
docker rmi docker_img
docker pull docker_img
docker push docker_img
```

- Build and Run Docker
```bash
docker build -t tutorials/simple-backend .
docker run -p 4000:4000 tutorials/simple-backend 
```

- Docker Containers
```bash
docker ps # list all the containers that are running
docker stop id
docker kill id
```

- Docker-Compose
```bash
docker-compose build
docker-compose up -d mongo
docker-compose up -d app
```