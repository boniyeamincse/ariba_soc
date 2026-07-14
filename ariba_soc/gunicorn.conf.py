import multiprocessing

bind = '0.0.0.0:8000'
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 120
keepalive = 5

accesslog = '/var/log/ariba-soc/gunicorn-access.log'
errorlog = '/var/log/ariba-soc/gunicorn-error.log'
loglevel = 'info'

forwarded_allow_ips = '*'
reload = False
preload_app = True

worker_class = 'sync'
worker_connections = 1000
