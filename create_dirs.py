import os

dirs = [
    'app',
    'app/static',
    'app/static/css',
    'app/static/js',
    'app/static/img',
    'app/templates',
    'app/models'
]

for dir in dirs:
    os.makedirs(dir, exist_ok=True)
