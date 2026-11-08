# Focused actor clip selection

Mechanical name filter only. Candidate inclusion does not establish that additive or virtual clips can be played independently.

- Actor candidates: 94.
- Lists: {'main': 30, 'controller-linked': 64}.
- Candidate clips with any listed ACL buffer: 94.
- Main-list `npc` rows examined for float curves: 663.
- Those with nonempty decoded `m_FloatCurves`: 0.
- Distinct literal `attribute` values in `m_FloatCurves`: 0.
- typeID 4 facial-path examples exposed as strings in generic binding records: 0. Integer/hash path values are not interpreted as names.

## Candidate counts by category keyword

- `idle` (待机): 38
- `relax` (放松/待机): 5
- `walk` (行走): 43
- `wave` (挥手/动作): 1
- `nod` (点头/动作): 1
- `shake` (摇头/动作): 1
- `scratchhead` (挠头/动作): 3
- `receive_gift` (收礼/动作): 1
- `camera` (镜头/动作): 1
- `tsundere` (傲娇表情/动作): 1
- `play` (玩耍/动作): 2

## Candidate list

| name | category keyword(s) | source list / bundle | duration (s) | additive marker | virtual marker | ACL buffer keys | binding count |
|---|---|---|---:|---|---|---|---:|
| `A_actor_jsspsi_dialog_virtual_single_idle_talkhands` | idle=待机 | main / `main/26ea04835de97c30580e27b4.ab` | 4.583333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_virtual_state_scratchhead_end` | scratchhead=挠头/动作 | main / `main/ce34dfbc57de5512f960692b.ab` | 2.266667 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1069 |
| `A_actor_jsspsi_dialog_virtual_state_scratchhead_start` | scratchhead=挠头/动作 | main / `main/ce34dfbc57de5512f960692b.ab` | 2.066667 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1068 |
| `A_actor_jsspsi_dialog_virtual_state_scratchhead_loop` | scratchhead=挠头/动作 | main / `main/ce34dfbc57de5512f960692b.ab` | 1.333333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1069 |
| `A_actor_jsspsi_dialog_single_idle_turn_r_90` | idle=待机 | main / `main/c85e52506e4ac8a41ea94e8b.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1084 |
| `A_actor_jsspsi_dialog_single_wave` | wave=挥手/动作 | main / `main/b3f8b44898341233b3185557.ab` | 4.166667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1077 |
| `A_actor_jsspsi_dialog_single_walk_stop_l` | walk=行走 | main / `main/8fb7183d6d4a904afad29533.ab` | 2.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1096 |
| `A_actor_jsspsi_dialog_state_walkandtalk_loop` | walk=行走 | main / `main/6a933226703ab22779d224c2.ab` | 5.666668 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_state_walkandtalk_end` | walk=行走 | main / `main/6a933226703ab22779d224c2.ab` | 16.66667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_state_walkandtalk_start` | walk=行走 | main / `main/6a933226703ab22779d224c2.ab` | 9.500001 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_single_walk_stop_r` | walk=行走 | main / `main/33de657eb10b14ab89a7a41f.ab` | 2.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1107 |
| `A_actor_jsspsi_interact_receive_gift` | receive_gift=收礼/动作 | main / `main/21e7bde1eafcc3e40b4b82f1.ab` | 7.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1084 |
| `A_actor_jsspsi_dialog_virtual_single_idle_talkrighthand1` | idle=待机 | main / `main/7fc97359eac6b519a42798d3.ab` | 2.833333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_interact_camera_01` | camera=镜头/动作 | main / `main/a6765406df864069c700013f.ab` | 5.833333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1125 |
| `A_actor_jsspsi_dialog_single_idle_turn_l_90` | idle=待机 | main / `main/27e79a83508de45961be8317.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1069 |
| `A_actor_jsspsi_dialog_virtual_single_idle_talklefthand2` | idle=待机 | main / `main/78d10aa3264d11532e520e58.ab` | 5.733334 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_single_walk_start_l_0_r` | walk=行走 | main / `main/3fdacb73ef4149140552e0c2.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1094 |
| `A_actor_jsspsi_dialog_virtual_single_walk_s` | walk=行走 | main / `main/c37d09b5e2ac7cff4f7b718f.ab` | 3.333333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1065 |
| `A_actor_jsspsi_dialog_virtual_single_idle_talklefthand1` | idle=待机 | main / `main/8c64befc37b5ab76d78aef2d.ab` | 2.833333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_single_idle_turn_l_180` | idle=待机 | main / `main/1613496c8913dea61fe333bc.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1075 |
| `A_actor_jsspsi_dialog_virtual_single_idle_nod` | idle=待机; nod=点头/动作 | main / `main/4d9e2231639e861a65e9c0fb.ab` | 1.333333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_single_idle_turn_r_180` | idle=待机 | main / `main/2bc31952d8ea0d9a4abcf90e.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1064 |
| `A_actor_jsspsi_dialog_state_play02_loop` | play=玩耍/动作 | main / `main/84ca6ca792b740a84d710fe1.ab` | 2.516667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1090 |
| `A_actor_jsspsi_dialog_virtual_single_idle_talkrighthand2` | idle=待机 | main / `main/2121356419e0625c0be01575.ab` | 5.733334 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_virtual_single_walk_l` | walk=行走 | main / `main/f4b46b406d84b6a841cbabe6.ab` | 4.4 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_virtual_single_idle_shake` | idle=待机; shake=摇头/动作 | main / `main/6fe76d3f22288d2900f7c957.ab` | 2.333333 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_virtual_single_walk_m` | walk=行走 | main / `main/a6a940b7d4afcfc5415bd31a.ab` | 3.616667 | not marked in name/top-level fields | name | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_state_idle_loop` | idle=待机 | main / `main/0e89fba4fe1a28327bc43337.ab` | 2.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1063 |
| `A_actor_jsspsi_dialog_single_play` | play=玩耍/动作 | main / `main/9e73c1238e379fbb88a1edc2.ab` | 16.583334 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1069 |
| `A_actor_jsspsi_dialog_single_tsundere` | tsundere=傲娇表情/动作 | main / `main/08726eb75d445bfdf04e4021.ab` | 3.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1069 |
| `A_actor_girl_idle_jump_land_block_r` | idle=待机 | controller-linked / `main/ff09682c22c777e6fc5e78b1.ab` | 4.05 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 385 |
| `A_actor_girl_idle_turn_l_90` | idle=待机 | controller-linked / `main/fec58358a0096b435cbbb29d.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_idle_jump_land_block_l` | idle=待机 | controller-linked / `main/f55c97e44c831b433908aca1.ab` | 4.05 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 386 |
| `A_actor_jsspsi_relax_loop` | relax=放松/待机 | controller-linked / `main/f12074e7b4b887c381e24553.ab` | 3.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1068 |
| `A_actor_girl_idle_bump_heavy_l` | idle=待机 | controller-linked / `main/e1ae6a431c5e07b768d7cc1c.ab` | 2.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_jsspsi_relax_react` | relax=放松/待机 | controller-linked / `main/e0cc3c34077cc06e5243e938.ab` | 11.266667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1089 |
| `A_actor_girl_idle_avoid_f` | idle=待机 | controller-linked / `main/da27531730767eb2ebc7b4a1.ab` | 2.583333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 356 |
| `A_actor_girl_walk_stepon_d_r` | walk=行走 | controller-linked / `main/c04e14aba77e4f05b88fb0c5.ab` | 1.603752 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_start_l_180_r` | walk=行走 | controller-linked / `main/bebb427e343ac20864204d12.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 383 |
| `A_actor_girl_walk_loop` | walk=行走 | controller-linked / `main/be6efc5a06bcf92e3ca9e5a1.ab` | 1.070981 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 353 |
| `A_actor_girl_run_to_walk_r` | walk=行走 | controller-linked / `main/bd4e0a4401ae36bb7d42cc1a.ab` | 1.533333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_loop_r` | walk=行走 | controller-linked / `main/b8d0d56c141287149af379bc.ab` | 1.070981 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 383 |
| `A_actor_girl_walk_quickstop_r` | walk=行走 | controller-linked / `main/b7f6762fe800687cce97a372.ab` | 2.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_stop_r` | walk=行走 | controller-linked / `main/b7f6762fe800687cce97a372.ab` | 2.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_start_r_90_l` | walk=行走 | controller-linked / `main/b2992ec858d764fbc733d85c.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 383 |
| `A_actor_girl_walk_jump_land_l` | walk=行走 | controller-linked / `main/b083e19b4a0ff3df77a9fdc5.ab` | 1.366667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 357 |
| `A_actor_girl_idle_turn_r_180` | idle=待机 | controller-linked / `main/ad5bf0821b05aa621b44b558.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_idle_turn_r_0` | idle=待机 | controller-linked / `main/ab34d9a02a7c26630df1b716.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_idle_jump_start_r` | idle=待机 | controller-linked / `main/a5e933dbf5215d336622e8fa.ab` | 1.401709 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 361 |
| `A_actor_girl_walk_loop_u` | walk=行走 | controller-linked / `main/a3ef0fc63355107f7f923e0b.ab` | 1.070981 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 357 |
| `A_actor_girl_walk_start_l_90_r` | walk=行走 | controller-linked / `main/9f68f16e8e29ba5f75212e42.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 383 |
| `A_actor_girl_walk_pivot_r` | walk=行走 | controller-linked / `main/9bed1d31291d42f611aa692e.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_stop_strafe_l` | walk=行走 | controller-linked / `main/93b8064d1585d89cdf22aad1.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 345 |
| `A_actor_girl_idle_avoid_b` | idle=待机 | controller-linked / `main/8f1a91687298520fee018287.ab` | 2.583333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_jsspsi_walk_loop_additive` | walk=行走 | controller-linked / `main/8e7c633d27d70b2b4c099e4b.ab` | 1.066667 | name | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1060 |
| `A_actor_girl_idle_bump_heavy_r` | idle=待机 | controller-linked / `main/861db51a588b39736ea2a240.ab` | 2.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_start_l_0_r` | walk=行走 | controller-linked / `main/85f9654e5314674758c85be0.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 382 |
| `A_actor_girl_walk_loop_wading` | walk=行走 | controller-linked / `main/7f531b8bb7ea1bae3b1845e8.ab` | 1.066667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 446 |
| `A_actor_jsspsi_idle_to_relax` | idle=待机; relax=放松/待机 | controller-linked / `main/78752c60f1a4ab8ed6fad3b6.ab` | 2.866667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1102 |
| `A_actor_girl_idle_turn_r_90` | idle=待机 | controller-linked / `main/784c1e05bda773bd89ce0c4f.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_walk_pivot_l` | walk=行走 | controller-linked / `main/769280bb8e974100c2faeac1.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_jump_land_heavy_l` | walk=行走 | controller-linked / `main/6f32b6703e215b4d0df35de7.ab` | 1.366667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 357 |
| `A_actor_jsspsi_idle_loop_additive` | idle=待机 | controller-linked / `main/6c4f78e44bbf64123fd46481.ab` | 2.0 | name | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1060 |
| `A_actor_girl_walk_start_r_0_l` | walk=行走 | controller-linked / `main/639c42945bc8333f2e9b8a8b.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 382 |
| `A_actor_girl_idle_bump_heavy_b` | idle=待机 | controller-linked / `main/6211a83200bb16fe9e002f8e.ab` | 2.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_idle_turn_l_180` | idle=待机 | controller-linked / `main/5d7c6db6fd3fe305eb6ba384.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_idle_turn_l_180 (1)` | idle=待机 | controller-linked / `main/5d7c6db6fd3fe305eb6ba384.ab` | 1.333333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 349 |
| `A_actor_girl_walk_bump_l` | walk=行走 | controller-linked / `main/5af1a932f922f2edfb8fa191.ab` | 1.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_idle_jump_land_r` | idle=待机 | controller-linked / `main/57f85957f9eda115c744b543.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_idle_turn_l_0` | idle=待机 | controller-linked / `main/54f6adab1b6b4678e3a24274.ab` | 2.5 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_walk_stepon_u_l` | walk=行走 | controller-linked / `main/52c10d74653b24f4088f78c8.ab` | 1.603752 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_loop_d` | walk=行走 | controller-linked / `main/4d3c1dba4a626fd6e6e4e5c5.ab` | 1.070981 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_idle_avoid_l` | idle=待机 | controller-linked / `main/4c7edc3fd60f10f37adae00e.ab` | 2.583333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_stepon_u_r` | walk=行走 | controller-linked / `main/4a5c7f4236399011dceb795c.ab` | 1.603752 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_jump_land_heavy_r` | walk=行走 | controller-linked / `main/47e008187e4684ca1e36847b.ab` | 1.366667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 357 |
| `A_actor_girl_idle_jump_land_l` | idle=待机 | controller-linked / `main/43db1205bd901dc3fb3cba02.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_jump_land_r` | walk=行走 | controller-linked / `main/3ec4f6e1b39fdfee27af4c4b.ab` | 1.366667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 357 |
| `A_actor_girl_run_to_walk_l` | walk=行走 | controller-linked / `main/3e123606766e059c535df36b.ab` | 1.533333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_idle_jump_land_heavy_r` | idle=待机 | controller-linked / `main/3c8512e8f2f39506eb44e3e4.ab` | 2.333333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_stepon_d_l` | walk=行走 | controller-linked / `main/397d6923c9ebaa1b11c013dd.ab` | 1.603752 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_idle_jump_land_heavy_l` | idle=待机 | controller-linked / `main/370d7521acc58d9ce9f9487f.ab` | 2.333333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_loop_l` | walk=行走 | controller-linked / `main/342fc22dad5de85fdd73c37b.ab` | 1.070981 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 383 |
| `A_actor_girl_idle_avoid_r` | idle=待机 | controller-linked / `main/25e54fc74dcfd5e8b4a47ece.ab` | 2.583333 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 354 |
| `A_actor_girl_idle_jump_start_l` | idle=待机 | controller-linked / `main/22f5a2da5b28505a2e6b6d3c.ab` | 1.401709 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 361 |
| `A_actor_girl_walk_quickstop_l` | walk=行走 | controller-linked / `main/1d5ef602c151440291feb120.ab` | 2.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_girl_walk_stop_l` | walk=行走 | controller-linked / `main/1d5ef602c151440291feb120.ab` | 2.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 358 |
| `A_actor_jsspsi_relax_sp_02` | relax=放松/待机 | controller-linked / `main/1a73e30ae23550bca25bf3f0.ab` | 15.916668 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1081 |
| `A_actor_girl_walk_bump_r` | walk=行走 | controller-linked / `main/19a90b7b60d0857d99440710.ab` | 1.566667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 355 |
| `A_actor_girl_walk_stop_strafe_r` | walk=行走 | controller-linked / `main/18e99896b63d01f6ca83a4ae.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 344 |
| `A_actor_jsspsi_relax_sp_01` | relax=放松/待机 | controller-linked / `main/16e85b40d5859c0a14fefde5.ab` | 11.35 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1094 |
| `A_actor_girl_idle_bump_heavy_f` | idle=待机 | controller-linked / `main/1683a476e7054db2e2041e29.ab` | 2.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 356 |
| `A_actor_girl_idle_loop` | idle=待机 | controller-linked / `main/12e36e32b1f9c18b25c1c865.ab` | 2.0 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 378 |
| `A_actor_jsspsi_walk_loop_sp_01` | walk=行走 | controller-linked / `main/0ed3bb646b515357d83b64da.ab` | 7.716667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 1155 |
| `A_actor_girl_walk_start_r_180_l` | walk=行走 | controller-linked / `main/0b20f0689f85d8135e64908f.ab` | 1.666667 | not marked in name/top-level fields | not marked in name/top-level fields | FloatBufferData;RootMotionBufferData;TransformBufferData | 383 |

## 663 `npc` rows: literal FloatCurve attribute values

| attribute value | occurrences |
|---|---:|

### Representative decoded float curve objects


### typeID 4 facial path string examples

- None: matching generic binding path fields were numeric values, so no facial names were guessed from hashes.
