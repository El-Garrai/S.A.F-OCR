import multiprocessing

bind = "0.0.0.0:80"
workers = multiprocessing.cpu_count()
accesslog = "/tmp/ocr.access.log"
timeout = 300
wsgi_app = "ocr:app"
