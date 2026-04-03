# drivers/coreldraw.py
# Controls CorelDRAW via two methods:
# Method 1: COM automation (preferred, modern versions)
# Method 2: VBA macro file injection (fallback, works on X7+)

import os
import time
import datetime
import subprocess
from pathlib import Path
from config.settings import OUTPUT_FOLDER, DESIGN_APPS

try:
    import pythoncom
    import win32com.client
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[CorelDRAW] pywin32 not installed — driver disabled")


CORELDRAW_PATH = DESIGN_APPS.get("coreldraw", {}).get("path", "")
VISIBLE = os.getenv("DESIGN_APP_VISIBLE", "true").lower() == "true"


def is_available() -> bool:
    return WIN32_AVAILABLE


def _mm_to_inches(mm: float) -> float:
    return mm / 25.4


def _hex_to_rgb(hex_color: str) -> tuple:
    try:
        hex_color = hex_color.lstrip("#").strip()
        if len(hex_color) < 6:
            return (44, 44, 44)  # safe dark grey fallback
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )
    except Exception:
        return (44, 44, 44)  # fallback if anything goes wrong


def _pick_font(font_style: str) -> str:
    fonts = {
        "modern":      "Montserrat",
        "bold":        "Impact",
        "classic":     "Times New Roman",
        "handwritten": "Segoe Print",
        "thin":        "Gill Sans MT",
    }
    return fonts.get(font_style, "Arial")


def _get_coreldraw_com():
    """
    Tries every known ProgID to connect to CorelDRAW.
    Returns the COM object or raises if none work.
    """
    pythoncom.CoInitialize()
    prog_ids = [
        "CorelDRAW.Application.17",  # X7 2015
        "CorelDRAW.Application.23",  # 2021
        "CorelDRAW.Application.24",  # 2022
        "CorelDRAW.Application.25",  # 2023
        "CorelDRAW.Application.26",  # 2024
        "CorelDRAW.Application",     # generic
    ]
    for prog_id in prog_ids:
        try:
            app = win32com.client.Dispatch(prog_id)
            print(f"[CorelDRAW] Connected via: {prog_id}")
            return app
        except Exception:
            continue
    raise RuntimeError(
        "Could not connect to CorelDRAW via COM.\n"
        "Trying VBA macro fallback..."
    )


def _generate_vba_macro(plan: dict, output_png: str, image_path: str = None) -> str:
    """
    Generates a CorelDRAW VBA macro (.bas file) from the design plan.
    This is the fallback method when COM launch fails.
    CorelDRAW can run .bas macros directly.
    """
    colors   = plan.get("color_palette", {})
    bg_r, bg_g, bg_b       = _hex_to_rgb(colors.get("background", "#1a1a2e"))
    pri_r, pri_g, pri_b    = _hex_to_rgb(colors.get("primary", "#ffffff"))
    acc_r, acc_g, acc_b    = _hex_to_rgb(colors.get("accent", "#ff6600"))

    dims      = plan.get("dimensions", {})
    width_mm  = dims.get("width_mm", 210)
    height_mm = dims.get("height_mm", 297)
    width_in  = _mm_to_inches(width_mm)
    height_in = _mm_to_inches(height_mm)

    title    = plan.get("title", "Design").replace('"', "'").upper()
    subtitle = plan.get("subtitle", "").replace('"', "'")
    body     = plan.get("body_text", "").replace('"', "'")
    font     = _pick_font(plan.get("font_style", "bold"))

    # Escape output path for VBA
    output_png_vba = output_png.replace("\\", "\\\\")

    macro = f'''
Sub DesignAgent_CreateDesign()
    Dim doc As Object
    Dim page As Object
    Dim layer As Object
    Dim rect As Object
    Dim txt As Object
    Dim line As Object

    ' Create new document
    Set doc = CreateDocument()
    Set page = doc.ActivePage
    page.SizeWidth = {width_in}
    page.SizeHeight = {height_in}

    Set layer = page.ActiveLayer

    ' Background rectangle
    Set rect = layer.CreateRectangle2(0, 0, {width_in}, {height_in})
    rect.Fill.UniformColor.RGBAssign({bg_r}, {bg_g}, {bg_b})
    rect.Outline.Color.RGBAssign({bg_r}, {bg_g}, {bg_b})

    ' Title text
    Set txt = layer.CreateArtisticText({width_in * 0.1}, {height_in * 0.75}, "{title}")
    txt.Fill.UniformColor.RGBAssign({pri_r}, {pri_g}, {pri_b})
    txt.Characters.All.Font = "{font}"
    txt.Characters.All.Size = 72

    ' Subtitle text
    Set txt = layer.CreateArtisticText({width_in * 0.1}, {height_in * 0.62}, "{subtitle}")
    txt.Fill.UniformColor.RGBAssign({acc_r}, {acc_g}, {acc_b})
    txt.Characters.All.Size = 36

    ' Body text
    Set txt = layer.CreateArtisticText({width_in * 0.1}, {height_in * 0.15}, "{body}")
    txt.Fill.UniformColor.RGBAssign({pri_r}, {pri_g}, {pri_b})
    txt.Characters.All.Size = 24

    ' Decorative line
    Dim line As Shape
    Set line = layer.CreateLineSegment({width_in * 0.1}, {height_in * 0.60}, {width_in * 0.9}, {height_in * 0.60})
    line.Outline.Color.RGBAssign({acc_r}, {acc_g}, {acc_b})
    line.Outline.Width = 0.02

    ' Export as PNG
    doc.ExportBitmap "{output_png_vba}", cdrPNG, cdrAllPages, 300

    MsgBox "DesignAgent: Done! Saved to {output_png_vba}"
End Sub
'''
    return macro


