#!/usr/bin/python


import sys
sys.path[0:0] = [
  '/opt/rockstor/src/rockstor',
  '/opt/rockstor/eggs/supervisor-3.0b1-py2.7.egg',
  '/opt/rockstor/eggs/meld3-1.0.2-py2.7.egg',
  '/opt/rockstor/eggs/setuptools-42.0.0-py2.7.egg',
  '/opt/rockstor/eggs/distro-1.4.0-py2.7.egg',
  '/opt/rockstor/eggs/six-1.10.0-py2.7.egg',
  '/opt/rockstor/eggs/requests-1.1.0-py2.7.egg',
  '/opt/rockstor/eggs/pyzmq-15.0.0-py2.7-linux-x86_64.egg',
  '/opt/rockstor/eggs/pytz-2014.3-py2.7.egg',
  '/opt/rockstor/eggs/python_socketio-1.6.0-py2.7.egg',
  '/opt/rockstor/eggs/psycopg2-2.7.4-py2.7-linux-x86_64.egg',
  '/opt/rockstor/eggs/psycogreen-1.0-py2.7.egg',
  '/opt/rockstor/eggs/psutil-3.3.0-py2.7-linux-x86_64.egg',
  '/opt/rockstor/eggs/mock-1.0.1-py2.7.egg',
  '/opt/rockstor/eggs/gevent_websocket-0.9.5-py2.7.egg',
  '/opt/rockstor/eggs/gevent-1.1.2-py2.7-linux-x86_64.egg',
  '/opt/rockstor/eggs/djangorestframework-3.1.1-py2.7.egg',
  '/opt/rockstor/eggs/django_ztask-0.1.5-py2.7.egg',
  '/opt/rockstor/eggs/django_pipeline-1.6.9-py2.7.egg',
  '/opt/rockstor/eggs/django_oauth_toolkit-0.9.0-py2.7.egg',
  '/opt/rockstor/eggs/Django-1.8.16-py2.7.egg',
  '/opt/rockstor/eggs/distribute-0.7.3-py2.7.egg',
  '/opt/rockstor/eggs/coverage-4.5.3-py2.7-linux-x86_64.egg',
  '/opt/rockstor/eggs/chardet-2.3.0-py2.7.egg',
  '/opt/rockstor/eggs/URLObject-2.1.1-py2.7.egg',
  '/opt/rockstor/eggs/python_engineio-3.8.1-py2.7.egg',
  '/opt/rockstor/eggs/greenlet-0.4.15-py2.7-linux-x86_64.egg',
  '/opt/rockstor/eggs/futures-3.2.0-py2.7.egg',
  '/opt/rockstor/eggs/oauthlib-1.0.1-py2.7.egg',
  '/opt/rockstor/eggs/django_braces-1.13.0-py2.7.egg',
  ]


from django.core import management

if __name__ == "__main__":
    management.execute_from_command_line()
