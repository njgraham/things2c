#/bin/bash
docker run --restart=always -h broker -d --name broker -p 0.0.0.0:1883:1883 broker
