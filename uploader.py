'''
>>> from time import sleep
>>> from Queue import Empty

>>> log = MockLog()
>>> test(log=log,
...      mk_uq=partial(UploadQueue.make, log, MockMqtt.make),
...      sleep=sleep)
>>> while not log.q.empty():
...     print log.q.get_nowait()
Process Uploader-1 is alive!
Process Uploader-2 is alive!
MockMqtt:publish(topic,start_1)
begin upload file_1
finishing upload file_1
MockMqtt:publish(topic,end_1)
Process Uploader-1 is exiting!
Process Uploader-3 is alive!
MockMqtt:publish(topic,start_3)
begin upload file_3
MockMqtt:publish(topic,cancel_2)
Process Uploader-2 is exiting!
finishing upload file_3
MockMqtt:publish(topic,end_3)
Process Uploader-3 is exiting!
'''
from functools import partial
from multiprocessing import Process, Queue
from Queue import Empty


def test(log, mk_uq, sleep):
    ''' Test the queued uploader - queue 3 files so that:
     - file_1 uploads but file_2 is cancelled while waiting
     - meanwhile, file_3 (already in progress) is allowed to finish

    Note: It's not completely deterministic when these processes
    run/finish.  So, the scheduling/processing load of the machine
    may cause the test to fail.  Sleep times are chosen to make
    passing very likely.
    '''
    def upload(log, msg):
        log.debug('begin upload %s' % msg)
        sleep(1)
        log.debug('finishing upload %s' % msg)

    uq = mk_uq()
    for (wait_time, sleep_between), (fname, args) in zip(
            ((3, 0.1), (5, 4), (0, 0.5)), [('file_%s' % i,
                                            tuple([('topic', m)
                                                   for m in
                                                   ['start_%s' % i,
                                                    'end_%s' % i,
                                                    'cancel_%s' % i]]))
                                           for i in range(1, 4)]):
        uq.queue(partial(upload, log, fname), wait_time, *args)
        sleep(sleep_between)
    uq.cancel()
    uq._join_all()


class Uploader(Process):
    def __init__(self, log, q, timeout, upload, mqtt,
                 start_msg, end_msg, cancel_msg):
        super(Uploader, self).__init__()
        self._log = log
        self._q = q
        self._timeout = timeout
        self._upload = upload
        self._mqtt = mqtt
        self._start_msg = start_msg
        self._end_msg = end_msg
        self._cancel_msg = cancel_msg

    def run(self):
        self._log.debug('Process %s is alive!' % self.name)
        try:
            self._q.get(timeout=self._timeout)
            self._mqtt.publish(*self._cancel_msg)
        except Empty:
            self._mqtt.publish(*self._start_msg)
            self._upload()
            self._mqtt.publish(*self._end_msg)
        self._log.debug('Process %s is exiting!' % self.name)

    def cancel(self):
        self._q.put(None)


class UploadQueue(object):
    def __init__(self, log, mk_mqtt):
        self._log = log
        self._mk_mqtt = mk_mqtt
        self._ul_list = list()

    @classmethod
    def make(cls, log, mk_mqtt):
        return UploadQueue(log, mk_mqtt)

    def queue(self, upload, timeout, start_msg, end_msg, cancel_msg):
        p = Uploader(self._log, Queue(), timeout,
                     upload=upload, mqtt=self._mk_mqtt(log=self._log),
                     start_msg=start_msg, end_msg=end_msg,
                     cancel_msg=cancel_msg)
        self._ul_list.append(p)
        p.start()

    def cancel(self):
        for p in self._ul_list:
            p.cancel()

    def _join_all(self):
        for p in self._ul_list:
            p.join()


class MockLog(object):
    def __init__(self):
        self.q = Queue()

    def debug(self, msg):
        self.q.put(msg)


class MockMqtt(object):
    def __init__(self, log):
        self._log = log

    @classmethod
    def make(cls, log):
        return MockMqtt(log)

    def publish(self, topic, payload):
        self._log.debug('MockMqtt:publish(%s,%s)' % (topic, payload))
