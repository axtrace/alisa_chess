import config

user = 'www-data'
group = 'www-data'
bind = config.HOST_IP + ':5000'
workers = 1
threads = 4
accesslog = '-'
errorlog = '-'
timeout = 10
certfile = 'server.crt'
keyfile = 'server.key'