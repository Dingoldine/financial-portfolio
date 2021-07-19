# financial-portfolio

Portfolio analysis software

## KNOWN BUGS

CSS error on data table in Chrome browser
Can spam the /portfolio/update endpoint to fill up MQ queue

## Saved Commands

podman run --env-file="../env/rabbit.env" --hostname rabbit -p 5672:5672 -p 5671:5671 -p4369:4369 rabbitmq:3.8.9

podman run --env-file="../env/postgres.env" -p 5432:5432 docker.io/library/postgres:latest

oc adm policy add-scc-to-user anyuid -z default
