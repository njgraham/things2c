''' nfc - report NFC read

see https://nfcpy.readthedocs.org
ln -s ../nfcpy-0.10.2 nfcpy-0.10.2
'''

def main(mknfc, now, sleep):
    clf = mknfc()
    term = lambda: now() - started > 2
    
    while True:
        started = now()
        clf.connect(rdwr={'on-connect': connected},
                    terminate=term)
        sleep(2)

def connected(tag, id='ac5b72cf-5b0f-4ac1-9ed8-5434f102d4cb'):
    if (tag.ndef and tag.ndef.message[0].data[3:] == id):
        print 'Detect authorized nfc!'    
        

if __name__ == '__main__':
    def __tcb__():
        import os
        import sys
        import time
        
        sys.path.insert(1, os.path.join(os.path.split(sys.path[0])[0],
                                        'nfcpy-0.10.2'))
        import nfc

        def now():
            return time.time()
        
        def mknfc():
            clf = nfc.ContactlessFrontend('usb')
            return clf

        return dict(mknfc=mknfc, now=now, sleep=time.sleep)
    main(**__tcb__())
