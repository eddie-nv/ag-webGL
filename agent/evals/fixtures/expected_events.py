"""Per-prompt event-count expectations used in M5 (mocked) and M8 (e2e)."""

TOMATO_EXPECTED: dict[str, dict[str, int]] = {
    "scene:camera_move": {"min": 1},
    "scene:object_add": {"min": 3, "max": 30},
    "scene:light_add": {"min": 2},
    "scene:animation_start": {"min": 2},
}
