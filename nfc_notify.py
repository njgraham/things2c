''' nfc - report NFC read

see https://nfcpy.readthedocs.org
ln -s ../nfcpy-0.10.2 nfcpy-0.10.2
'''

def main(mknfc, now, sleep, mk_client):
    clf = mknfc()
    term = lambda: now() - started > 2

    client = mk_client()

    def connected(tag, id='ac5b72cf-5b0f-4ac1-9ed8-5434f102d4cb'):
        data = tag.ndef.message[0].data[3:] if tag.ndef else None
        if data == id:
            print 'Detect authorized nfc!'
            client.reconnect()
            client.publish('/nfc/scan/data', data)

    while True:
        started = now()
        client.publish('/nfc/scan/status', 'scan')
        clf.connect(rdwr={'on-connect': connected},
                    terminate=term)
        sleep(2)

        

if __name__ == '__main__':
    def __tcb__():
        import os
        import sys
        import time
        
        sys.path.insert(1, os.path.join(os.path.split(sys.path[0])[0],
                                        'nfcpy-0.10.2'))
        import nfc
        from motionctl import _tcb_ as mqtt

        def now():
            return time.time()
        
        def mknfc():
            clf = nfc.ContactlessFrontend('usb')
            return clf

        return dict(mknfc=mknfc, now=now, sleep=time.sleep, **mqtt())
    main(**__tcb__())
