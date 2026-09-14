# Tests

`tools/test.sh` runs every `test_*.gd` here; `tools/test.sh plot regrow` runs only tests whose `file.method` contains one of the words. Preflight runs the whole suite and fails on any failed check or any script error printed during a test.

## What gets a test

- Every script under `scripts/` whose logic runs without a scene tree: game rules, save format, calendar, crop growth, procedural placement. One test file per script, named after it.
- Every file under `data/`: a `test_data.gd` check that the game can read it and that its values are in range. Adding a data file means adding a check.
- A bug fix starts with a failing test that reproduces it.

Scenes, input, and drawing are covered by preflight's scene load and by the committed previews, not by tests here.

## Writing one

- `extends TestCase`; methods named `test_*`; `check`, `check_eq`, `check_near`, `fail` record failures without stopping the test. Override `setup` and `teardown` for fixtures; free any Node you create in `teardown`.
- Each test gets a fresh instance, a reset `game` autoload, a fixed random seed, and an empty `user://tests/` directory. Write files only through `temp_path`.
- Build small crops with `CropData.from_dict` instead of relying on entries in `crops.json`, unless the test is about that data.
