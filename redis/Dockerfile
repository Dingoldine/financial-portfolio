FROM docker.io/library/redis:6.2.1

COPY redis.conf /redis.conf

EXPOSE 6379

CMD [ "redis-server", "/redis.conf" ]