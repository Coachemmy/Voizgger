import json
import os
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

def process_voice_to_ledger(audio_bytes: bytes, filename: str) -> dict:
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
        print("--- RAW META ASR RESPONSE ---")
        print(json.dumps(response_json, indent=2))
        print("-----------------------------")

        if asr_response.status_code != 200:
            return {"error": f"Meta ASR Error: {asr_response.status_code} - {asr_response.text}"}

        transcript_text = response_json.get("transcript", "")
        
        if not transcript_text and response_json.get("turns"):
            turns = response_json["turns"]
            if len(turns) > 0:
                transcript_text = turns[0].get("transcript", "")

        if not transcript_text:
            return {"error": "Transcription was empty. Please check terminal for the raw response."}

        prompt = f"""
        You are a financial assistant for a local market trader. 
        Here is a transcript of them speaking: "{transcript_text}"
        
        Extract the following information and output ONLY a valid JSON object with these keys:
        - "items": list of items mentioned
        - "quantity": list of quantities (numbers only)
        - "amount_paid": total amount paid (number only, no currency symbols)
        - "amount_owed": total amount owed (number only, 0 if none)
        - "summary": a 1-sentence summary of the transaction.
        - "follow_up_sms": A polite, short SMS the trader can send to the customer to remind them of the debt. If no debt, return an empty string.

        Example output:
        {{
            "items": ["Rice", "Beans"],
            "quantity": [5, 2],
            "amount_paid": 50000,
            "amount_owed": 10000,
            "summary": "Sold 5 bags of rice and 2 bags of beans for 60k, customer paid 50k and owes 10k.",
            "follow_up_sms": "Hello! Just a quick reminder about the 10,000 Naira balance for the rice and beans. Please let me know when you can complete the payment. Thank you!"
        }}
        """

        chat_response = client.chat.completions.create(
            model=settings.MODEL_TEXT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )

        raw_json = chat_response.choices[0].message.content.strip()
       
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:-3].strip()
        elif raw_json.startswith("```"):
            raw_json = raw_json[3:-3].strip()

        try:
            structured_data = json.loads(raw_json)
        except json.JSONDecodeError:
            return {"error": "The AI generated an invalid response. Please try a shorter voice note."}

        structured_data["transcript"] = transcript_text
        return structured_data

    except Exception as e:
        print(f"Error details: {str(e)}")
        return {"error": str(e)}