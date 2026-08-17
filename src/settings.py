import os


def get_from_env(env_var, *, default_value=None, setting_name=None, required=False):
    if setting_name is None:
        setting_name = env_var
    value_from_env = os.environ.get(env_var)
    if required and not value_from_env:
        raise RuntimeError(
            f"Env var {env_var} is required but is not set or blank (val={value_from_env})"
        )
    globals()[setting_name] = (
        value_from_env if value_from_env is not None else default_value
    )


# read env vars into settings variables
get_from_env("UDS_DBNAME")
get_from_env("UDS_USERNAME")
get_from_env("UDS_PASSWORD")
get_from_env("UDS_HOST")
get_from_env("UDS_PORT")
get_from_env("UDS_CONNECT_TIMEOUT")
get_from_env("UDS_QUERY_TIMEOUT")
get_from_env("SCHEMA_NAME")
get_from_env("RABBITMQ_USERNAME")
get_from_env("RABBITMQ_PASSWORD")
get_from_env("RABBITMQ_HOST")
get_from_env("RABBITMQ_PORT")
get_from_env("RABBITMQ_QUEUE")

get_from_env("FTPS_HOST")
get_from_env("FTPS_PORT", default_value=990)
get_from_env("FTPS_USERNAME")
get_from_env("FTPS_PASSWORD")

get_from_env("HASHER_API_HOSTNAME")
get_from_env("HASHER_API_PORT")

get_from_env("CABOODLE_DBNAME")
get_from_env("CABOODLE_USERNAME")
get_from_env("CABOODLE_PASSWORD")
get_from_env("CABOODLE_HOST")
get_from_env("CABOODLE_PORT")
get_from_env("CABOODLE_CONNECT_TIMEOUT")
get_from_env("CABOODLE_QUERY_TIMEOUT")
get_from_env("CABOODLE_TESTING")

get_from_env("LOG_LEVEL", default_value="INFO")

get_from_env("INSTANCE_NAME", required=True)
