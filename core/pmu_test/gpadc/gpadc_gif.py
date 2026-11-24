"""GPADC Auto Best 搜索 GIF 编码（纯 Python，无 Qt 依赖）。"""

from pathlib import Path

from PIL import Image


def encode_search_gif_frames(frames, output_path, stop_check=None):
    """将 (RGB bytes, width, height, stride, duration_ms) 帧序列原子写入 GIF。"""
    if not frames:
        raise ValueError("没有可编码的 GIF 帧")

    output = Path(output_path)
    temporary = output.with_suffix(output.suffix + ".tmp")
    images = []
    durations = []

    def _stopped():
        temporary.unlink(missing_ok=True)
        return {
            "saved": False,
            "stopped": True,
            "path": None,
            "frame_count": len(images),
        }

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        for data, width, height, stride, duration_ms in frames:
            if stop_check and stop_check():
                return _stopped()
            image = Image.frombytes(
                "RGB", (int(width), int(height)), bytes(data), "raw", "RGB", int(stride), 1,
            )
            images.append(image)
            durations.append(int(duration_ms))

        palette = images[-1].quantize(
            colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE,
        )
        gif_frames = [
            image.quantize(palette=palette, dither=Image.Dither.NONE)
            for image in images
        ]
        if stop_check and stop_check():
            return _stopped()
        gif_frames[0].save(
            temporary,
            format="GIF",
            save_all=True,
            append_images=gif_frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
        )
        if stop_check and stop_check():
            return _stopped()
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return {
        "saved": True,
        "stopped": False,
        "path": str(output),
        "frame_count": len(gif_frames),
    }
