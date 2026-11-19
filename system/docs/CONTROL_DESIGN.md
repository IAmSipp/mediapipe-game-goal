# Goalkeeper control design

The original directory contract, thin launcher, 1120 × 760 window, camera panel, mouse start/replay and resource ownership are preserved. The scene looks out from the goalkeeper's goal toward a football pitch, penalty-area markings, a distant goal, stadium stands and floodlights. Nearby posts and a crossbar frame the view; netting appears only at the sides. A striker winds up before a scheduled shot and follows through after launch. The ball illustration grows and follows an arc from the striker's feet toward its target. Scene colors are editable literal data in setting/game_settings.py.

The two independent circular gloves and the target ring mark the save area. A ball resolves once at the goal plane, rather than colliding with the moving perspective illustration early. Either glove can save any ball, including when arms cross. The drawn flight arc and striker animation do not alter arrival timing or collision coordinates.

Commands contain `gloves`, a dictionary keyed by the subject's actual `Left`/`Right`, and `skill`, a one-frame boolean pulse. Coordinates are normalized display coordinates; the camera is mirrored once for display and control x is transformed with `1 - x`. No half-screen assumption is used to label hands.

Preset controls use middle finger MCP landmark 9 for glove position, gain around the image center and an exponential filter based on elapsed time. Finger tips 8/12/16/20 are compared with PIP joints 6/10/14/18 relative to wrist 0 in image x/y coordinates. This is an intentionally simple teaching heuristic; partial occlusion or a fist turned edge-on can fail detection.

The exclusive custom branch calls `setting.hand_controls.get_goalkeeper_command`. It reads no preset values, including camera thresholds, dwell, confidence, gain or smoothing. Its editable camera options and direct landmark rules live in hand_controls.py. Common command validation, edge triggering and game cooldown do not implement preset gestures.

A visible release arms the skill. A fist held across cooldown expiry does not repeat. Tracking loss resets preset dwell and removes the glove but does not count as release. All hands present at the last press must be visible again before release can rearm the skill. Reset requires a new visible release, clears smoothing and dwell, and removes all round state. With an either-hand gesture, release means no detected hand is making a fist; keep both hands visible for the clearest result.

Skill selection is allowed only on menu/game-over screens. Cooldown starts on activation; skills cannot overlap even if the configured cooldown is shorter than the effect duration. Big gloves enlarge collision and rendering together. Slow ball changes flight progress, not the round clock or cooldown. Shield saves every ball that arrives while active. Score is awarded only for saves. Losing the camera pauses simulation and clears control state; the original restart guidance applies.

Motion and timers use elapsed seconds, with bounded simulation substeps for arrival checks. Skill expiration divides steps so slow-ball motion does not depend on rendering frame rate. Large elapsed intervals advance the round rather than discarding time.
