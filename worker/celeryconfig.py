timezone = 'Europe/Stockholm'
enable_utc = True
task_serializer = "json"
result_accept_content = ['json']
result_backend = 'redis://redisdb:6379/0'
task_routes = {
    'portfolio_worker.tasks.updatePortfolio': {
        'queue': 'default',
        'routing_key': 'default'
    }
}
accept_content = ['json']
result_serializer = 'json'
task_default_queue = 'default'
task_track_started = 'True'
task_default_exchange_type = 'direct'
task_default_routing_key = 'default'
