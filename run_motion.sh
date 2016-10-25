#/bin/bash
if ! docker volume ls | grep -q motion; then
    echo "Creating motion volume"
    docker volume create --name motion
else
    echo "motion volume already created"
fi
docker run --restart=always -h motion -d --name motion -p 127.0.0.1:8181:8081 --privileged -v motion:/var/lib/motion -v /dev/video0:/dev/video0 motion
