"""
Usage:
  things2c [options] nfc_scan
  things2c [options] motionctl
  things2c [options] watchdog
  things2c [options] blinkctl
  things2c [options] notify <notify_text>
  things2c [options] publish

Sub-commands:
  nfc_scan          NFC scan/report
  motionctl         Control motion sensor
  watchdog          Watchdog for motion control
  blinkctl          Control status blink(1)
  notify            Send notifications
  publish           Publish topic/payload to MQ

Options:
  -h --help         Print usage
  -c --config=FILE  Configuration file [default: things2c.ini]
  -v --verbose      Verbose/debug output
  -t --topic=TOPIC  Topic to publish
  -p --payload=PL   Payload for publish
"""
import logging
from functools import partial
from Queue import Queue, Empty

logging.basicConfig(format='%(asctime)s: %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)

log = logging.getLogger(__name__)


def main(cli, cfg, mk_mqtt, mk_notify, mk_nfc, sleep, blink, now,
         is_motion_on, motion_on, motion_off):
    if cli.verbose:
        log.setLevel(logging.DEBUG)

    if cli.nfc_scan:
        nfc_scan(cli, cfg, mk_mqtt, mk_nfc, sleep)
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
    else:
        raise NotImplementedError()


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
               msg.payload[3:] == cfg.config.motionctl.authorized_id):
                mqtt.publish(cfg.get_topics().info, 'Authorized scan data')
                last_auth = now()
                if is_motion_on():
                    motion_off()
                    notify.notify('MOTION OFF')

        except Empty:
            log.debug('motionctl() queue is empty')

        if(((now() - last_update >
             float(cfg.config.motionctl.scan_timeout_sec))
            or
            ((not last_auth) or now() - last_auth >
             float(cfg.config.motionctl.auth_timeout_sec)))
           and not is_motion_on()):
            log.debug('motionctl() Update/auth timeout exceeded '
                      'and motion not on - turning on.')
            motion_on()
            notify.notify('MOTION ON')

        mqtt.publish(cfg.get_topics().motion_status_on if is_motion_on()
                     else cfg.get_topics().motion_status_off)
        if q.empty():
            sleep(float(cfg.config.motionctl.proc_poll_sleep))


def blinkctl(cli, cfg, mk_mqtt, blink, sleep, now):
    q = Queue()
    mqtt = mk_mqtt(log=log, topics=[cfg.get_topics().motion_all],
                   msg_queue=q)
    mqtt.loop_start()

    color = cfg.config.blink.motion_unknown_color
    last_update = None

    on_count = int(cfg.config.blink.motion_on_blink_count)
    while True:
        while not q.empty():
            try:
                msg = q.get_nowait()
                last_update = now()
                if msg.topic == cfg.get_topics().motion_status_on:
                    color = cfg.config.blink.motion_on_color
                elif msg.topic == cfg.get_topics().motion_status_off:
                    color = cfg.config.blink.motion_off_color
                elif msg.topic == cfg.get_topics().motion_detected:
                    color = cfg.config.blink.motion_detected_color
                elif msg.topic == cfg.get_topics().motion_filesync:
                    color = cfg.config.blink.motion_filesync_color
            except Empty:
                pass
        if(not last_update or (now() - last_update)
           > float(cfg.config.blink.motion_unknown_timeout_sec)):
            color = cfg.config.blink.motion_unknown_color

        if color == cfg.config.blink.motion_on_color:
            if on_count > 0:
                blink(color)
            on_count = max(on_count - 1, 0)
        else:
            on_count = int(cfg.config.blink.motion_on_blink_count)
            blink(color)
        sleep(float(cfg.config.blink.sec_between_blinks))


def nfc_scan(cli, cfg, mk_mqtt, mk_nfc, sleep):
    nfc = mk_nfc(log=log)
    mqtt = mk_mqtt(log=log)
    while True:
        log.debug('nfc_scan()')
        mqtt.publish(cfg.get_topics().nfc_scan)
        data = nfc.read()
        log.debug('nfc_scan() data: %s' % data)
        if data:
            mqtt.publish(cfg.get_topics().nfc_scan_data,
                         data)
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

        def now():
            return time()

        def blink(color):
            system('blink1-tool --rgb %(color)s --blink 1 > /dev/null'
                   % dict(color=color))

        def is_motion_on():
            if system('pgrep -a motion > /dev/null') == 0:
                return True
            return False

        def motion_on():
            system('sudo supervisorctl start motion')

        def motion_off():
            system('sudo supervisorctl stop motion')

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
                    motion_off=motion_off)
    main(**_tcb_())
