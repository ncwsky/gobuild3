#coding: utf-8
'''
task status : models.Build.status

initing -> pending -> building -> uploading -> done

when program start, reset all pending to initing
'''

import threading
import Queue
import time
import datetime

import models

que = Queue.Queue()
notify = Queue.Queue()

def loopwraper(fn):
    def _loopfn():
        while True:
            fn()
    t = threading.Thread(target=_loopfn)
    t.daemon = True
    t.start()
    return fn

with models.db_session:
    builds = models.select(b for b in models.Build if \
            b.status == 'pending')[:]
    for b in builds:
        b.status = 'initing'

@loopwraper
@models.db_session
def loop_task():
    builds = models.select(b for b in models.Build if b.status == 'initing')[:]
    for b in builds:
        b.status = 'pending'
        b.updated = datetime.datetime.today()
        que.put(b.id)
        print b.id
    msg = notify.get()

@loopwraper
def loop_alarm():
    notify.put('alarm')
    time.sleep(3.0)

@loopwraper
def loop_task_idle():
    time.sleep(10)
    que.put(0)
