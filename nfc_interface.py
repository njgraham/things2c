from functools import partial
from Queue import Queue, Empty


def main(mk_nfc, cmd):
    import logging
    logging.basicConfig(format='%(asctime)s: %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', level=logging.DEBUG)
    log = logging.getLogger(__name__)
    nfc = mk_nfc(log=log)
    if cmd == 'read':
        nfc.read()
    elif cmd == 'write':
        nfc.write()
    else:
        raise NotImplementedError()


class NfcInterface(object):
    def __init__(self, nfc, now, log):
        self._log = log
        self._clf = nfc.ContactlessFrontend('usb')
        self._nfc = nfc
        self._now = now

    @classmethod
    def make(cls, nfc, now, log):
        return NfcInterface(nfc, now, log)

    def read(self, timeout=2):
        self._log.debug('NFC read(), timeout %d' % timeout)

        queue = Queue()
        started = self._now()

        def term():
            return self._now() - started > timeout

        def connected(tag):
            self._log.debug('NFC read() connected')
            data = tag.ndef.message[0].data if tag.ndef else None
            queue.put(data)

        constat = self._clf.connect(rdwr={'on-connect': connected},
                                    terminate=term)
        if constat is False:
            raise IOError('Connect returned False')

        try:
            data = queue.get(block=True, timeout=timeout)
        except Empty:
            data = None

        self._log.debug('NFC read() data: %s' % data)
        return data

    def write(self, data, timeout=2):
        started = self._now()

        def term():
            return self._now() - started > timeout

        def connected(tag):
            self._log.debug('NFC write() connected')

        tag = self._clf.connect(rdwr={'on-connect': connected},
                                terminate=term)

        msg = self._nfc.ndef.TextRecord()
        msg.text = data
        tag.ndef.message = self._nfc.ndef.Message(msg)

if __name__ == '__main__':
    def _tcb_():
        from os import path as ospath
        from sys import argv, path
        from time import time

        nfcpy_path = argv[1]
        path.insert(1, ospath.join(ospath.split(path[0])[0],
                                   nfcpy_path))
        import nfc

        def now():
            return time()

        return dict(mk_nfc=partial(NfcInterface.make, nfc=nfc, now=now),
                    cmd=argv[2] if argv[2] in ['read', 'write'] else None)
    main(**_tcb_())
