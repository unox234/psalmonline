#!/usr/bin/env python
import cgitb; cgitb.enable()
import os
import sys
from wsgiref.simple_server import make_server

# Path to your app.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import your Flask app
import app

# Run the WSGI server
if __name__ == '__main__':
    # Cottage-style server for CGI
    from wsgiref.handlers import CGIHandler
    CGIHandler().run(app.app)