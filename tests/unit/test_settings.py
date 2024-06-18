from eduagent.defs import defs
from eduagent.settings import new_settings


def test_settings() -> None:
    settings = new_settings(defs.pathes.example_settings_file)
    print(settings)


def test_pg_vector_connection_string() -> None:
    settings = new_settings(defs.pathes.example_settings_file)
    assert settings.pg_vector.connection_string == "postgresql+psycopg://ysu_keg:123456789@db.eduagent:5432/eduagent"


