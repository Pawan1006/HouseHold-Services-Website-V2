# Import the create_app function from the web module
from web import create_app

# Create an instance of the Flask application
app = create_app()
# celery = celery_config(app)
# Entry point for running the application
if __name__ == "__main__":
    app.run(debug=True)


# redis-server (kill port if any by - sudo pkill redis-server)
# (connection on 192.168.29.118 - 
#     redis-cli -h 127.0.0.1 -p 6379
#     CONFIG SET protected-mode no value
#     )
# celery -A web.celery_config.celery worker --loglevel=info
# celery -A web.celery_config.celery beat --loglevel=info