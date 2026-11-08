"""Verify the approved merge and record observed headset input separately from replay."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

lab = Path('H:/MGFR/HandLab-20261018')
changes = json.loads((lab / 'main-overwrite-manifest.json').read_text(encoding='utf8'))
additions = json.loads((lab / 'main-additions-manifest.json').read_text(encoding='utf8'))
for item in changes:
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['after'], item['path']
for item in additions:
    assert hashlib.sha256(Path(item['target']).read_bytes()).hexdigest() == item['sha256'], item['target']
log_path = lab / 'headset-3788-30717.log'
log = log_path.read_text(encoding='utf8', errors='replace')
status = [line for line in log.splitlines() if '[MGFR hands]' in line]
receipt = {
    'recorded_utc': datetime.now(timezone.utc).isoformat(),
    'approved_merge_applied': True,
    'overwritten_configs': len(changes),
    'added_files': len(additions),
    'all_approved_hashes_match_tested_project': True,
    'player': str(lab / 'Project-v3/Build/Windows/MGFR.exe'),
    'headset_log': str(log_path),
    'runtime_joint_input_observed': any('source=XR_RUNTIME left=26/26 right=26/26' in s for s in status),
    'left_pinch_transition_observed': any('leftPinch=True' in s for s in status),
    'right_pinch_transition_observed': any('rightPinch=True' in s for s in status),
    'cloth_grab_observed': any(' cloth grab=' in s for s in status),
    'manual_bare_hand_alignment': 'awaiting user confirmation with controllers put down and F8 overlay',
    'headset_hand_depth_occlusion': 'awaiting user confirmation',
    'room_depth_map': 'not implemented',
    'replay_report': str(lab / 'Review-v3/hands-review.txt'),
}
with (lab / 'hand-delivery.json').open('x', encoding='utf8') as file:
    json.dump(receipt, file, ensure_ascii=False, indent=2)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
