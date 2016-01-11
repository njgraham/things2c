from functools import partial


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
        self._now = now

    @classmethod
    def make(cls, nfc, now, log):
        return NfcInterface(nfc, now, log)

    def read(self, timeout=2):
        self._log.debug('NFC read(), timeout %d' % timeout)

        data = None
        started = self._now()
        def term():
            return self._now() - started > timeout

        def connected(tag):
            data = tag.ndef.message[0].data[3:] if tag.ndef else None

        self._clf.connect(rdwr={'on-connect': connected},
                          terminate=term)

        self._log.debug('NFC read() data: %s' % data)
        return data

    def write(self):
        raise NotImplementedError()

if __name__ == '__main__':
    def _tcb_():
        from os import path as ospath
        from sys import argv, path
        from time import time
        path.insert(1, ospath.join(ospath.split(path[0])[0],
                                    'nfcpy-0.10.2'))
        import nfc

        def now():
            return time()
            
        return dict(mk_nfc=partial(NfcInterface.make, nfc=nfc, now=now),
                    cmd=argv[1] if argv[1] in ['read', 'write'] else None)
    main(**_tcb_())

    