"""Builds FFmpeg filter graphs for video and audio processing."""

import os


def build_video_filters(config: dict, logo_path: str | None = None, video_width: int = 1920, video_height: int = 1080) -> tuple[list[str], bool]:
    """Build the video filter chain.

    Returns:
        (ffmpeg_args, uses_logo_input): ffmpeg_args is a list of CLI args,
        uses_logo_input indicates if a second input (-i logo.png) is needed.
    """
    chains = []
    current = "0:v"
    uses_logo = False

    # Step 1: Remove existing watermark with delogo
    remove_wm = config.get("remove_watermark")
    if remove_wm:
        x, y, w, h = _parse_region(remove_wm, video_width, video_height)
        chains.append(f"[{current}]delogo=x={x}:y={y}:w={w}:h={h}[v_dl]")
        current = "v_dl"

    # Step 2: Blur a region (for stubborn watermarks)
    blur = config.get("blur_region")
    if blur:
        bx, by, bw, bh = _parse_region(blur, video_width, video_height)
        chains.append(
            f"[{current}]split[blur_base][blur_src];"
            f"[blur_src]crop={bw}:{bh}:{bx}:{by},boxblur=15[blurred];"
            f"[blur_base][blurred]overlay={bx}:{by}[v_bl]"
        )
        current = "v_bl"

    # Step 3: Overlay PNG logo
    effective_logo = logo_path or config.get("logo_path")
    if effective_logo and os.path.isfile(effective_logo):
        uses_logo = True
        scale = config.get("logo_scale", 0.12)
        pos = _position_expr(config.get("logo_position", "bottom-right"))
        chains.append(
            f"[1:v]scale=iw*{scale}:-1[logo];"
            f"[{current}][logo]overlay={pos}[v_logo]"
        )
        current = "v_logo"

    # Step 4: Draw text watermark
    text = config.get("watermark_text")
    if text:
        font_path = _find_font(config)
        font_size = config.get("font_size", 24)
        font_color = config.get("font_color", "white@0.75")
        tx, ty = _text_position_expr(config.get("text_position", "top-left"))
        escaped = text.replace("'", "\\'").replace(":", "\\:")

        fontfile_arg = f"fontfile='{font_path}':" if font_path else ""
        chains.append(
            f"[{current}]drawtext="
            f"{fontfile_arg}"
            f"text='{escaped}':"
            f"fontcolor={font_color}:"
            f"fontsize={font_size}:"
            f"x={tx}:y={ty}:"
            f"box=1:boxcolor=black@0.4:boxborderw=5[v_txt]"
        )
        current = "v_txt"

    if not chains:
        return [], False

    # Rename final output label to [v_out]
    last = chains[-1]
    # Find the last [...] label and rename it
    bracket_start = last.rfind("[")
    final_label = last[bracket_start + 1 : last.rfind("]")]
    if final_label != "v_out":
        chains[-1] = last[: bracket_start] + "[v_out]"

    filter_str = ";".join(chains)
    return ["-filter_complex", filter_str, "-map", "[v_out]"], uses_logo


def build_audio_filters(pitch_shift: float, sample_rate: int = 44100) -> list[str]:
    """Build the audio filter for pitch shifting.

    Returns list of ffmpeg CLI args for audio processing.
    """
    if pitch_shift == 1.0:
        return ["-map", "0:a", "-c:a", "copy"]

    tempo = 1.0 / pitch_shift
    tempo_filters = _chain_atempo(tempo)

    af = (
        f"aformat=channel_layouts=stereo,"
        f"asetrate={sample_rate}*{pitch_shift},"
        f"{','.join(tempo_filters)},"
        f"aresample={sample_rate}"
    )

    return ["-map", "0:a", "-af", af, "-c:a", "aac", "-b:a", "192k"]


def _chain_atempo(factor: float) -> list[str]:
    """Chain atempo filters to stay within [0.5, 100.0] range."""
    filters = []
    while factor < 0.5:
        filters.append("atempo=0.5")
        factor /= 0.5
    while factor > 100.0:
        filters.append("atempo=100.0")
        factor /= 100.0
    filters.append(f"atempo={factor:.6f}")
    return filters


def _position_expr(position: str) -> str:
    """Convert position name to FFmpeg overlay expression."""
    positions = {
        "top-left": "15:15",
        "top-right": "W-w-15:15",
        "bottom-left": "15:H-h-15",
        "bottom-right": "W-w-15:H-h-15",
        "center": "(W-w)/2:(H-h)/2",
    }
    return positions.get(position, "W-w-15:H-h-15")


def _text_position_expr(position: str) -> tuple[str, str]:
    """Convert position name to drawtext x,y expressions."""
    positions = {
        "top-left": ("10", "10"),
        "top-right": ("w-tw-10", "10"),
        "bottom-left": ("10", "h-th-10"),
        "bottom-right": ("w-tw-10", "h-th-10"),
        "center": ("(w-tw)/2", "(h-th)/2"),
    }
    return positions.get(position, ("10", "10"))


def _parse_region(region: str, video_width: int, video_height: int) -> tuple[str, str, str, str]:
    """Parse a region string that supports percentage values.

    Format: "x:y:w:h" where values can be absolute pixels or percentages (e.g. "86%:1%:13%:14%").
    Percentages for x/w are relative to video width, y/h relative to video height.
    Returns pixel values as strings.
    """
    parts = region.split(":")
    ref_dims = [video_width, video_height, video_width, video_height]
    result = []
    for val, ref in zip(parts, ref_dims):
        val = val.strip()
        if val.endswith("%"):
            pct = float(val[:-1]) / 100.0
            result.append(str(int(ref * pct)))
        else:
            result.append(val)
    return tuple(result)


def _find_font(config: dict) -> str | None:
    """Find a usable font file. Check assets/fonts/ first, then Windows system fonts."""
    font_dir = "assets/fonts"
    if os.path.isdir(font_dir):
        for f in os.listdir(font_dir):
            if f.lower().endswith((".ttf", ".otf")):
                return os.path.join(font_dir, f).replace("\\", "/")

    # Fallback to Windows system fonts
    win_fonts = "C:/Windows/Fonts"
    for name in ["arial.ttf", "calibri.ttf", "segoeui.ttf", "verdana.ttf"]:
        path = os.path.join(win_fonts, name)
        if os.path.isfile(path):
            return path.replace("\\", "/")

    return None
