import os
import torch
import torchaudio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

# Try to import pyannote.audio with error handling
try:
    from pyannote.audio import Pipeline
    from pyannote.core import Segment as PyannoteSegment
    DIARIZATION_AVAILABLE = True
except ImportError:
    DIARIZATION_AVAILABLE = False
    logger.warning("pyannote.audio not available. Speaker diarization will be disabled.")

# Default speaker colors (can be customized)
DEFAULT_SPEAKER_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
]

@dataclass
class DiarizationResult:
    """Container for diarization results"""
    segments: List[Dict[str, Any]]
    speakers: List[Dict[str, str]]
    audio_duration: float

class SpeakerDiarizer:
    """Handles speaker diarization using pyannote.audio"""
    
    def __init__(self, auth_token: Optional[str] = None):
        """Initialize the diarizer with an optional auth token for Hugging Face Hub"""
        self.pipeline = None
        self.auth_token = auth_token or os.getenv('HUGGINGFACE_TOKEN')
        self._load_model()
    
    def _load_model(self):
        """Load the diarization model"""
        if not DIARIZATION_AVAILABLE:
            logger.error("pyannote.audio is not available. Cannot load diarization model.")
            return
            
        try:
            if not self.auth_token:
                logger.warning("No Hugging Face auth token provided. Some features may be limited.")
            
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.auth_token
            )
            logger.info("Successfully loaded speaker diarization model")
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            self.pipeline = None
    
    def is_available(self) -> bool:
        """Check if diarization is available"""
        return self.pipeline is not None and DIARIZATION_AVAILABLE
    
    def process_audio_file(
        self, 
        audio_path: str, 
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> Optional[DiarizationResult]:
        """
        Process an audio file to identify speakers
        
        Args:
            audio_path: Path to the audio file
            min_speakers: Minimum number of speakers (optional)
            max_speakers: Maximum number of speakers (optional)
            
        Returns:
            DiarizationResult with segments and speaker info, or None if processing failed
        """
        if not self.is_available():
            logger.error("Diarization is not available")
            return None
        
        try:
            # Load audio file
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Convert to mono if needed
            if len(waveform.shape) > 1 and waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 16kHz if needed (required by pyannote)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
                waveform = resampler(waveform)
                sample_rate = 16000
            
            # Prepare input for pyannote
            audio_input = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
            
            # Run diarization
            diarization = self.pipeline(audio_input, min_speakers=min_speakers, max_speakers=max_speakers)
            
            # Process results
            segments = []
            speaker_ids = set()
            
            # Get audio duration
            audio_duration = waveform.shape[1] / sample_rate
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_id = str(speaker)
                speaker_ids.add(speaker_id)
                
                segments.append({
                    "start": round(turn.start, 2),
                    "end": round(turn.end, 2),
                    "speaker": speaker_id,
                    "text": ""  # Will be filled in by the transcription
                })
            
            # Sort segments by start time
            segments.sort(key=lambda x: x["start"])
            
            # Create speaker info with colors
            speaker_ids = sorted(list(speaker_ids))
            speakers = []
            
            for i, speaker_id in enumerate(speaker_ids):
                speakers.append({
                    "id": speaker_id,
                    "name": f"Speaker {i+1}",
                    "color": DEFAULT_SPEAKER_COLORS[i % len(DEFAULT_SPEAKER_COLORS)]
                })
            
            return DiarizationResult(
                segments=segments,
                speakers=speakers,
                audio_duration=audio_duration
            )
            
        except Exception as e:
            logger.error(f"Error during diarization: {e}", exc_info=True)
            return None

def merge_transcription_with_diarization(
    transcription_segments: List[Dict[str, Any]],
    diarization_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge transcription segments with speaker diarization results
    
    Args:
        transcription_segments: List of segments from the transcription
        diarization_segments: List of segments from diarization
        
    Returns:
        List of segments with both text and speaker information
    """
    if not diarization_segments:
        return transcription_segments
    
    result = []
    diarization_idx = 0
    
    for seg in transcription_segments:
        seg_start = seg.get('start', 0)
        seg_end = seg.get('end', float('inf'))
        
        # Find overlapping diarization segments
        overlapping_speakers = {}
        
        # Find all diarization segments that overlap with this transcription segment
        for diar_seg in diarization_segments:
            diar_start = diar_seg['start']
            diar_end = diar_seg['end']
            
            # Check for overlap
            if diar_start < seg_end and diar_end > seg_start:
                # Calculate overlap duration
                overlap_start = max(seg_start, diar_start)
                overlap_end = min(seg_end, diar_end)
                overlap_duration = max(0, overlap_end - overlap_start)
                
                # Track speaker and their total overlap time
                speaker = diar_seg['speaker']
                if speaker in overlapping_speakers:
                    overlapping_speakers[speaker] += overlap_duration
                else:
                    overlapping_speakers[speaker] = overlap_duration
        
        # Find the speaker with the most overlap
        speaker = None
        if overlapping_speakers:
            speaker = max(overlapping_speakers.items(), key=lambda x: x[1])[0]
        
        # Create a new segment with speaker info
        new_seg = seg.copy()
        if speaker:
            new_seg['speaker'] = speaker
        
        result.append(new_seg)
    
    return result
