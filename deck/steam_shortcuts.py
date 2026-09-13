#!/usr/bin/env python3
"""Registers the Farm launchers as Non-Steam games by editing Steam's shortcuts.vdf.

Usage: steam_shortcuts.py FARM_DIR [STEAM_DIR]        register the shortcuts (Steam must not be running)
       steam_shortcuts.py --art FARM_DIR [STEAM_DIR]  refresh the library artwork only (safe while Steam runs)
       steam_shortcuts.py --self-test
"""
import os
import struct
import sys
import tempfile
import zlib

SHORTCUTS = [("Farm", "", "farm"), ("Farm (stable)", "stable", "farm_stable")]
ART_KINDS = {"p": "p", "wide": "", "hero": "_hero", "logo": "_logo"}
OBJECT, STRING, INT, END = 0, 1, 2, 8


def read_vdf(data: bytes, pos: int = 0):
    result = {}
    while True:
        kind = data[pos]
        pos += 1
        if kind == END:
            return result, pos
        end = data.index(b"\x00", pos)
        key = data[pos:end].decode("utf-8")
        pos = end + 1
        if kind == OBJECT:
            result[key], pos = read_vdf(data, pos)
        elif kind == STRING:
            end = data.index(b"\x00", pos)
            result[key] = data[pos:end].decode("utf-8")
            pos = end + 1
        elif kind == INT:
            result[key] = struct.unpack_from("<i", data, pos)[0]
            pos += 4
        else:
            raise ValueError("unknown vdf type %d" % kind)


def write_vdf(obj: dict) -> bytes:
    out = bytearray()
    for key, value in obj.items():
        name = key.encode("utf-8") + b"\x00"
        if isinstance(value, dict):
            out += bytes([OBJECT]) + name + write_vdf(value)
        elif isinstance(value, str):
            out += bytes([STRING]) + name + value.encode("utf-8") + b"\x00"
        else:
            out += bytes([INT]) + name + struct.pack("<i", value)
    out.append(END)
    return bytes(out)


def exe_for(farm: str) -> str:
    return '"%s/deck/play.sh"' % farm


def shortcut_appid(exe: str, name: str) -> int:
    return zlib.crc32((exe + name).encode("utf-8")) | 0x80000000


def shortcut(farm: str, name: str, launch_options: str) -> dict:
    exe = exe_for(farm)
    return {
        "appid": struct.unpack("<i", struct.pack("<I", shortcut_appid(exe, name)))[0],
        "AppName": name,
        "Exe": exe,
        "StartDir": '"%s/deck/"' % farm,
        "icon": "%s/assets/ui/icon.png" % farm,
        "ShortcutPath": "",
        "LaunchOptions": launch_options,
        "IsHidden": 0,
        "AllowDesktopConfig": 1,
        "AllowOverlay": 1,
        "OpenVR": 0,
        "Devkit": 0,
        "DevkitGameID": "",
        "DevkitOverrideAppID": 0,
        "LastPlayTime": 0,
        "FlatpakAppID": "",
        "tags": {},
    }


def install_art(farm: str, config_dir: str) -> int:
    """Copies deck/art/ into Steam's grid folder under each shortcut's app id; returns files written."""
    grid = os.path.join(config_dir, "grid")
    written = 0
    for name, _, art in SHORTCUTS:
        appid = shortcut_appid(exe_for(farm), name)
        for kind, suffix in ART_KINDS.items():
            src = os.path.join(farm, "deck", "art", "%s_%s.png" % (art, kind))
            if not os.path.exists(src):
                continue
            with open(src, "rb") as f:
                data = f.read()
            dst = os.path.join(grid, "%d%s.png" % (appid, suffix))
            if os.path.exists(dst):
                with open(dst, "rb") as f:
                    if f.read() == data:
                        continue
            os.makedirs(grid, exist_ok=True)
            with open(dst, "wb") as f:
                f.write(data)
            written += 1
    return written


def register(farm: str, vdf_path: str) -> list:
    entries = {}
    if os.path.exists(vdf_path):
        with open(vdf_path, "rb") as f:
            entries = read_vdf(f.read())[0].get("shortcuts", {})
    ours = {name: shortcut(farm, name, opts) for name, opts, _ in SHORTCUTS}
    kept = [e for e in entries.values() if e.get("AppName") not in ours]
    merged = {str(i): e for i, e in enumerate(kept + list(ours.values()))}
    os.makedirs(os.path.dirname(vdf_path), exist_ok=True)
    with open(vdf_path, "wb") as f:
        f.write(write_vdf({"shortcuts": merged}))
    return list(ours)


def user_config_dirs(steam: str) -> list:
    userdata = os.path.join(steam, "userdata")
    if not os.path.isdir(userdata):
        return []
    return [os.path.join(userdata, u, "config") for u in sorted(os.listdir(userdata)) if u.isdigit() and u != "0"]


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vdf = os.path.join(tmp, "shortcuts.vdf")
        other = shortcut("/opt/other", "Other Game", "")
        with open(vdf, "wb") as f:
            f.write(write_vdf({"shortcuts": {"0": other}}))
        register("/home/deck/games/farm", vdf)
        register("/home/deck/games/farm", vdf)
        with open(vdf, "rb") as f:
            data = f.read()
        parsed, consumed = read_vdf(data)
        assert consumed == len(data), "trailing bytes"
        entries = list(parsed["shortcuts"].values())
        names = [e["AppName"] for e in entries]
        assert names == ["Other Game", "Farm", "Farm (stable)"], names
        assert list(parsed["shortcuts"]) == ["0", "1", "2"]
        assert entries[0] == other
        assert entries[2]["LaunchOptions"] == "stable"
        assert entries[1]["Exe"] == '"/home/deck/games/farm/deck/play.sh"'
        assert entries[1]["appid"] < 0 and entries[1]["appid"] != entries[2]["appid"]
        assert struct.unpack("<I", struct.pack("<i", entries[1]["appid"]))[0] & 0x80000000
        assert data.startswith(b"\x00shortcuts\x00\x00" + b"0\x00\x02appid\x00")
        assert data.endswith(b"\x00tags\x00\x08\x08\x08\x08")
        farm = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert install_art(farm, tmp) == 8, "expected 8 artwork files"
        assert install_art(farm, tmp) == 0, "second copy must be a no-op"
        appid = shortcut_appid(exe_for(farm), "Farm (stable)")
        assert appid > 0x80000000 and appid < 2**32
        assert os.path.exists(os.path.join(tmp, "grid", "%dp.png" % appid))
        assert os.path.exists(os.path.join(tmp, "grid", "%d_hero.png" % appid))
    print("steam_shortcuts self-test ok")


def main(argv: list) -> int:
    if argv[1:] == ["--self-test"]:
        self_test()
        return 0
    art_only = argv[1:2] == ["--art"]
    args = argv[2:] if art_only else argv[1:]
    if not args:
        print(__doc__)
        return 2
    farm = os.path.abspath(args[0])
    steam = args[1] if len(args) > 1 else os.path.expanduser("~/.steam/steam")
    configs = user_config_dirs(steam)
    if not configs:
        print("No Steam user found under %s; add the shortcuts by hand" % steam)
        return 0
    for config in configs:
        if not art_only:
            names = register(farm, os.path.join(config, "shortcuts.vdf"))
            print("Steam shortcuts written to %s: %s" % (config, ", ".join(names)))
        written = install_art(farm, config)
        if written:
            print("Steam artwork updated in %s (%d files)" % (config, written))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
