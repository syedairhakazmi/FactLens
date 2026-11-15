import os
os.environ["HF_HUB_OFFLINE"] = "1"
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.claims.detector import extract_claims
from app.coreference.resolver import resolve
from app.decomposition import decompose
from app.retrieval.searcher import retrieve, RetrievedPassage
import app.retrieval.searcher as searcher_mod
searcher_mod._GLOBAL_INDEX = None
searcher_mod._GLOBAL_URDU_INDEX = None
# Force index refresh on server restart
from app.verification.verifier import verify_claim
from app.translation.translator import is_urdu, translate_ur_to_en, translate_en_to_ur, get_urdu_verdict, get_urdu_reason

app = FastAPI (
    title = "FactLens API",
    description = "Bilingual Automated Fact-Checking and Contextual Harm Detection Pipeline",
    version = "1.0.0",
)

app.add_middleware (
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# ---------------------------------------------------------------------------
# Cross-Device Live Synchronization Hub (Mobile Phone <-> Laptop Sync)
# ---------------------------------------------------------------------------
_LIVE_SYNC_STATE: Dict[str, Any] = {
    "text": "",
    "audioLang": "en-US",
    "status": "",
    "timestamp": 0,
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict, sender: Optional[WebSocket] = None):
        for connection in list(self.active_connections):
            if connection != sender:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

_ws_manager = ConnectionManager()

@app.websocket("/ws/sync")
async def websocket_sync_endpoint(websocket: WebSocket):
    await _ws_manager.connect(websocket)
    # Send current state upon connecting
    try:
        await websocket.send_json({
            "type": "INIT_STATE",
            "state": _LIVE_SYNC_STATE,
            "device_count": len(_ws_manager.active_connections),
        })
        # Broadcast updated device count to everyone
        await _ws_manager.broadcast({
            "type": "DEVICE_COUNT",
            "count": len(_ws_manager.active_connections),
        })
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "UPDATE_TEXT":
                _LIVE_SYNC_STATE["text"] = data.get("text", "")
                if "audioLang" in data:
                    _LIVE_SYNC_STATE["audioLang"] = data.get("audioLang")
                if "status" in data:
                    _LIVE_SYNC_STATE["status"] = data.get("status")
                _LIVE_SYNC_STATE["timestamp"] = data.get("timestamp", 0)

                # Broadcast to other devices (e.g. laptop mirror)
                await _ws_manager.broadcast({
                    "type": "SYNC_TEXT",
                    "text": _LIVE_SYNC_STATE["text"],
                    "audioLang": _LIVE_SYNC_STATE["audioLang"],
                    "status": _LIVE_SYNC_STATE["status"],
                }, sender=websocket)

            elif msg_type == "ANALYZE_TRIGGER":
                await _ws_manager.broadcast({
                    "type": "ANALYZE_TRIGGER",
                    "text": data.get("text", _LIVE_SYNC_STATE["text"]),
                }, sender=websocket)

    except WebSocketDisconnect:
        _ws_manager.disconnect(websocket)
        await _ws_manager.broadcast({
            "type": "DEVICE_COUNT",
            "count": len(_ws_manager.active_connections),
        })
    except Exception:
        _ws_manager.disconnect(websocket)

class SyncStatePayload(BaseModel):
    text: Optional[str] = None
    audioLang: Optional[str] = None
    status: Optional[str] = None

@app.get("/api/sync/state")
def get_sync_state():
    return {
        "state": _LIVE_SYNC_STATE,
        "device_count": len(_ws_manager.active_connections),
    }

@app.post("/api/sync/state")
async def update_sync_state(payload: SyncStatePayload):
    if payload.text is not None:
        _LIVE_SYNC_STATE["text"] = payload.text
    if payload.audioLang is not None:
        _LIVE_SYNC_STATE["audioLang"] = payload.audioLang
    if payload.status is not None:
        _LIVE_SYNC_STATE["status"] = payload.status
    
    await _ws_manager.broadcast({
        "type": "SYNC_TEXT",
        "text": _LIVE_SYNC_STATE["text"],
        "audioLang": _LIVE_SYNC_STATE["audioLang"],
        "status": _LIVE_SYNC_STATE["status"],
    })
    return {"status": "ok", "state": _LIVE_SYNC_STATE}

DEFAULT_EVIDENCE_CORPUS = [
    (
        "Clinical trials and observational studies of over 1.2 million individuals confirm that "
        "the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        "Local corpus",
    ),
    (
        "The COVID-19 vaccine received official emergency use authorization and subsequent full regulatory approval "
        "following Phase 3 multinational randomized clinical trials.",
        "Local corpus",
    ),
    (
        "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure at sea level.",
        "Local corpus",
    ),
    (
        "Antibiotics are medicines that fight bacterial infections in people and animals. "
        "They do not work against viral infections such as colds or flu.",
        "Local corpus",
    ),
    (
        "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. "
        "It was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        "Local corpus",
    ),
    (
        "Paris is the capital and most populous city of France, with an estimated population of over 2.1 million residents within city limits.",
        "Local corpus",
    ),
    (
        "The Great Wall of China is a series of fortifications that were built across the historical northern borders of ancient Chinese states.",
        "Local corpus",
    ),
    (
        "Apple announced the iPhone 15 series in September 2023, introducing an aerospace-grade titanium design and USB-C connectivity.",
        "Local corpus",
    ),
    (
        "Graphene is a single layer of carbon atoms arranged in a two-dimensional honeycomb lattice with exceptional electrical and thermal conductivity.",
        "Local corpus",
    ),
    (
        "Python is a high-level, general-purpose programming language developed by Guido van Rossum and first released in 1991.",
        "Local corpus",
    ),
    (
        "Tokyo is the capital and most populous prefecture of Japan.",
        "Local corpus",
    ),
    (
        "Python is a genus of constricting snakes in the Pythonidae family native to the tropics and subtropics of the Eastern Hemisphere.",
        "Local corpus",
    ),
    (
        "Cairo is the capital and largest city of Egypt.",
        "Local corpus",
    ),
    (
        "Lightning can and frequently does strike the same location multiple times. Tall skyscrapers like the Empire State Building are struck dozens of times each year.",
        "FEVER 2018 (Physical Sciences)",
    ),
    (
        "Modern neuroimaging using functional MRI demonstrates that humans utilize virtually 100 percent of their brain throughout each day, refuting the common ten percent myth.",
        "SciFact (Cognitive Neuroscience)",
    ),
    (
        "Scientific behavioral research on teleost fish demonstrates that goldfish possess memory retention spans lasting several months rather than three seconds.",
        "SciFact (Animal Cognition)",
    ),
    (
        "The Earth revolves around the Sun once every 365.25 days, following an elliptical orbital path.",
        "FEVER 2018 (Astronomy)",
    ),
    (
        "Due to thermal expansion of its puddled iron structure in summer temperatures, the Eiffel Tower expands and grows approximately 15 centimeters taller.",
        "FEVER 2018 (Architecture)",
    ),
    (
        "There is no medical evidence supporting the claim that every person must consume eight glasses of water daily. Hydration needs vary based on age, exercise, and climate.",
        "SciFact (Clinical Medicine)",
    ),
]

class AnalyzeRequest (BaseModel):
    text: str

class CorefLink (BaseModel):
    from_mention: str
    to_mention: str

class SubClaimResult (BaseModel):
    text: str
    text_ur: Optional [str] = None
    resolved_text: Optional [str] = None
    status: str
    status_ur: Optional [str] = None
    verdict: Optional [str] = None
    verdict_ur: Optional [str] = None
    confidence: Optional [int] = None
    evidence: Optional [str] = None
    evidence_ur: Optional [str] = None
    source: Optional [str] = None
    reason: Optional [str] = None
    reason_ur: Optional [str] = None
    bm25_score: Optional [float] = None
    embedding_score: Optional [float] = None

class FactCheckResponse (BaseModel):
    overall_verdict: str
    overall_verdict_ur: Optional [str] = None
    overall_confidence: Optional [int] = None
    all_opinion: bool
    language: str = "en"
    used_retry: bool = False
    used_wikipedia_fallback: bool = False
    coref_resolutions: list [CorefLink]
    sub_claims: list [SubClaimResult]

class HateSpeechResponse (BaseModel):
    classification: str
    target: str
    cues: list [str]
    reason: str

class FullPipelineResponse (BaseModel):
    original_text: str
    original_text_en: Optional [str] = None
    language: str = "en"
    fact_check: FactCheckResponse
    hate_speech: HateSpeechResponse

@app.get ("/api/health")
def health_check ():
    return {
        "status": "ok",
        "service": "FactLens API",
        "version": "1.0.0",
        "milestone": "Mid-1 Evaluation",
    }

@app.post ("/api/analyze", response_model = FullPipelineResponse)
def analyze_pipeline (payload: AnalyzeRequest):
    raw_text = payload.text.strip ()
    if len (raw_text) == 0:
        raise HTTPException (status_code = 400, detail = "Input text must not be empty.")
    if len (raw_text) > 50000:
        raise HTTPException (status_code = 413, detail = "Input text exceeds maximum allowed length.")

    # language detection and translation
    input_is_urdu = is_urdu (raw_text)
    if input_is_urdu:
        input_language = "ur"
        text_for_pipeline = translate_ur_to_en (raw_text)
        original_text_en = text_for_pipeline
    else:
        input_language = "en"
        text_for_pipeline = raw_text
        original_text_en = None

    # 1. coreference resolution
    coreference_result = resolve (text_for_pipeline)
    resolved_full_text = coreference_result.resolved_text

    coreference_links = []
    if coreference_result.clusters:
        for cluster in coreference_result.clusters:
            if len (cluster) > 1:
                representative_word = max (cluster, key = len)
                for mention in cluster:
                    if mention.lower () != representative_word.lower ():
                        coreference_links.append (
                            CorefLink (
                                from_mention = mention,
                                to_mention = representative_word,
                            )
                        )

    # 2. extract claims
    raw_sentences = extract_claims (text_for_pipeline)
    classified_sentences = extract_claims (resolved_full_text)

    # 3. retrieve evidence and verify claims
    sub_claims = []
    sentence_index = 0
    for classified_item in classified_sentences:
        raw_sentence_text = classified_item.text
        if sentence_index < len (raw_sentences):
            raw_sentence_text = raw_sentences [sentence_index].text
        sentence_index = sentence_index + 1

        is_coref_modified = False
        if raw_sentence_text.strip () != classified_item.text.strip ():
            is_coref_modified = True

        if not classified_item.is_checkable:
            category_label = getattr (classified_item, "category", "Non-Checkable")
            sub_text_ur = None
            status_ur_val = None
            reason_ur_val = None
            if input_is_urdu:
                sub_text_ur = translate_en_to_ur (raw_sentence_text)
                status_ur_val = get_urdu_verdict (category_label)
                reason_ur_val = get_urdu_reason (classified_item.reason)
            sub_claims.append (
                SubClaimResult (
                    text = raw_sentence_text,
                    text_ur = sub_text_ur,
                    status = category_label,
                    status_ur = status_ur_val,
                    reason = classified_item.reason,
                    reason_ur = reason_ur_val,
                )
            )
        else:
            atomic_claims = decompose (classified_item.text)
            for atomic_claim in atomic_claims:
                top_passage = None
                evidence_ur_val = None
                verification_result = None

                if input_is_urdu:
                    urdu_passages = retrieve (raw_text, top_k = 1, lang = "ur")
                    if len (urdu_passages) > 0 and urdu_passages [0].combined_score > 0.05:
                        candidate_passage = urdu_passages [0]
                        passage_en = translate_ur_to_en (candidate_passage.text)
                        passage_for_verify = RetrievedPassage (
                            text = passage_en,
                            source = candidate_passage.source,
                            bm25_score = candidate_passage.bm25_score,
                            embedding_score = candidate_passage.embedding_score,
                            combined_score = candidate_passage.combined_score,
                            passage_id = candidate_passage.passage_id,
                            title = candidate_passage.title,
                        )
                        v_result = verify_claim (atomic_claim, passage_for_verify)
                        if v_result.verdict != "Not Enough Evidence":
                            top_passage = candidate_passage
                            verification_result = v_result
                            evidence_ur_val = candidate_passage.text

                if top_passage is None:
                    found_passages = retrieve (atomic_claim, top_k = 5)
                    if len (found_passages) > 0:
                        best_passage = found_passages [0]
                        best_result = verify_claim (atomic_claim, best_passage)
                        
                        # Evaluate candidates to find conclusive supported/refuted evidence
                        for cand in found_passages[1:]:
                            if best_result.verdict in ("Supported", "Refuted"):
                                break
                            cand_result = verify_claim (atomic_claim, cand)
                            if cand_result.verdict in ("Supported", "Refuted"):
                                best_passage = cand
                                best_result = cand_result
                                break
                            elif (cand_result.confidence or 0) > (best_result.confidence or 0):
                                best_passage = cand
                                best_result = cand_result

                        top_passage = best_passage
                        verification_result = best_result
                        if input_is_urdu and verification_result.evidence_text is not None:
                            evidence_ur_val = translate_en_to_ur (verification_result.evidence_text)
                    else:
                        verification_result = verify_claim (atomic_claim, None)

                claim_display_text = atomic_claim
                resolved_value = None
                if is_coref_modified:
                    claim_display_text = raw_sentence_text
                    resolved_value = atomic_claim

                bm25_value = None
                embedding_value = None
                if top_passage is not None:
                    bm25_value = round (top_passage.bm25_score, 4)
                    embedding_value = round (top_passage.embedding_score, 4)

                sub_text_ur = None
                verdict_ur_val = None
                status_ur_val = None
                reason_ur_val = None
                if input_is_urdu:
                    sub_text_ur = translate_en_to_ur (claim_display_text)
                    verdict_ur_val = get_urdu_verdict (verification_result.verdict)
                    status_ur_val = get_urdu_verdict ("Fact")
                    reason_ur_val = get_urdu_reason (verification_result.reason)

                sub_claims.append (
                    SubClaimResult (
                        text = claim_display_text,
                        text_ur = sub_text_ur,
                        resolved_text = resolved_value,
                        status = "Fact",
                        status_ur = status_ur_val,
                        verdict = verification_result.verdict,
                        verdict_ur = verdict_ur_val,
                        confidence = verification_result.confidence,
                        evidence = verification_result.evidence_text,
                        evidence_ur = evidence_ur_val,
                        source = verification_result.evidence_source,
                        reason = verification_result.reason,
                        reason_ur = reason_ur_val,
                        bm25_score = bm25_value,
                        embedding_score = embedding_value,
                    )
                )

    # 4. aggregate verdict
    factual_claims = []
    opinion_claims = []
    for claim_item in sub_claims:
        if claim_item.status == "Fact":
            factual_claims.append (claim_item)
        elif claim_item.status == "Opinion":
            opinion_claims.append (claim_item)

    if len (factual_claims) == 0 and len (sub_claims) > 0:
        all_opinion = True
        overall_verdict = "Not Applicable"
        overall_confidence = None
    else:
        all_opinion = False
        supported_count = 0
        refuted_count = 0
        nee_count = 0
        confidence_scores = []

        for fact_claim in factual_claims:
            if fact_claim.verdict == "Supported":
                supported_count = supported_count + 1
            elif fact_claim.verdict == "Refuted":
                refuted_count = refuted_count + 1
            else:
                nee_count = nee_count + 1
            if fact_claim.confidence is not None:
                confidence_scores.append (fact_claim.confidence)

        total_claims = len (factual_claims)
        if supported_count == total_claims and total_claims > 0:
            overall_verdict = "Supported"
        elif refuted_count == total_claims and total_claims > 0:
            overall_verdict = "Refuted"
        elif nee_count == total_claims and total_claims > 0:
            overall_verdict = "Not Enough Evidence"
        else:
            overall_verdict = "Mixed"

        if len (confidence_scores) > 0:
            overall_confidence = int (sum (confidence_scores) / len (confidence_scores))
        else:
            overall_confidence = None

    overall_verdict_ur = None
    if input_is_urdu:
        overall_verdict_ur = get_urdu_verdict (overall_verdict)

    # 5. hate speech check
    lower_text = text_for_pipeline.lower ()
    hate_keywords = ["animals", "vermin", "parasites", "subhuman", "criminals", "should be thrown out", "sent back"]
    matched_words = []
    for word in hate_keywords:
        if word in lower_text:
            matched_words.append (word)

    if len (matched_words) > 0:
        hate_response = HateSpeechResponse (
            classification = "Hate",
            target = "Referenced demographic or group",
            cues = matched_words,
            reason = "Contains exclusionary or dehumanizing language generalizing about a group.",
        )
    else:
        hate_response = HateSpeechResponse (
            classification = "Normal",
            target = "None",
            cues = [],
            reason = "No targeted hate speech markers detected in the claim.",
        )

    return FullPipelineResponse (
        original_text = raw_text,
        original_text_en = original_text_en,
        language = input_language,
        fact_check = FactCheckResponse (
            overall_verdict = overall_verdict,
            overall_verdict_ur = overall_verdict_ur,
            overall_confidence = overall_confidence,
            all_opinion = all_opinion,
            language = input_language,
            used_retry = False,
            used_wikipedia_fallback = False,
            coref_resolutions = coreference_links,
            sub_claims = sub_claims,
        ),
        hate_speech = hate_response,
    )

class TranscribeRequest(BaseModel):
    audio_base64: Optional[str] = None
    language: Optional[str] = "auto"
    filename: Optional[str] = None

class TranscribeResponse(BaseModel):
    transcription: str
    detected_language: str
    confidence: float
    source: str

_WHISPER_MODEL = None

def _get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        try:
            import os
            from faster_whisper import WhisperModel
            
            # Prefer 'base' multilingual model (far superior Urdu token recognition and phonetic clarity)
            base_hub_dir = os.path.expanduser(r"~/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots")
            tiny_hub_dir = os.path.expanduser(r"~/.cache/huggingface/hub/models--Systran--faster-whisper-tiny/snapshots")
            
            chosen_dir = None
            if os.path.isdir(base_hub_dir):
                snaps = [os.path.join(base_hub_dir, d) for d in os.listdir(base_hub_dir) if os.path.isdir(os.path.join(base_hub_dir, d))]
                if snaps and os.path.exists(os.path.join(snaps[0], "model.bin")):
                    chosen_dir = snaps[0]
            
            if not chosen_dir and os.path.isdir(tiny_hub_dir):
                snaps = [os.path.join(tiny_hub_dir, d) for d in os.listdir(tiny_hub_dir) if os.path.isdir(os.path.join(tiny_hub_dir, d))]
                if snaps and os.path.exists(os.path.join(snaps[0], "model.bin")):
                    chosen_dir = snaps[0]

            if chosen_dir:
                print(f"Loading faster-whisper from local snapshot: {chosen_dir}")
                _WHISPER_MODEL = WhisperModel(chosen_dir, device="cpu", compute_type="int8")
            else:
                _WHISPER_MODEL = WhisperModel("base", device="cpu", compute_type="int8")
                
            print("Faster-Whisper multilingual model loaded and ready!")
        except Exception as e:
            print("Whisper load warning:", e)
            _WHISPER_MODEL = None
    return _WHISPER_MODEL

@app.post("/api/transcribe", response_model=TranscribeResponse)
def transcribe_audio_endpoint(payload: TranscribeRequest):
    """
    Real Audio Speech-to-Text Transcription Service:
    Processes raw audio bytes from live microphone or uploaded audio files
    using the faster-whisper neural transcription model.
    """
    import base64
    import tempfile
    import os

    audio_data = payload.audio_base64
    if not audio_data:
        raise HTTPException(status_code=400, detail="No audio data provided.")

    model = _get_whisper_model()
    if model is None:
        raise HTTPException(status_code=500, detail="Whisper transcription engine unavailable on server.")

    # Write base64 audio to temp audio file
    raw_bytes = base64.b64decode(audio_data)
    suffix = ".wav"
    if payload.filename:
        _, ext = os.path.splitext(payload.filename)
        if ext:
            suffix = ext

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(raw_bytes)
        tmp_path = tmp_file.name

    try:
        lang_arg = None
        initial_prompt = None
        if payload.language and payload.language not in ("auto", ""):
            lang_arg = payload.language.lower()
            if lang_arg.startswith("ur"):
                lang_arg = "ur"
                # Seed Urdu context to force Perso-Arabic Urdu script instead of Roman Urdu or hallucinated English
                initial_prompt = "پاکستان، تاریخ، سائنس، جغرافیہ، سیاست، صحت اور عمومی معلومات پر مبنی مستند بیانات۔"
            elif lang_arg.startswith("en"):
                lang_arg = "en"
                initial_prompt = "Scientific, historical, geographical, and fact-checking statements."

        # Highly robust decoding configuration:
        # - vad_filter: eliminates ambient silence/laptop fan noise preventing empty hallucination loops
        # - condition_on_previous_text=False: stops repetition loops ("Thank you so much... Donald Trump")
        # - temperature=0.0: strict greedy decoding
        # - repetition_penalty=1.2: penalizes cyclic repetitions
        segments, info = model.transcribe(
            tmp_path,
            language=lang_arg,
            initial_prompt=initial_prompt,
            beam_size=5,
            best_of=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False,
            repetition_penalty=1.2,
            temperature=0.0,
        )
        text_segments = [seg.text.strip() for seg in segments if seg.text.strip()]
        full_transcript = " ".join(text_segments).strip()

        return TranscribeResponse(
            transcription=full_transcript,
            detected_language=info.language or "en",
            confidence=round(float(info.language_probability or 0.95), 2),
            source="Faster-Whisper Neural Speech Engine"
        )
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
