# import redis
# from redis.exceptions import RedisError, ConnectionError
#
# redis.Redis().ping()
#
# from redis import Redis
# try:
#     Redis(socket_timeout=1.5).ping()
#     print("Redis connected")
# except:
#     print("Redis not connected")