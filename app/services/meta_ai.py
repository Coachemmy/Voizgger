import base64
import json
import os
import re
import tempfile
import subprocess
import imageio_ffmpeg
import httpx
from openai import OpenAI
from app.core.config import settings

client = OpenAI(base_url=settings.META_BASE_URL, api_key=settings.META_API_KEY)


def convert_to_wav(audio_bytes: bytes) -> bytes:
    """
    Converts any audio format to strict 16kHz mono 16-bit PCM WAV using temp files.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_in:
        tmp_in.write(audio_bytes)
        in_path = tmp_in.name

    out_path = in_path + ".wav"

    try:
        subprocess.run(
            [ffmpeg_exe, "-y", "-i", in_path, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        with open(out_path, "rb") as f:
            wav_bytes = f.read()

        return wav_bytes

    except subprocess.CalledProcessError:
        raise Exception("FFmpeg failed to convert audio. Ensure the file is valid.")
    finally:
        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply that may contain prose or fences."""
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


def _chat(
    prompt: str,
    *,
    deep_audit: bool = False,
    max_tokens: int = 3000,
    effort: str | None = None,
) -> str:
    kwargs = {
        "model": settings.MODEL_TEXT,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000 if deep_audit else max_tokens,
    }
    if deep_audit:
        kwargs["reasoning_effort"] = "high"
    elif effort:
        kwargs["reasoning_effort"] = effort

    response = client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    content = (choice.message.content or "").strip()

    if not content:
        raise Exception(
            f"The AI returned an empty response (finish_reason: {choice.finish_reason}). "
            "Try a shorter voice note."
        )
    return content


def process_voice_to_ledger(
    audio_bytes: bytes,
    filename: str,
    language: str = "English",
    deep_audit: bool = False,
) -> dict:
    try:
        wav_bytes = convert_to_wav(audio_bytes)
        print(f"\n[DEBUG] Converted WAV size: {len(wav_bytes)} bytes")

        headers = {"Authorization": f"Bearer {settings.META_API_KEY}"}

        request_data = {
            "model": "muse-voice-transcribe-1.0",
            "audioEncoding": "WAV",
            "mode": "PUSH_TO_TALK",
            "languageBias": ["English"]
        }

        files = {
            "request": (None, json.dumps(request_data), "application/json"),
            "audio": ("audio.wav", wav_bytes, "audio/wav"),
        }

        with httpx.Client() as http_client:
            asr_response = http_client.post(
                f"{settings.META_BASE_URL}/asr/transcribe",
                headers=headers,
                files=files,
                timeout=60.0,
            )

        print(f"[DEBUG] Status: {asr_response.status_code}")
        response_json = asr_response.json()

        if asr_response.status_code != 200:
            return {"error": f"Meta ASR Error: {asr_response.status_code} - {asr_response.text}"}

        transcript_text = response_json.get("transcript", "")

        if not transcript_text and response_json.get("turns"):
            turns = response_json["turns"]
            if len(turns) > 0:
                transcript_text = turns[0].get("transcript", "")

        if not transcript_text:
            return {
                "error": (
                    "We didn't catch any speech in that recording. "
                    "Check that your microphone is working, then try again."
                ),
                "empty_audio": True,
            }

        target_language = (language or "English").strip() or "English"
        audit_note = (
            "This is a DEEP AUDIT. Think carefully about quantities, prices, discounts and any "
            "conditional debts before answering. Flag anything that does not add up inside "
            "the summary."
            if deep_audit else ""
        )

        prompt = f"""
        You are a financial assistant for a local market trader.
        Here is a transcript of them speaking: "{transcript_text}"
        {audit_note}

        Extract the transaction and reply with ONLY a valid JSON object.
        No markdown, no code fences, no explanation.
        Every human-readable value MUST be written in {target_language}.

        Keys:
        - "items": array of item names. If the speaker states a packaging size or weight
          ("twenty-five kilo rice", "50kg bag"), append it in parentheses: "Rice (25kg)".
          Never invent a size the speaker did not say.
        - "quantity": array of quantities as numbers (same order as items)
        - "amount_paid": number only, no currency symbols
        - "amount_owed": number only, 0 if none
        - "summary": one sentence describing the transaction
        - "translated_transcript": the transcript rendered naturally in {target_language}
        - "follow_up_sms": polite short payment reminder in {target_language}; empty string if no debt
        - "confidence": integer 0-100, how sure you are the extraction is correct
        - "item_confidence": array of integers 0-100, one per item, in the same order

        Example output:
        {{
            "items": ["Rice (25kg)", "Beans"],
            "quantity": [5, 2],
            "amount_paid": 50000,
            "amount_owed": 10000,
            "summary": "Sold 5 bags of rice and 2 bags of beans for 60k, customer paid 50k and owes 10k.",
            "translated_transcript": "I sold five bags of rice and two bags of beans for sixty thousand. The customer paid fifty thousand and still owes ten thousand.",
            "follow_up_sms": "Hello! Just a quick reminder about the 10,000 Naira balance for the rice and beans. Please let me know when you can complete the payment. Thank you!",
            "confidence": 94,
            "item_confidence": [96, 92]
        }}
        """

        structured_data = _extract_json(
            _chat(prompt, deep_audit=deep_audit, max_tokens=3000)
        )

        structured_data["transcript"] = transcript_text
        structured_data["language"] = target_language
        structured_data["deep_audit"] = deep_audit
        return structured_data

    except Exception as e:
        print(f"Error details: {str(e)}")
        return {"error": str(e)}


