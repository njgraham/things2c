from os import path as ospath
from sys import argv, path
from time import time
from uuid import uuid4 as rnd_uuid

from config import Config

import logging
logging.basicConfig(format='%(asctime)s: %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S', level=logging.DEBUG)
log = logging.getLogger(__name__)

if __name__ == '__main__':
    config = argv[1]
    with open(config, 'rb') as cfgin:
        cfg = Config(cfgin)

    path.insert(1, ospath.join(ospath.split(path[0])[0],
                               cfg.config.nfc.nfcpy_path))
    import nfc
    from nfc_interface import NfcInterface
    ni = NfcInterface.make(nfc=nfc, now=time, log=log)
    ni.read()
    ni.write(str(rnd_uuid()))
    ni.read()
