"""
VieNeu-TTS — Vercel Entrypoint (Remote Mode)
Loads a lightweight Gradio UI that calls a remote TTS backend.
Set VIENEU_API_BASE environment variable in Vercel project settings.
"""

import os
import sys
import json
import tempfile
import requests
import numpy as np
import soundfile as sf
import gradio as gr

# ── Remote backend config ────────────────────────────────────────────────────
# Set VIENEU_API_BASE in Vercel → Settings → Environment Variables
# Example: https://your-server.com/v1
API_BASE = os.environ.get("VIENEU_API_BASE", "").rstrip("/")
MODEL_NAME = os.environ.get("VIENEU_MODEL", "pnnbao-ump/VieNeu-TTS-v2")

# ── Load built-in voices from JSON ───────────────────────────────────────────
_VOICES_JSON = os.path.join(os.path.dirname(__file__),
                            "src", "vieneu", "assets", "voices.json")
try:
    with open(_VOICES_JSON, encoding="utf-8") as f:
        _vdata = json.load(f)
    _VOICE_CHOICES = [
        (v["description"], k)
        for k, v in _vdata.get("presets", {}).items()
        if "description" in v
    ]
    _VOICE_CHOICES.sort(key=lambda x: x[0])
    _DEFAULT_VOICE = _vdata.get("default_voice", "Binh")
except Exception:
    _VOICE_CHOICES = [("Bình (nam miền Bắc)", "Binh")]
    _DEFAULT_VOICE = "Binh"


def synthesize(text: str, voice_id: str, temperature: float):
    """Call the remote TTS API and return the audio file path."""
    if not API_BASE:
        return None, (
            "❌ Chưa cấu hình server.\n"
            "Vui lòng đặt biến môi trường **VIENEU_API_BASE** trong "
            "Vercel → Project Settings → Environment Variables.\n\n"
            "Ví dụ: `https://your-tts-server.com/v1`"
        )

    if not text or not text.strip():
        return None, "⚠️ Vui lòng nhập văn bản."

    # Get voice codes from local JSON
    voice_codes = _vdata.get("presets", {}).get(voice_id, {}).get("codes", [])
    ref_text = _vdata.get("presets", {}).get(voice_id, {}).get("text", "")

    payload = {
        "model": MODEL_NAME,
        "input": text.strip(),
        "voice": voice_id,
        "ref_codes": voice_codes,
        "ref_text": ref_text,
        "temperature": temperature,
        "response_format": "wav",
    }

    try:
        resp = requests.post(
            f"{API_BASE}/audio/speech",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        return None, f"❌ Không thể kết nối tới server: `{API_BASE}`"
    except requests.exceptions.Timeout:
        return None, "❌ Server phản hồi quá chậm (timeout 120s)."
    except requests.exceptions.HTTPError as e:
        return None, f"❌ Lỗi từ server: {e.response.status_code} — {e.response.text[:200]}"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(resp.content)
        return f.name, "✅ Hoàn tất!"


# ── Gradio UI ────────────────────────────────────────────────────────────────
_STATUS_MSG = (
    f"✅ Đã kết nối: `{API_BASE}`" if API_BASE
    else "⚠️ Chưa cấu hình server — đặt `VIENEU_API_BASE` trong Vercel Environment Variables."
)

css = """
.container { max-width: 900px; margin: auto; }
.header { text-align: center; padding: 20px; background: linear-gradient(135deg,#0f172a,#1e293b);
          border-radius: 12px; color: white; margin-bottom: 20px; }
.header h1 { font-size: 2rem; font-weight: 800; margin: 0; }
.header p  { color: #94a3b8; margin: 6px 0 0; }
"""

with gr.Blocks(title="VieNeu-TTS", css=css) as demo:
    gr.HTML("""
    <div class="header">
        <h1>🦜 VieNeu-TTS</h1>
        <p>Tổng hợp giọng nói tiếng Việt chất lượng cao</p>
    </div>
    """)

    gr.Textbox(value=_STATUS_MSG, label="Trạng thái server", interactive=False,
               elem_classes=["status-box"])

    with gr.Row():
        with gr.Column(scale=3):
            txt_input = gr.Textbox(
                label="Văn bản cần đọc",
                placeholder="Nhập văn bản tiếng Việt hoặc tiếng Anh...",
                lines=5,
            )
        with gr.Column(scale=1):
            dd_voice = gr.Dropdown(
                choices=_VOICE_CHOICES,
                value=_DEFAULT_VOICE,
                label="Giọng đọc",
            )
            sl_temp = gr.Slider(0.1, 1.5, value=0.7, step=0.05,
                                label="Temperature (sáng tạo)")
            btn = gr.Button("🎙️ Tổng hợp", variant="primary")

    audio_out = gr.Audio(label="Kết quả", type="filepath")
    status_out = gr.Textbox(label="Trạng thái", interactive=False)

    btn.click(
        fn=synthesize,
        inputs=[txt_input, dd_voice, sl_temp],
        outputs=[audio_out, status_out],
    )

    gr.Examples(
        examples=[
            ["Hà Nội những ngày vào thu mang một vẻ đẹp trầm mặc và cổ kính đến lạ thường.", "Binh", 0.7],
            ["Về miền Tây không chỉ để ngắm nhìn sông nước hữu tình, mà còn để cảm nhận tấm chân tình.", "Vinh", 0.7],
        ],
        inputs=[txt_input, dd_voice, sl_temp],
    )

# Expose ASGI app for Vercel
app = demo.app

