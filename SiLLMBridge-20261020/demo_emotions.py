"""No model/key required: exercise emotion and gesture together over real HTTP."""
import argparse
import json
from urllib.request import Request, build_opener, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emotion', choices=['neutral', 'happy', 'sad', 'angry', 'surprised', 'shy', 'thinking', 'affection'], default='sad')
    parser.add_argument('--action', default='think')
    args = parser.parse_args()
    data = {'version': 1, 'text': '我会陪你慢慢说。' if args.emotion == 'sad' else '这次的情绪和动作会一起播放。',
            'emotion': args.emotion, 'emotion_intensity': .6, 'speech_duration': 10,
            'actions': [{'name': args.action, 'at': 0}]}
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(Request('http://127.0.0.1:18766/v1/perform', json.dumps(data).encode(), {'Content-Type': 'application/json'}), timeout=3) as response:
            print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
    except OSError:
        print('请先启动本地桥接服务和角色程序。')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
