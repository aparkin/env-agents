# env_agents/core/persistence.py
from __future__ import annotations
import json, os, tempfile, pathlib
import pandas as pd

def save_df_with_meta(df: pd.DataFrame, path: str | os.PathLike, *, compression: str | None = "snappy") -> None:
    p = pathlib.Path(path)
    if p.suffix.lower() != ".parquet":
        raise ValueError("Use a .parquet filename")
    p.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "schema": df.attrs.get("schema"),
        "capabilities": df.attrs.get("capabilities"),
        "variable_registry": df.attrs.get("variable_registry"),
    }

    # Write parquet (optionally compressed)
    df.to_parquet(p, index=False, compression=compression)

    # Atomic sidecar write
    sidecar = p.with_suffix(p.suffix + ".meta.json")
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(sidecar.parent), encoding="utf-8")
    try:
        json.dump(meta, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, sidecar)  # atomic on POSIX
    finally:
        try: os.unlink(tmp.name)
        except FileNotFoundError: pass

def load_df_with_meta(path: str | os.PathLike) -> pd.DataFrame:
    p = pathlib.Path(path)
    if p.suffix.lower() != ".parquet":
        raise ValueError("Use a .parquet filename")
    df = pd.read_parquet(p)
    sidecar = p.with_suffix(p.suffix + ".meta.json")
    if sidecar.exists():
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            # Only attach known keys
            for k in ("schema","capabilities","variable_registry"):
                if k in meta:
                    df.attrs[k] = meta[k]
        except Exception:
            # Don’t fail loads if meta is corrupt/missing
            pass
    return df