def translate_ledger(
    transcript: str,
    items: list,
    summary: str,
    follow_up_sms: str,
    language: str,
) -> dict:
    """Re-render an existing ledger in another language without re-processing the audio."""
    target_language = (language or "English").strip() or "English"

    if target_language.lower() == "english":
        return {
            "transcript": transcript,
            "items": items,
            "summary": summary,
            "follow_up_sms": follow_up_sms,
            "language": "English",
        }

    payload = {
        "transcript": transcript or "",
        "items": items or [],
        "summary": summary or "",
        "follow_up_sms": follow_up_sms or "",
    }

    prompt = f"""
    Translate this sales transaction record into {target_language}.
    Keep every number, quantity and currency amount exactly as it is.
    Reply with ONLY a valid JSON object using these keys:
    - "transcript": the transcript in {target_language}
    - "summary": the summary in {target_language}
    - "follow_up_sms": the reminder message in {target_language} (empty string stays empty)
    - "items": the item names in {target_language}, same order and same length as the input

    RECORD:
    {json.dumps(payload, ensure_ascii=False)}
    """

    try:
        data = _extract_json(_chat(prompt, max_tokens=3000, effort="low"))
    except Exception as e:
        return {"error": f"Translation failed: {str(e)}"}

    # Never let a bad translation break the ledger: fall back to the source values
    translated_items = data.get("items")
    if not isinstance(translated_items, list) or len(translated_items) != len(payload["items"]):
        translated_items = payload["items"]

    return {
        "transcript": data.get("transcript") or payload["transcript"],
        "items": translated_items,
        "summary": data.get("summary") or payload["summary"],
        "follow_up_sms": data.get("follow_up_sms", payload["follow_up_sms"]),
        "language": target_language,
    }


def base_item_name(name: str) -> str:
    """'Rice (50kg)' -> 'rice' — match on the product, not the packaging spec."""
    return re.sub(r"\s*\(.*?\)", "", str(name)).strip().lower()


_SPEC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kgs|kg|g|ml|cl|l)\b", re.IGNORECASE)


def parse_packaging_spec(text: str) -> str:
    """'25 Kgs Net' / '50 kg' / '500ml' -> '25kg' / '50kg' / '500ml'. Blank when unreadable."""
    match = _SPEC_RE.search(str(text or ""))
    if not match:
        return ""
    unit = match.group(2).lower().rstrip("s")
    return f"{match.group(1)}{unit}"


def spec_from_item_name(name: str) -> str:
    """Pull the size out of 'Rice (50kg)' so it can be compared with the photo."""
    match = re.search(r"\(([^)]*)\)", str(name))
    return parse_packaging_spec(match.group(1)) if match else ""


def photo_label(name: str, spec: str) -> str:
    """Describe what the photo shows: product name + the size actually printed on it.

    The model can echo the requested name (including the recorded size) back at us, so the
    label is rebuilt from the plain product name and the spec it read from the image.
    """
    base = re.sub(r"\s*\(.*?\)", "", str(name or "")).strip()
    size = parse_packaging_spec(spec)
    return f"{base} ({size})" if size else base


