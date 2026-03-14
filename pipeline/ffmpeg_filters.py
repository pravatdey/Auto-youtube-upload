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

    # Step 2b: Blur additional regions (list of regions)
    extra_blurs = config.get("extra_blur_regions", [])
    for idx, region in enumerate(extra_blurs):
        bx, by, bw, bh = _parse_region(region, video_width, video_height)
        label_base = f"ebl{idx}_base"
        label_src = f"ebl{idx}_src"
        label_blurred = f"ebl{idx}_blurred"
        label_out = f"v_ebl{idx}"
        chains.append(
            f"[{current}]split[{label_base}][{label_src}];"
            f"[{label_src}]crop={bw}:{bh}:{bx}:{by},boxblur=10[{label_blurred}];"
            f"[{label_base}][{label_blurred}]overlay={bx}:{by}[{label_out}]"
        )
        current = label_out

    # Step 3: Intro overlay - cover first N seconds with branding to hide original marketing
    intro_duration = config.get("intro_cover_duration", 0)
    if intro_duration > 0:
        font_path = _find_font(config)
        fontfile_arg = f"fontfile={font_path}:" if font_path else ""

        # Cover the entire top area (StudyIQ banner + logo + title area) for intro duration
        # Draw a dark overlay box covering the top portion where StudyIQ branding appears
        intro_regions = config.get("intro_cover_regions", [])
        for ridx, region_cfg in enumerate(intro_regions):
            rx, ry, rw, rh = _parse_region(region_cfg["region"], video_width, video_height)
            label = f"v_icover{ridx}"
            chains.append(
                f"[{current}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
                f"color={region_cfg.get('color', 'black')}@{region_cfg.get('opacity', '0.95')}:"
                f"t=fill:enable='lt(t,{intro_duration})'[{label}]"
            )
            current = label

        # Draw your name over the covered area during intro
        intro_name = config.get("intro_name")
        if intro_name:
            escaped_name = intro_name.replace("'", "\\'").replace(":", "\\:")
            intro_name_size = config.get("intro_name_fontsize", 36)
            intro_name_color = config.get("intro_name_color", "white")
            label = "v_iname"
            chains.append(
                f"[{current}]drawtext="
                f"{fontfile_arg}"
                f"text='{escaped_name}':"
                f"fontcolor={intro_name_color}:"
                f"fontsize={intro_name_size}:"
                f"x=(w-tw)/2:y=(h-th)/2+50:"
                f"enable='lt(t,{intro_duration})'[{label}]"
            )
            current = label

        # Draw channel/tutorial name during intro
        intro_channel = config.get("intro_channel_text")
        if intro_channel:
            escaped_ch = intro_channel.replace("'", "\\'").replace(":", "\\:")
            ch_size = config.get("intro_channel_fontsize", 28)
            label = "v_ich"
            chains.append(
                f"[{current}]drawtext="
                f"{fontfile_arg}"
                f"text='{escaped_ch}':"
                f"fontcolor=yellow:"
                f"fontsize={ch_size}:"
                f"x=(w-tw)/2:y=(h-th)/2-30:"
                f"enable='lt(t,{intro_duration})'[{label}]"
            )
            current = label

    # Step 4: Overlay PNG logo at all configured positions
    effective_logo = logo_path or config.get("logo_path")
    if effective_logo and os.path.isfile(effective_logo):
        uses_logo = True

        # Build list of logo placements: primary + extra positions
        logo_placements = []
        primary_scale = config.get("logo_scale", 0.12)
        primary_pos = config.get("logo_position", "bottom-right")
        logo_placements.append({"position": primary_pos, "scale": primary_scale})

        for extra in config.get("extra_logo_positions", []):
            logo_placements.append({
                "position": extra.get("position", "top-right"),
                "scale": extra.get("scale", primary_scale),
            })

        for idx, placement in enumerate(logo_placements):
            scale = placement["scale"]
            pos = _position_expr(placement["position"])
            logo_label = f"logo{idx}"
            out_label = f"v_logo{idx}"
            chains.append(
                f"[1:v]scale=iw*{scale}:-1[{logo_label}];"
                f"[{current}][{logo_label}]overlay={pos}[{out_label}]"
            )
            current = out_label

    # Step 5: Draw text watermark (your branding text - always visible)
    text = config.get("watermark_text")
    if text:
        font_path = _find_font(config)
        font_size = config.get("font_size", 24)
        font_color = config.get("font_color", "white@0.75")
        tx, ty = _text_position_expr(config.get("text_position", "top-left"))
        escaped = text.replace("'", "\\'").replace(":", "\\:")

        fontfile_arg = f"fontfile={font_path}:" if font_path else ""
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

    # Step 6: Draw name at bottom during intro only (replaces original teacher name)
    intro_byline = config.get("intro_byline")
    if intro_byline and intro_duration > 0:
        font_path = _find_font(config)
        fontfile_arg = f"fontfile={font_path}:" if font_path else ""
        escaped_bl = intro_byline.replace("'", "\\'").replace(":", "\\:")
        bl_size = config.get("intro_byline_fontsize", 20)
        bl_color = config.get("intro_byline_color", "white")
        chains.append(
            f"[{current}]drawtext="
            f"{fontfile_arg}"
            f"text='{escaped_bl}':"
            f"fontcolor={bl_color}:"
            f"fontsize={bl_size}:"
            f"x=(w-tw)/2:y=h-th-20:"
            f"box=1:boxcolor=black@0.5:boxborderw=5:"
            f"enable='lt(t,{intro_duration})'[v_byline]"
        )
        current = "v_byline"

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


def build_audio_filters(pitch_shift: float, sample_rate: int = 44100, intro_mute_duration: int = 0) -> list[str]:
    """Build the audio filter for pitch shifting and intro muting.

    Returns list of ffmpeg CLI args for audio processing.
    """
    af_parts = []

    # Mute first N seconds to remove original branding audio
    if intro_mute_duration > 0:
        af_parts.append(f"volume=enable='lt(t,{intro_mute_duration})':volume=0")

    if pitch_shift != 1.0:
        tempo = 1.0 / pitch_shift
        tempo_filters = _chain_atempo(tempo)

        af_parts.extend([
            f"aformat=channel_layouts=stereo",
            f"asetrate={sample_rate}*{pitch_shift}",
            *tempo_filters,
            f"aresample={sample_rate}",
        ])

    if not af_parts:
        return ["-map", "0:a", "-c:a", "copy"]

    af = ",".join(af_parts)
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
                return _escape_font_path(os.path.join(font_dir, f))

    # Fallback to Windows system fonts
    win_fonts = "C:/Windows/Fonts"
    for name in ["arial.ttf", "calibri.ttf", "segoeui.ttf", "verdana.ttf"]:
        path = os.path.join(win_fonts, name)
        if os.path.isfile(path):
            return _escape_font_path(path)

    return None


def _escape_font_path(path: str) -> str:
    """Escape font path for FFmpeg filtergraph: backslash colons and use forward slashes."""
    return path.replace("\\", "/").replace(":", "\\\\:")
