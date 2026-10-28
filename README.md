# VoxLedger: Voice-to-Ledger for the Informal Economy

VoxLedger is an AI-powered financial assistant designed for market traders. It allows users to record a voice note in natural language (e.g., Pidgin or English) describing a transaction, and automatically converts it into a structured digital ledger.

## 🚀 Built With
- **Meta Muse Voice Transcribe** (ASR)
- **Meta Muse Spark** (Reasoning & JSON Extraction)
- **FastAPI** (Backend)
- **HTML/CSS/JS** (Frontend)

## 🛠️ Prerequisites
1. Python 3.10+
2. **FFmpeg**: Required for audio conversion. 
   - *Windows*: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to PATH.
   - *Mac*: `brew install ffmpeg`
   - *Linux*: `sudo apt install ffmpeg`

## ⚙️ Setup & Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/voxledger.git
   cd voxledger
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Mac/Linux:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables. Create a `.env` file in the root directory:
   ```env
   MODEL_API_KEY=your_meta_api_key_here
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Open your browser and go to `http://127.0.0.1:8000`
