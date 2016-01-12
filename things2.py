"""
Usage:
  things2 [options] nfc_scan
  things2 [options] motionctl
  things2 [options] watchdog
  things2 [options] blinkctl

Sub-commands:
  nfc_scan          NFC scan/report
  motionctl         Control motion sensor
  watchdog          Watchdog for motion control
  blinkctl          Control status blink(1)

Options:
  -h --help         Print usage
  -c --config=FILE  Configuration file [default: things2.ini]
  -v --verbose      Verbose/debug output
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
        nfc_scan(cli, cfg, mk_mqtt, mk_nfc, sleep, now)
    elif cli.motionctl:
        motionctl(cli, cfg, mk_mqtt, sleep, now, is_motion_on,
                  motion_on, motion_off)
    elif cli.watchdog:
        watchdog(cli, cfg, mk_mqtt, mk_notify)
    elif cli.blinkctl:
        blinkctl(cli, cfg, mk_mqtt, blink, sleep, now)
    else:
        raise NotImplementedError()


def motionctl(cli, cfg, mk_mqtt, sleep, now, is_motion_on,
              motion_on, motion_off):
    q = Queue()
    mqtt = mk_mqtt(log=log, topics=[cfg.get_topics().nfc_scan_all],
                   msg_queue=q)
    mqtt.loop_start()

    while True:
        try:
            msg = q.get(block=True,
                        timeout=float(cfg.config.watchdog.scan_timeout_sec))
            if(msg.topic == cfg.get_topics().nfc_scan_data and
               msg.data[3:] == cfg.config.motionctl.authorized_id):
                mqtt.publish(cfg.get_topics().info, 'Authorized scan data')
                if is_motion_on():
                    motion_off()
        except Empty:
            if not is_motion_on():
                motion_on()
        mqtt.publish(cfg.get_topics().motion_status_on if is_motion_on()
                     else cfg.get_topics().motion_status_off)
        sleep(float(cfg.config.motionctl.proc_poll_sleep))


def blinkctl(cli, cfg, mk_mqtt, blink, sleep, now):
    q = Queue()
    mqtt = mk_mqtt(log=log, topics=[cfg.get_topics().motion_status_all],
                   msg_queue=q)
    mqtt.loop_start()

    color = cfg.config.blink.motion_unknown_color
    last_update = None
    while True:
        while not q.empty():
            try:
                msg = q.get_nowait()
                last_update = now()
                if msg.topic == cfg.get_topics().motion_status_on:
                    color = cfg.config.blink.motion_on_color
                elif msg.topic == cfg.get_topics().motion_status_off:
                    color = cfg.config.blink.motion_off_color
            except Empty:
                pass
        if(not last_update or (now() - last_update)
           > float(config.blink.motion_unknown_timeout_sec)):
            color = cfg.config.blink.motion_unknown_color
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
    while True:
        try:
            msg = q.get(block=True,
                        timeout=float(cfg.config.watchdog.timeout_sec))
            log.debug('%s %s' % (msg.topic, msg.payload))
        except Empty:
            notify.notify('MOTION WATCHDOG')

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

        path.insert(1, ospath.join(ospath.split(path[0])[0],
                                   'nfcpy-0.10.2'))
        import nfc

        cli = AttrDict(dict([(i[0].replace('--', ''), i[1])
                             for i in docopt(__doc__, argv=argv[1:]).items()]))
        with open(cli.config, 'rb') as cfgin:
            cfg = Config(cfgin)

        def now():
            return time()

        def blink(color):
            system('blink1-tool --rgb %(color)s --blink 1 > /dev/null'
                   % dict(color=color))

        def is_motion_on():
            if system('pgrep -a motion') == 0:
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
                    sleep=sleep, blink=blink, now=now, is_motion_on,
                    motion_on, motion_off)
    main(**_tcb_())
