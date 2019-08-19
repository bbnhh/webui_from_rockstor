#!/usr/bin/env python
import os
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(os.path.join(HERE, "..")))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
