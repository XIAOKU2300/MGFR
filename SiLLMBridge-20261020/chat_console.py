"""Interactive LLM console, with conversation retained only in memory."""
from pathlib import Path
import json
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'client'))
from llm_chat import perform_turn, ClientError


def main():
    print('祀 / 输入消息，/exit 退出；先配置 SI_LLM_BASE_URL 和 SI_LLM_MODEL。')
    history = []
    while True:
        try:
            text = input('你> ').strip()
        except (KeyboardInterrupt, EOFError):
            return 0
        if text == '/exit':
            return 0
        if not text:
            continue
        try:
            plan, response = perform_turn(text,
                service_url=os.environ.get('SI_LLM_SERVICE_URL', 'http://127.0.0.1:18766'),
                model_url=os.environ.get('SI_LLM_BASE_URL'), model=os.environ.get('SI_LLM_MODEL'),
                api_key=os.environ.get('SI_LLM_API_KEY'), history=history[-20:])
            effective = response['effective_plan']
            print('祀>', effective['text'])
            print('情绪:', effective['emotion'], '| 表情:', effective['expression_variant'],
                  '| 动作:', ', '.join(a['name'] for a in effective['actions']) or '保持待机')
            history.extend([{'role': 'user', 'content': text}, {'role': 'assistant', 'content': json.dumps(plan, ensure_ascii=False)}])
            history = history[-20:]
        except ClientError as exc:
            print('未播放:', exc)


if __name__ == '__main__':
    raise SystemExit(main())
