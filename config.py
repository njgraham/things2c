from attrdict import AttrDict
from ConfigParser import SafeConfigParser

_topics = {'motion':
           {'status': {'on': None,
                       'off': None},
            'event': {'start': None,
                      'end': None},
            'filesync': {'start': None,
                         'end': None},
            'detected': None},
           'nfc': {'scan':
                   {'data': None}},
           'info': None}


class Config(object):
    def __init__(self, ini_file):
        self._ini_file = ini_file
        self.config = self._get_config(self._ini_file)

    def get_topics(self, topics=_topics):
        '''
        >>> c = Config(None)
        >>> t = c.get_topics(topics={'motion':
        ...                          {'status':
        ...                            {'on': None,
        ...                             'off': None}}})
        >>> print t.motion
        /motion/
        >>> print t.motion_status_on
        /motion/status/on/
        >>> print t.motion_status_all
        /motion/status/#
        '''
        def all_paths(topics):
            paths = []

            def ht(dct, paths, parent=''):
                if not dct:
                    return False
                for c in dct.keys():
                    np = '/'.join([parent, c])
                    if ht(dct[c], paths, np):
                        paths.append('/'.join([np, '#']))
                    np += '/'
                    paths.append(np)
                return True
            ht(topics, paths)
            return paths
        paths = all_paths(topics)
        return AttrDict(dict(zip(
            [p.strip('/').replace('/', '_').replace('#', 'all')
             for p in paths], paths)))

    def _get_config(self, rd):
        ''' Parse configuration from input stream
        >>> from pkg_resources import resource_stream
        >>> c = Config(resource_stream(__name__, 'things2c.ini.example'))
        >>> 'broker' in c.config.keys()
        True
        >>> c.config.broker.host == 'localhost'
        True
        '''
        if not rd:
            return None
        cp = SafeConfigParser()
        cp.readfp(rd)
        return AttrDict(cp._sections)
