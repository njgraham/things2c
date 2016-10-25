#/bin/bash
docker run --restart=always -h motion -d --name motion -p 127.0.0.1:8181:8081 --privileged -v /dev/video0:/dev/video0 motion
