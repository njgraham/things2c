"""
Usage:
  things2c [options] nfc_scan
  things2c [options] motionctl
  things2c [options] watchdog
  things2c [options] blinkctl
  things2c [options] notify <notify_text>
  things2c [options] publish
  things2c [options] snoop

Sub-commands:
  nfc_scan          NFC scan/report
  motionctl         Control motion sensor
  watchdog          Watchdog for motion control
  blinkctl          Control status blink(1)
  notify            Send notifications
  publish           Publish topic/payload to MQ
  snoop             Output all MQTT traffic

Options:
  -h --help         Print usage
  -c --config=FILE  Configuration file [default: things2c.ini]
  -v --verbose      Verbose/debug output
  -t --topic=TOPIC  Topic to publish
  -p --payload=PL   Payload for publish
"""
import logging
from hashlib import sha1
from collections import defaultdict
from datetime import timedelta
from functools import partial
from Queue import Queue, Empty

logging.basicConfig(format='%(asctime)s: %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)

log = logging.getLogger(__name__)


def main(cli, cfg, mk_mqtt, mk_notify, mk_nfc, sleep, blink, now,
         is_motion_on, motion_on, motion_off, reboot):
    if cli.verbose:
        log.setLevel(logging.DEBUG)

    if cli.nfc_scan:
        nfc_scan(cli, cfg, mk_mqtt, mk_nfc, sleep, mk_notify, reboot, now)
    elif cli.motionctl:
        motionctl(cli, cfg, mk_mqtt, sleep, now, is_motion_on,
                  motion_on, motion_off, mk_notify)
    elif cli.watchdog:
        watchdog(cli, cfg, mk_mqtt, mk_notify)
    elif cli.blinkctl:
        blinkctl(cli, cfg, mk_mqtt, blink, sleep, now)
    elif cli.notify:
        notify = mk_notify(log=log)
        notify.notify(cli.notify_text)
    elif cli.publish:
        valid_topics = [vn for vn in
                        cfg.get_topics().keys() if not vn.endswith('_all')]
        if not cli.topic or cli.topic not in valid_topics:
            log.error('Valid topics are:\n%s' % '\n'.join(valid_topics))
        else:
            mqtt = mk_mqtt(log=log)
            mqtt.publish(cfg.get_topics()[cli.topic],
                         cli.payload if cli.payload else '')
    elif cli.snoop:
        snoop(cli, mk_mqtt)
    else:
        raise NotImplementedError()


def snoop(cli, mk_mqtt):
    q = Queue()
    mqtt = mk_mqtt(log=log, topics=['/#'], msg_queue=q)
    mqtt.loop_start()
    while True:
        try:
            msg = q.get(block=True, timeout=1)
            if msg:
                log.info('%s%s' % (msg.topic, ', %s' %
                                   msg.payload if msg.payload else ''))
        except Empty:
            pass


def dt_salted_hash(data, dt):
    '''
    >>> import datetime as dt
    >>> dt_salted_hash('mysecretkey', dt.datetime(2016, 1, 1, 0, 0, 0))
    '35a86879588c32b6299f562ebb70d7926c6e4bc8'
    '''
    h = sha1(dt.strftime('%Y%m%d%H%M%S') + data).hexdigest()
    log.debug('data: %s, dt: %s, hash: %s' % (data, dt, h))
    return h


def authorized(candidate, secret, now, window_sec=30):
    '''
    >>> import datetime as dt
    >>> def now(as_datetime): return dt.datetime(2016, 1, 1, 0, 0, 0)
    >>> authorized(candidate='35a86879588c32b6299f562ebb70d7926c6e4bc8',
    ...            secret='mysecretkey', now=now)
    True
    >>> authorized(candidate='xxx', secret='mysecretkey', now=now)
    False
    '''
    start = now(as_datetime=True)
    one_sec = timedelta(seconds=1)
    # To minimize hash calculations, start at the current time and move
    # outward one second at a time (0, +1, -1, +2, -2...).
    for time in [t2 for sublist in (
            [[start]] + [(start + one_sec * t, start - one_sec * t)
                         for t in range(1, window_sec + 1)])
                 for t2 in sublist]:
        key_hash = dt_salted_hash(secret, time)
        log.debug('authorized() dt: %s, candidate: %s, key_hash: %s' %
                  (time, candidate, key_hash))
        if key_hash == candidate:
            return True
    return False


def motionctl(cli, cfg, mk_mqtt, sleep, now, is_motion_on,
              motion_on, motion_off, mk_notify):
    q = Queue()
    mqtt = mk_mqtt(log=log, topics=[cfg.get_topics().nfc_scan_all],
                   msg_queue=q)
    notify = mk_notify(log=log)
    mqtt.loop_start()

    last_update = now()
    last_auth = None
    while True:
        try:
            msg = q.get_nowait()
            last_update = now()
            log.debug('motionctl() got %s, %s' % (msg.topic, msg.payload))
            if(msg.topic == cfg.get_topics().nfc_scan_data and
               authorized(msg.payload, cfg.config.motionctl.authorized_id,
                          now)):
                mqtt.publish(cfg.get_topics().info, 'Authorized scan data')
                last_auth = now()
                if is_motion_on():
                    motion_off()
                    notify.notify('MOTION OFF')

        except Empty:
            log.debug('motionctl() queue is empty')

        if(((now() - last_update >
             float(cfg.config.motionctl.scan_timeout_sec)) or
            ((not last_auth) or now() - last_auth >
             float(cfg.config.motionctl.auth_timeout_sec))) and
           not is_motion_on()):
            log.debug('motionctl() Update/auth timeout exceeded '
                      'and motion not on - turning on.')
            motion_on()
            notify.notify('MOTION ON')

        mqtt.publish(cfg.get_topics().motion_status_on if is_motion_on()
                     else cfg.get_topics().motion_status_off)
        if q.empty():
            sleep(float(cfg.config.motionctl.proc_poll_sleep))


def rgbcnvt(rgb):
    '''
    >>> print rgbcnvt('0xff,0x00,0x00')
    #ff0000
    '''
    return '#' + rgb.replace('0x', '').replace(',', '')


def mkpattern(colors, msec=0.4):
    '''
    >>> print mkpattern(['0xff,0x00,0xff', '0x00,0xcc,0x00'])
    '1,#ff00ff,0.4,0,#00cc00,0.4,0'
    >>> print mkpattern(None)
    None
    '''
    return ("'%s'" % ','.join(['1'] +
                              [item for sublist in
                               [[rgbcnvt(c), str(msec), '0']
                                for c in colors] for item in sublist])
            if colors else None)


def blinkctl(cli, cfg, mk_mqtt, blink, sleep, now):
    q = Queue()
    mqtt = mk_mqtt(log=log, topics=[cfg.get_topics().motion_all],
                   msg_queue=q)
    mqtt.loop_start()

    cd = defaultdict(lambda: None)

    def seen_recently(color):
        return (cd[color] and
                (now() - cd[color] <
                 float(cfg.config.blink.recent_status_sec)))

    while True:
        while not q.empty():
            try:
                msg = q.get_nowait()
                if msg.topic == cfg.get_topics().motion_status_on:
                    cd[cfg.config.blink.motion_on_color] = now()
                elif msg.topic == cfg.get_topics().motion_status_off:
                    cd[cfg.config.blink.motion_off_color] = now()
                elif msg.topic == cfg.get_topics().motion_detected:
                    cd[cfg.config.blink.motion_detected_color] = now()
                elif msg.topic.startswith(cfg.get_topics().motion_filesync):
                    cd[cfg.config.blink.motion_filesync_color] = now()
            except Empty:
                pass

        if(seen_recently(cfg.config.blink.motion_off_color)):
            cl = list()
            for c, u in cd.items():
                if u and (now() - u) < float(cfg.config.blink.show_status_sec):
                    cl.append(c)

            if cl:
                blink(pattern=mkpattern(
                    colors=(sorted(cl)) + ['0x00,0x00,0x00']))
        sleep(float(cfg.config.blink.sec_between_blinks))


def nfc_scan(cli, cfg, mk_mqtt, mk_nfc, sleep, mk_notify, reboot,
             now, padlen=3):
    nfc = None
    mqtt = mk_mqtt(log=log)
    notify = mk_notify(log=log)

    fail_count = 0
    while True:
        log.debug('nfc_scan()')
        mqtt.publish(cfg.get_topics().nfc_scan)
        try:
            if not nfc:
                nfc = mk_nfc(log=log)
            data = nfc.read()
            fail_count = 0
            log.debug('nfc_scan() data: %s' % data)
            if data and len(data) > padlen:
                mqtt.publish(cfg.get_topics().nfc_scan_data,
                             dt_salted_hash(data[padlen:],
                             now(as_datetime=True)))
        except Exception, e:
            fail_count += 1
            msg = 'nfc_scan() failed! Count is %d' % fail_count
            log.error(msg)
            log.error(str(e))
            mqtt.publish(cfg.get_topics().info, msg)
            #  TODO: Make fail_count configurable
            if fail_count >= 30:
                msg = 'nfc_scan() scanner is stuck - rebooting!'
                log.error(msg)
                mqtt.publish(cfg.get_topics().info, msg)
                notify.notify(msg)
                reboot()
        log.debug('nfc_scan() sleeping for %s' %
                  cfg.config.nfc.scan_poll_sleep)
        sleep(float(cfg.config.nfc.scan_poll_sleep))


def watchdog(cli, cfg, mk_mqtt, mk_notify):
    q = Queue()
    client = mk_mqtt(log=log, topics=[cfg.get_topics().motion_status_all],
                     msg_queue=q)
    notify = mk_notify(log=log)
    client.loop_start()

    notifications = int(cfg.config.watchdog.notification_count)
    while True:
        try:
            msg = q.get(block=True,
                        timeout=float(cfg.config.watchdog.timeout_sec))
            log.debug('%s %s' % (msg.topic, msg.payload))
            notifications = int(cfg.config.watchdog.notification_count)
        except Empty:
            log.info('Watchdog!')
            if notifications:
                notify.notify('MOTION WATCHDOG')
            notifications = max(notifications - 1, 0)

if __name__ == '__main__':
    def _tcb_():
        from attrdict import AttrDict
        from datetime import datetime
        from docopt import docopt
        from os import path as ospath, system
        from sys import argv, path
        from time import time, sleep

        from config import Config
        from httplib import HTTPSConnection
        from mqtt_client import MqttClient
        from nfc_interface import NfcInterface
        from pushover_notify import PushoverNotify
        from urllib import urlencode

        cli = AttrDict(dict([(i[0].replace('--', '').strip('<>'), i[1])
                             for i in docopt(__doc__, argv=argv[1:]).items()]))
        with open(cli.config, 'rb') as cfgin:
            cfg = Config(cfgin)

        path.insert(1, ospath.join(ospath.split(path[0])[0],
                                   cfg.config.nfc.nfcpy_path))
        try:
            import nfc
        except:
            log.warning('Can\'t import nfc!')
            nfc = None

        def now(as_datetime=False):
            if as_datetime:
                return datetime.now()
            return time()

        def blink(pattern):
            system('blink1-tool --playpattern %(pattern)s > /dev/null'
                   % dict(pattern=pattern))

        def is_motion_on():
            if system('pgrep -a motion > /dev/null') == 0:
                return True
            return False

        def motion_on():
            system('sudo supervisorctl start motion')

        def motion_off():
            system('sudo supervisorctl stop motion')

        def reboot():
            system('sudo /sbin/reboot')

        return dict(cli=cli, cfg=cfg,
                    mk_mqtt=partial(MqttClient.make, cfg.config.broker.host,
                                    cfg.config.broker.port),
                    mk_notify=partial(PushoverNotify.make,
                                      urlencode=urlencode,
                                      connection=HTTPSConnection,
                                      token=cfg.config.pushover.token,
                                      user=cfg.config.pushover.user),
                    mk_nfc=partial(NfcInterface.make, nfc=nfc, now=now),
                    sleep=sleep, blink=blink, now=now,
                    is_motion_on=is_motion_on, motion_on=motion_on,
                    motion_off=motion_off, reboot=reboot)
    main(**_tcb_())
