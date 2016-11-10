#/bin/bash
hg archive things2c.zip
# no-cache since Docker can't detect that things2c needs to be built
docker build --no-cache=true -f Dockerfile_things2c -t things2c .
