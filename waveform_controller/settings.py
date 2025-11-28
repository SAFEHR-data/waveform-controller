import os
from pathlib import Path

def get_from_env(env_var, setting_name=None):
    if setting_name is None:
        setting_name = env_var
    globals()[setting_name] = os.environ.get(env_var)

# read env vars into settings variables
get_from_env("UDS_DBNAME")
get_from_env("UDS_USERNAME")
get_from_env("UDS_PASSWORD")
get_from_env("UDS_HOST")
get_from_env("UDS_PORT")
get_from_env("SCHEMA_NAME")
get_from_env("RABBITMQ_USERNAME")
get_from_env("RABBITMQ_PASSWORD")
get_from_env("RABBITMQ_HOST")
get_from_env("RABBITMQ_PORT")
get_from_env("RABBITMQ_QUEUE")
