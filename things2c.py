"""
Usage:
  things2c [options] nfc_scan
  things2c [options] motionctl
  things2c [options] watchdog
  things2c [options] blinkctl
  things2c [options] notify <notify_text>
  things2c [options] publish
  things2c [options] snoop
  things2c [options] filemanager
  things2c version

Sub-commands:
  nfc_scan          NFC scan/report
  motionctl         Control motion sensor
  watchdog          Watchdog for motion control
  blinkctl          Control status blink(1)
  notify            Send notifications
  publish           Publish topic/payload to MQ
  snoop             Output all MQTT traffic
  filemanager       Upload/delete video files
  version           Display version and exit

Options:
  -h --help         Print usage
  -c --config=FILE  Configuration file [default: /etc/things2c/things2c.ini]
  -v --verbose      Verbose/debug output
  -t --topic=TOPIC  Topic to publish
  -p --payload=PL   Payload for publish
  -e --encode       Encode payload
"""
import logging
from attrdict import AttrDict
from hashlib import sha1
from collections import defaultdict
from datetime import timedelta
from functools import partial
from Queue import Queue, Empty

logging.basicConfig(format='%(asctime)s: %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)

log = logging.getLogger(__name__)


def main(cli, cfg, mk_mqtt, mk_notify, mk_nfc, sleep, blink, now,
         is_motion_on, motion_on, motion_off, reboot, mk_fmq,
         upload, delete, mk_mplog):
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
            if cli.payload:
                if cli.encode:
                    payload = dt_salted_hash(cli.payload,
                                             now(as_datetime=True))
                else:
                    payload = cli.payload
            else:
                payload = ''
            mqtt.publish(cfg.get_topics()[cli.topic], payload)
    elif cli.snoop:
        snoop(cli, mk_mqtt)
    elif cli.filemanager:
        filemanger(cli, cfg, mk_mqtt, mk_fmq, upload, delete, mk_mplog, now)
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


def filemanger(cli, cfg, mk_mqtt, mk_fmq, upload, delete, mk_mplog, now):
    mplog = mk_mplog()
    if cli.verbose:
        mplog.setLevel(logging.DEBUG)

    fmq = mk_fmq(log=mplog, mk_mqtt=mk_mqtt)

    q = Queue()
    mqtt = mk_mqtt(log=log, topics=[cfg.get_topics().motion_filesync_all,
                                    cfg.get_topics().nfc_scan_all],
                   msg_queue=q)
    mqtt.loop_start()
    while True:
        try:
            msg = q.get(timeout=0.5)
            log.debug('filemanager() got %s, %s' % (msg.topic, msg.payload))
            if(msg.topic == cfg.get_topics().nfc_scan_data and
               authorized(msg.payload, cfg.config.motionctl.authorized_id,
                          now)):
                log.debug('filemanger() got authorized scan')
                fmq.cancel()
            elif msg.topic == cfg.get_topics().motion_filesync_queue:
                fmq.queue(upload=partial(upload, filename=msg.payload),
                          delete=partial(delete, filename=msg.payload),
                          timeout=int(cfg.config.filemanager.filesync_delay),
                          start_msg=(cfg.get_topics().motion_filesync_start,
                                     msg.payload),
                          end_msg=(cfg.get_topics().motion_filesync_end,
                                   msg.payload),
                          cancel_msg=(cfg.get_topics().motion_filesync_cancel,
                                      msg.payload))
        except Empty:
            pass
        #  Avoid zombies
        fmq._join_all(timeout=0)


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

    last_seen_topics = defaultdict(lambda: None)

    def seen_recently(topic):
        return (last_seen_topics[topic] and
                (now() - last_seen_topics[topic] <
                 float(cfg.config.blink.recent_status_sec)))

    def topic_to_color(topic):
        t2c = dict([(cfg.get_topics().motion_status_on,
                     cfg.config.blink.motion_on_color),
                    (cfg.get_topics().motion_status_off,
                     cfg.config.blink.motion_off_color),
                    (cfg.get_topics().motion_detected,
                     cfg.config.blink.motion_detected_color),
                    (cfg.get_topics().motion_filesync_start,
                     cfg.config.blink.motion_filesync_start_color),
                    (cfg.get_topics().motion_filesync_end,
                     cfg.config.blink.motion_filesync_end_color),
                    (cfg.get_topics().motion_filesync_cancel,
                     cfg.config.blink.motion_filesync_cancel_color)])
        if topic in t2c.keys():
            return t2c[topic]
        return None

    while True:
        # Get all the messages pending - keep track of when we found them
        while not q.empty():
            try:
                msg = q.get_nowait()
                last_seen_topics[msg.topic] = now()
            except Empty:
                pass

        # If motion is currently off, blink recent status
        if(seen_recently(cfg.get_topics().motion_status_off)):
            colors = list()
            for topic, last_seen in last_seen_topics.items():
                if(last_seen and (now() - last_seen) <
                   float(cfg.config.blink.show_status_sec)):
                    colors.append(topic_to_color(topic))
            if colors:
                blink(pattern=mkpattern(
                    colors=(sorted([c for c in colors if c])) +
                    ['0x00,0x00,0x00']))
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
    from docopt import docopt
    from sys import argv
    cli = AttrDict(dict([(i[0].replace('--', '').strip('<>'), i[1])
                         for i in docopt(__doc__, argv=argv[1:]).items()]))

    def _tcb_():
        import nfc
        from datetime import datetime
        from multiprocessing import log_to_stderr
        from os import system, path as ospath, remove
        from time import time, sleep
        from config import Config
        from file_manager import FileManagerQueue
        from httplib import HTTPSConnection
        from mqtt_client import MqttClient
        from nfc_interface import NfcInterface
        from owncloud import Client as ocClient
        from pushover_notify import PushoverNotify
        from urllib import urlencode

        with open(cli.config, 'rb') as cfgin:
            cfg = Config(cfgin)

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

        def upload(filename, path, s3_dest, oc_url, oc_user,
                   oc_password, oc_subdir):
            fullpath = ospath.join(path, ospath.split(filename)[1])
            if ospath.isfile(fullpath):
                if s3_dest:
                    cmd = ('s3cmd sync %(fullpath)s %(s3_dest)s'
                           % dict(fullpath=fullpath, s3_dest=s3_dest))
                    system(cmd)
                if oc_url:
                    oc = ocClient(oc_url)
                    oc.login(oc_user, oc_password)
                    fn = ospath.split(fullpath)[-1:][0]
                    oc.put_file(ospath.join(oc_subdir) if oc_subdir else fn,
                                fullpath)

        def delete(filename, path):
            fullpath = ospath.join(path, ospath.split(filename)[1])
            if ospath.isfile(fullpath):
                remove(fullpath)

        def mk_mplog():
            return log_to_stderr()

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
                    motion_off=motion_off, reboot=reboot,
                    mk_fmq=FileManagerQueue.make,
                    upload=partial(
                        upload,
                        path=cfg.config.filemanager.filestore_path,
                        s3_dest=cfg.config.filemanager.s3_dest,
                        oc_url=cfg.config.filemanager.oc_url,
                        oc_user=cfg.config.filemanager.oc_user,
                        oc_password=cfg.config.filemanager.oc_password,
                        oc_subdir=cfg.config.filemanager.oc_subdir),
                    delete=partial(delete,
                                   path=cfg.config.filemanager.filestore_path),
                    mk_mplog=mk_mplog)

    if cli.version:
        from version import VERSION_STRING
        print VERSION_STRING
    else:
        main(**_tcb_())