def run_design(plan: dict, image_path: str = None) -> dict:
    """
    Main entry point. Tries COM first, falls back to VBA macro.
    """
    if not WIN32_AVAILABLE:
        return {
            "success": False,
            "error": "pywin32 not installed. Run: pip install pywin32",
            "output_png": None,
        }

    if not plan:
        return {
            "success": False,
            "error": "Empty design plan",
            "output_png": None,
        }

    # ── Setup output paths ────────────────────────────────────
    timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    job_name   = plan.get("title", "design").replace(" ", "_")[:30]
    job_folder = OUTPUT_FOLDER / f"{timestamp}_{job_name}"
    job_folder.mkdir(parents=True, exist_ok=True)

    output_cdr = str(job_folder / f"{job_name}.cdr")
    output_png = str(job_folder / f"{job_name}.png")
    macro_path = str(job_folder / f"{job_name}.bas")

    print(f"[CorelDRAW] Job: {job_name}")
    print(f"[CorelDRAW] Output: {job_folder}")

    # ── Method 1: COM automation ──────────────────────────────
    try:
        corel = _get_coreldraw_com()
        corel.Visible = VISIBLE

        dims      = plan.get("dimensions", {})
        width_in  = _mm_to_inches(dims.get("width_mm", 210))
        height_in = _mm_to_inches(dims.get("height_mm", 297))

        doc = corel.CreateDocument()
        page = doc.ActivePage
        page.SizeWidth = width_in
        page.SizeHeight = height_in

        colors = plan.get("color_palette", {})
        bg_r, bg_g, bg_b    = _hex_to_rgb(colors.get("background", "#1a1a2e"))
        pri_r, pri_g, pri_b = _hex_to_rgb(colors.get("primary", "#ffffff"))
        acc_r, acc_g, acc_b = _hex_to_rgb(colors.get("accent", "#ff6600"))

        # Background
        bg_rect = page.ActiveLayer.CreateRectangle2(0, 0, width_in, height_in)
        bg_rect.Fill.UniformColor.RGBAssign(bg_r, bg_g, bg_b)
        bg_rect.Outline.Color.RGBAssign(bg_r, bg_g, bg_b)

        # Image
        if image_path and Path(image_path).exists():
            img = page.ActiveLayer.Import(image_path)
            img.SetPosition(width_in * 0.1, height_in * 0.2)
            img.SetSize(width_in * 0.8, height_in * 0.5)

     # Title
        title = plan.get("title", "")
        if title:
            t = page.ActiveLayer.CreateArtisticText(
                width_in * 0.1, height_in * 0.75, title.upper()
            )
            t.Fill.UniformColor.RGBAssign(pri_r, pri_g, pri_b)

        # Subtitle
        subtitle = plan.get("subtitle", "")
        if subtitle:
            s = page.ActiveLayer.CreateArtisticText(
                width_in * 0.1, height_in * 0.65, subtitle
            )
            s.Fill.UniformColor.RGBAssign(acc_r, acc_g, acc_b)

        # Body
        body = plan.get("body_text", "")
        if body:
            b = page.ActiveLayer.CreateArtisticText(
                width_in * 0.1, height_in * 0.15, body
            )
            b.Fill.UniformColor.RGBAssign(pri_r, pri_g, pri_b)

        # Line
        line = page.ActiveLayer.CreateLineSegment(
            width_in * 0.1, height_in * 0.62,
            width_in * 0.9, height_in * 0.62,
        )
        line.Outline.Color.RGBAssign(acc_r, acc_g, acc_b)

        doc.SaveAs(output_cdr)
        doc.ExportBitmap(output_png, 20, 0, 300,
                         int(width_in * 300), int(height_in * 300))

        print(f"[CorelDRAW] ✅ COM method succeeded")
        return {
            "success":    True,
            "method":     "COM",
            "output_cdr": output_cdr,
            "output_png": output_png,
            "job_folder": str(job_folder),
            "error":      None,
        }

    except Exception as com_error:
        print(f"[CorelDRAW] COM failed: {com_error}")
        print(f"[CorelDRAW] Trying VBA macro fallback...")

    # ── Method 2: VBA macro fallback ─────────────────────────
    try:
        macro_code = _generate_vba_macro(plan, output_png, image_path)

        with open(macro_path, "w") as f:
            f.write(macro_code)

        print(f"[CorelDRAW] Macro written: {macro_path}")
        print(f"[CorelDRAW] Open CorelDRAW → Tools → Macros → Run Macro")
        print(f"[CorelDRAW] Select file: {macro_path}")
        print(f"[CorelDRAW] Run: DesignAgent_CreateDesign")

        return {
            "success":    True,
            "method":     "VBA_MANUAL",
            "macro_path": macro_path,
            "output_png": output_png,
            "job_folder": str(job_folder),
            "error":      None,
            "manual_step": (
                f"Open CorelDRAW → Tools → Macros → Load Macro\n"
                f"File: {macro_path}\n"
                f"Run: DesignAgent_CreateDesign"
            )
        }

    except Exception as vba_error:
        print(f"[CorelDRAW] VBA fallback also failed: {vba_error}")
        return {
            "success": False,
            "error":   str(vba_error),
            "output_png": None,
        }