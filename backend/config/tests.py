from django.conf import settings


def test_database_configured():
    """Test that database is configured correctly"""
    assert 'default' in settings.DATABASES
    database_engine = settings.DATABASES['default']['ENGINE']

    if database_engine == 'django.db.backends.sqlite3':
        database_name = str(settings.DATABASES['default']['NAME'])
        assert database_name.endswith('test_db.sqlite3') or database_name.startswith('file:memorydb_')
    else:
        assert database_engine == 'django.db.backends.mysql'


def test_rest_framework_configured():
    """Test that DRF is configured"""
    assert 'REST_FRAMEWORK' in dir(settings)
    assert 'DEFAULT_AUTHENTICATION_CLASSES' in settings.REST_FRAMEWORK


def test_installed_apps_includes_drf():
    """Test that DRF is in INSTALLED_APPS"""
    assert 'rest_framework' in settings.INSTALLED_APPS
