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

logging.basicConfig(format='%(asctime)s: %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)

log = logging.getLogger(__name__)


def main(cli):
    if cli.verbose:
        log.setLevel(logging.DEBUG)

if __name__ == '__main__':
    def _tcb_():
        from attrdict import AttrDict
        from docopt import docopt
        from sys import argv

        cli = AttrDict(dict([(i[0].replace('--', ''), i[1])
                             for i in docopt(__doc__, argv=argv[1:]).items()]))
        return dict(cli=cli)
    main(**_tcb_())
    