def compare_stock(detected: list, items: list, quantities: list) -> dict:
    """Match model-detected stock against the spoken ledger. Pure — no network."""
    counts: dict = {}
    specs: dict = {}
    for row in detected:
        name = str(row.get("item", "")).strip().lower()
        if not name:
            continue
        counts[name] = counts.get(name, 0) + int(row.get("count", 0) or 0)
        spec = parse_packaging_spec(row.get("spec", "")) or spec_from_item_name(name)
        if spec:
            specs.setdefault(name, set()).add(spec)

    def related(name: str, item: str) -> bool:
        if name == item.lower():
            return True
        base = base_item_name(item)
        if not base:
            return False
        other = base_item_name(name)
        return base in other or other in base

    def detected_count(item: str) -> int:
        return sum(n for name, n in counts.items() if related(name, item))

    def detected_specs(item: str) -> set:
        found = set()
        for name, spec_set in specs.items():
            if related(name, item):
                found |= spec_set
        return found

    spoken = {
        str(item).strip(): int(quantities[i] or 0) if i < len(quantities) else 0
        for i, item in enumerate(items)
    }

    checks = []
    short = []
    packaging = []
    for item, qty in spoken.items():
        seen = detected_count(item)
        recorded_spec = spec_from_item_name(item)
        seen_specs = detected_specs(item)

        if seen < qty:
            status = "short"
            short.append(item)
        elif recorded_spec and seen_specs and recorded_spec not in seen_specs:
            status = "packaging"
            packaging.append(item)
        else:
            status = "match"

        checks.append(
            {
                "item": item,
                "recorded": qty,
                "detected": seen,
                "recorded_spec": recorded_spec,
                "seen_spec": ", ".join(sorted(seen_specs)),
                "status": status,
            }
        )

    shown = ", ".join(
        f"{row.get('count')} × {photo_label(row.get('item', ''), row.get('spec', ''))}"
        for row in detected
    ) or "nothing recognisable"
    recorded = ", ".join(f"{qty} × {item}" for item, qty in spoken.items())

    # Items whose size was never spoken: the photo may show one, but there is nothing to
    # compare it against, so say so instead of implying the size was verified.
    unverified_specs = [
        item for item in spoken if not spec_from_item_name(item) and detected_specs(item)
    ]

    if not detected:
        verdict = "unknown"
        message = "No goods could be recognised in this photo. Try a clearer, straight-on shot."
    elif short:
        verdict = "review"
        message = (
            f"Photo shows {shown}. The recorded sale was {recorded} — "
            f"{', '.join(short)} look short, so double-check the ledger."
        )
    elif packaging:
        verdict = "review"
        message = (
            f"Photo shows {shown}. The count matches, but the packaging size does not — "
            f"{', '.join(packaging)} was recorded at a different size than what is on the shelf. "
            "Recheck the sale before it becomes an invoice."
        )
    else:
        verdict = "consistent"
        message = f"Photo shows {shown}. That matches the quantities you recorded ({recorded})."
        if unverified_specs:
            message += (
                f" The packaging size for {', '.join(unverified_specs)} was not stated in the "
                "recording, so it could not be verified."
            )

    return {
        "verdict": verdict,
        "message": message,
        "short": short,
        "packaging": packaging,
        "spoken": spoken,
        "checks": checks,
    }


def verify_inventory(image_bytes: bytes, mime_type: str, items: list, quantities: list) -> dict:
    """
    Visual verification: muse-wonder counts the stock visible in a photo so the
    recorded quantities (and packaging sizes) can be sanity-checked.
    """
    if not items:
        return {"error": "Process a transaction before running a visual audit."}

    mime_type = mime_type or "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode()

    prompt = (
        "You are a stock verification assistant for a market trader. "
        "Look at the photo of their stock — it may be a shop shelf, a store room, or a delivery load. "
        "For each item below, count how many units are visible: "
        f"{json.dumps(items, ensure_ascii=False)}. "
        "Item names may include a packaging spec in parentheses like 'Rice (50kg)' — match by the "
        "product itself: any bag/sack of rice counts as 'Rice (50kg)', regardless of the brand. "
        "Also read the size printed on the packaging (e.g. '25 Kgs Net' -> '25kg') so a size "
        "mismatch can be caught. "
        'Reply ONLY with JSON: {"detected":[{"item":"<plain product name, no parentheses or sizes>","count":<int>,'
        '"spec":"<size printed on the packaging, e.g. 25kg, or empty string if none is legible>"}],'
        '"confidence":<0-100>}. The "spec" must be read from the photo itself — never copy the '
        "size from my list above into it. If an item is not visible at all, use count 0."
    )

    body = {
        "model": settings.MODEL_VISION,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:{mime_type};base64,{b64}"},
                ],
            }
        ],
    }

    try:
        with httpx.Client() as http_client:
            response = http_client.post(
                f"{settings.META_BASE_URL}/responses",
                headers={
                    "Authorization": f"Bearer {settings.META_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=180.0,
            )

        if response.status_code != 200:
            return {"error": f"Vision Error: {response.status_code} - {response.text[:300]}"}

        payload = response.json()
        text = ""
        for block in payload.get("output", []):
            if block.get("type") == "message":
                for part in block.get("content", []):
                    if part.get("type") == "output_text":
                        text += part.get("text", "")

        data = _extract_json(text)
        detected = data.get("detected") or []

    except Exception as e:
        return {"error": f"Visual audit failed: {str(e)}"}

    # Compare detected stock against what the trader said they sold
    result = compare_stock(detected, items, quantities)

    return {
        "detected": detected,
        "verdict": result["verdict"],
        "message": result["message"],
        "checks": result["checks"],
        "confidence": data.get("confidence"),
    }
