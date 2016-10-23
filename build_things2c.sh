#/bin/bash
hg archive things2c.zip
docker build -f Dockerfile_things2c -t things2c .
