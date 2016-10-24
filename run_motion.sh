#/bin/bash
docker run --restart=always -h motion -d --name motion --privileged -v /dev/video0:/dev/video0 motion
