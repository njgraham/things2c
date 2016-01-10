from functools import partial


def main(mk_pn, msg):
    import logging
    logging.basicConfig(format='%(asctime)s: %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', level=logging.DEBUG)
    log = logging.getLogger(__name__)
    pn = mk_pn(log=log)
    pn.notify(msg)


class PushoverNotify(object):
    def __init__(self, log, urlencode, connection, user, token):
        self._log = log
        self._urlencode = urlencode
        self._connection = connection
        self._user = user
        self._token = token

    @classmethod
    def make(cls, log, urlencode, connection, user, token):
        return PushoverNotify(log, urlencode, connection, user, token)

    def notify(self, msg):
        self._log.info('Pushover: %s' % msg)
        c = self._connection('api.pushover.net:443')
        c.request('POST', '/1/messages.json',
                  self._urlencode({
                      'token': self._token,
                      'user': self._user,
                      'message': msg}),
                  {'Content-type': 'application/x-www-form-urlencoded'})
        return c.getresponse()

if __name__ == '__main__':
    def _tcb_():
        from sys import argv
        from httplib import HTTPSConnection
        from urllib import urlencode

        return dict(mk_pn=partial(PushoverNotify.make,
                                  urlencode=urlencode,
                                  connection=HTTPSConnection,
                                  token=argv[1],
                                  user=argv[2]),
                    msg=argv[3])
    main(**_tcb_())

    