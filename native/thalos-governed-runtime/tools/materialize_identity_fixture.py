"""Write the tiny ONNX Identity fixture from its checked-in hexadecimal form."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEX_PATH = ROOT / "tests" / "fixtures" / "identity_f32_1x4.onnx.hex"
OUT_PATH = ROOT / "tests" / "fixtures" / "identity_f32_1x4.onnx"


def main() -> None:
    encoded = HEX_PATH.read_text(encoding="ascii").strip()
    model = bytes.fromhex(encoded)
    if not model:
        raise SystemExit("fixture is empty")
    OUT_PATH.write_bytes(model)
    print(f"Wrote {OUT_PATH} ({len(model)} bytes)")


if __name__ == "__main__":
    main()
