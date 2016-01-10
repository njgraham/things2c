from attrdict import AttrDict
from ConfigParser import SafeConfigParser

TOPICS = {'motion':
          {'status': {'on': None,
                      'off': None}},
          'nfc': {'scan':
                  {'authorized': None,
                   'data': None}}}


def get_topics(topics=TOPICS):
    '''
    >>> t = get_topics(topics={'motion':
    ...                        {'status':
    ...                          {'on': None,
    ...                           'off': None}}})
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


def get_config(rd):
    ''' Parse configuration from input stream
    >>> from pkg_resources import resource_stream
    >>> opts = get_config(resource_stream(__name__, 'things2.ini.example'))
    >>> 'broker' in opts.keys()
    True
    >>> opts.broker.host == 'localhost'
    True
    '''
    cp = SafeConfigParser()
    cp.readfp(rd)
    return(AttrDict(cp._sections))
