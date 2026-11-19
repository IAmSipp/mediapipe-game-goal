# Controls and verification

## Learner configuration
`setting/control_settings.py` contains one boolean switch and literal values only.
Preset SKILL_ACTION values: กำมือข้างใดก็ได้, กำมือซ้าย, กำมือขวา, กำมือสองข้าง.
SENSITIVITY accepts 0.5–1.5; HOLD_SECONDS and SMOOTHING_SECONDS accept seconds >= 0.
MOVEMENT_GAIN is positive; confidence thresholds accept 0–1.
Detection, presence and tracking thresholds are passed to HandLandmarkerOptions.
Handedness confidence filters unreliable glove positions.
Set SMOOTHING_SECONDS to 0 to inspect raw movement.

The custom function receives hand dictionaries with side, confidence and 21 landmarks.
It returns `{"gloves": {"Left": (0.2, 0.5), "Right": (0.8, 0.5)}, "skill": False}`.
Omit a missing hand; an empty dictionary means no active gloves.
Coordinates use the mirrored screen: x=0 left, x=1 right, y=0 top.
Return skill=True while your custom gesture is held. The system produces a single press until visible release.
The custom example has no preset dwell or smoothing; learners can change direct if rules.

## Official API references
- [Hand Landmarker Python API and running modes](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python)
- [Official landmark enumeration and options](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/hand_landmarker.py)
- [Official handedness and image tests](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/test/vision/hand_landmarker_test.py)
- [Official hand model](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task)

VIDEO mode calls detect_for_video on unmirrored RGB with strictly increasing milliseconds.
Rendering alone mirrors the camera and overlay; preserve Tasks handedness labels.
Static-model checks compare the official right-hand reference and its horizontal flip; this is separate from a live person's handedness check.
No inference is made with the old Solutions API.

## Reproducible checks
Run from the project root:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s system/tests -v
.\.venv\Scripts\python.exe -m system.tests.manual_checks --fixture-dir PATH_TO_IMAGES
.\.venv\Scripts\python.exe -m system.tests.manual_checks --live
```
Fixture names are right_hands.jpg, pointing_up.jpg and fist.jpg. Verification here reused the template's local test images; the official Tasks tests also reference right_hands.jpg and pointing_up.jpg.
Manual checks write screen renders and a JSON report to ignored system/artifacts/.
Live checking reads a small number of frames, closes the camera/model, and does not save camera photos.
A successful camera read alone does not prove a person performed gestures.

## In-person acceptance
Run main.py, show both open hands, start, move each hand independently and cross arms.
Confirm glove colors follow the correct actual hand.
Try each skill, hold the fist through cooldown, release and trigger again.
Let five balls pass, replay, then play a timed round.
Repeat with USE_PRESET=False. Confirm custom changes remain after switching back to True.
Close the game and confirm the camera can be reopened.
The automated tests cover these game transitions with synthetic inputs, not a human performance.

## Distribution
AI instruction files, PROJECT_FORMAT.md, caches, virtual environments, artifacts and ZIPs are ignored.
The copied template's Git history is not part of this project.
Git export attributes omit local-only instruction files from git archive.
When creating a student ZIP, explicitly exclude those paths and any skill sources.
Keep required models and the official download helper. No GitHub upload or student ZIP is performed by default.
