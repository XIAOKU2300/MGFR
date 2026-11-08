"""Main-project bridge: JSON plans are aligned to actual voice playback by Unity."""
from pathlib import Path
from http.server import ThreadingHTTPServer
import argparse
import json
from bridge_server import Bridge, Handler, InvalidPlan

ROOT = Path(__file__).resolve().parent


class MainHandler(Handler):
    def do_GET(self):
        if self.path == '/v1/player/plan':
            if not self.allowed():
                return self.reply(403, {'error': 'Local clients only'})
            bridge = self.server.bridge
            with bridge.lock:
                current = bridge.current
                result = {'sequence': bridge.sequence, 'turn_id': '', 'voice_round': -1, 'actions': [], 'emotion': 'neutral'}
                if current:
                    result = {**current['plan'], 'sequence': bridge.sequence, 'turn_id': current['turn_id'],
                              'voice_round': current.get('voice_round', -1)}
            return self.reply(200, result)
        return super().do_GET()

    def do_POST(self):
        if self.path == '/v1/voice/perform':
            if not self.allowed():
                return self.reply(403, {'error': 'Local clients only'})
            try:
                if self.headers.get_content_type() != 'application/json':
                    raise InvalidPlan('JSON required')
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 65536:
                    raise InvalidPlan('Body too large')
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict) or set(value) != {'round', 'plan'} or type(value['round']) is not int or value['round'] < 1:
                    raise InvalidPlan('Invalid voice envelope')
                bridge = self.server.bridge
                with bridge.lock:
                    result = bridge.perform(value['plan'])
                    if bridge.current['turn_id'] == result['turn_id']:
                        bridge.current['voice_round'] = value['round']
                return self.reply(200, result)
            except (ValueError, TypeError, UnicodeError):
                return self.reply(400, {'error': 'Invalid structured voice plan'})
        return super().do_POST()


def make_server(catalog, port=18766):
    server = ThreadingHTTPServer(('127.0.0.1', port), MainHandler)
    server.daemon_threads = True
    server.bridge = Bridge(catalog)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18766)
    args = parser.parse_args()
    catalog = json.loads((ROOT / 'MainData/catalog.json').read_text(encoding='utf-8'))
    server = make_server(catalog, args.port)
    print('Main avatar bridge ready on 127.0.0.1:' + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
