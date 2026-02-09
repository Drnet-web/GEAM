#!/usr/bin/env python
from app import create_app
import sys

# Log su file per NSSM
sys.stdout = open("log.txt", "w")
sys.stderr = open("err.txt", "w")

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
