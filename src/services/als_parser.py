"""Parser for Ableton Live .als project files.

.als files are gzipped XML files containing project data including:
- Plugins (VST/AU)
- Devices (Ableton built-in devices)
- Tracks (audio/MIDI/return/master)
- Tempo, time signature
- Arrangement length
- Sample references
- Device chains and parameters (for ML feature extraction)
- Clip details (count, types, durations)
"""

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from ..utils.logging import get_logger

# Try to use lxml for better XPath support and performance
try:
    from lxml import etree as lxml_ET
    USE_LXML = True
except ImportError:
    USE_LXML = False


@dataclass
class DeviceChainInfo:
    """Information about a device chain."""
    track_name: str = ""
    track_type: str = ""  # "audio", "midi", "return", "master"
    devices: List[str] = field(default_factory=list)
    device_count: int = 0
    has_plugins: bool = False
    plugin_count: int = 0


@dataclass
class ClipInfo:
    """Information about a clip."""
    name: str = ""
    clip_type: str = ""  # "audio" or "midi"
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    is_looping: bool = False
    color_index: int = -1


@dataclass
class ExtendedMetadata:
    """Extended metadata for ML feature extraction."""
    # Device chain analysis
    device_chains: List[DeviceChainInfo] = field(default_factory=list)
    total_device_count: int = 0
    unique_device_types: int = 0
    avg_devices_per_track: float = 0.0
    
    # Clip analysis
    clips: List[ClipInfo] = field(default_factory=list)
    audio_clip_count: int = 0
    midi_clip_count: int = 0
    total_clip_count: int = 0
    avg_clip_duration: float = 0.0
    
    # Routing information
    has_sends: bool = False
    send_count: int = 0
    has_sidechain: bool = False
    
    # Automation density
    automation_lane_count: int = 0
    automation_point_count: int = 0
    
    # Groove/swing settings
    groove_pool_size: int = 0
    
    # Scene information
    scene_count: int = 0
    
    # Key/scale information (if present in project)
    musical_key: Optional[str] = None
    scale_type: Optional[str] = None
    
    # Plugin parameter counts (for complexity analysis)
    plugin_parameter_count: int = 0


@dataclass
class ProjectMetadata:
    """Extracted metadata from an Ableton project."""
    plugins: List[str] = field(default_factory=list)  # Plugin names/paths
    devices: List[str] = field(default_factory=list)  # Ableton device names
    tempo: Optional[float] = None
    time_signature: Optional[str] = None
    track_count: int = 0
    audio_tracks: int = 0
    midi_tracks: int = 0
    return_tracks: int = 0
    master_track: bool = False
    arrangement_length: Optional[float] = None  # In bars
    ableton_version: Optional[str] = None
    sample_references: List[str] = field(default_factory=list)  # Sample file paths
    has_automation: bool = False
    # Export-related metadata
    export_filenames: List[str] = field(default_factory=list)  # Export filenames found in project
    annotation: Optional[str] = None  # Project annotation/notes
    master_track_name: Optional[str] = None  # Master track name (sometimes used as song name)
    
    # Musical key/scale information
    musical_key: Optional[str] = None  # Root note (e.g., "C", "D#", "A")
    scale_type: Optional[str] = None  # Scale type (e.g., "Major", "Minor", "Dorian")
    is_in_key: Optional[bool] = None  # Whether "In Key" mode is enabled globally
    
    # Extended metadata for ML features (Phase 5)
    extended: Optional[ExtendedMetadata] = None
    
    # Feature vector cache for ML (populated by feature extractor)
    _feature_vector: Optional[List[float]] = field(default=None, repr=False)


class ALSParser:
    """Parser for Ableton Live .als project files.
    
    Supports standard xml.etree.ElementTree parsing with optional lxml
    enhancement for better XPath support and performance.
    """
    
    def __init__(self, extract_extended: bool = False, use_lxml: bool = None):
        """Initialize the parser.
        
        Args:
            extract_extended: If True, extract extended metadata for ML features.
            use_lxml: Force lxml usage (True), disable it (False), or auto-detect (None).
        """
        self.logger = get_logger(__name__)
        self._cache: Dict[str, ProjectMetadata] = {}
        self._extract_extended = extract_extended
        self._use_lxml = use_lxml if use_lxml is not None else USE_LXML
    
    def parse(self, als_path: Path) -> Optional[ProjectMetadata]:
        """Parse an .als file and extract metadata.
        
        Args:
            als_path: Path to the .als file.
            
        Returns:
            ProjectMetadata object with extracted data, or None if parsing fails.
        """
        if not als_path.exists():
            return None
        
        # Check cache (keyed by path and modification time)
        cache_key = f"{als_path}_{als_path.stat().st_mtime}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Decompress and parse XML
            with gzip.open(als_path, 'rb') as f:
                xml_data = f.read()
            
            root = ET.fromstring(xml_data)
            
            metadata = ProjectMetadata()
            
            # Extract Ableton version
            metadata.ableton_version = self._extract_version(root)
            
            # Extract tempo and time signature
            metadata.tempo = self._extract_tempo(root)
            metadata.time_signature = self._extract_time_signature(root)
            
            # Extract tracks
            tracks_info = self._extract_tracks(root)
            metadata.track_count = tracks_info['total']
            metadata.audio_tracks = tracks_info['audio']
            metadata.midi_tracks = tracks_info['midi']
            metadata.return_tracks = tracks_info['return']
            metadata.master_track = tracks_info['master']
            
            # Extract arrangement length
            metadata.arrangement_length = self._extract_arrangement_length(root)
            
            # Extract plugins and devices
            plugins, devices = self._extract_plugins_and_devices(root)
            metadata.plugins = plugins
            metadata.devices = devices
            
            # Extract sample references
            metadata.sample_references = self._extract_samples(root)
            
            # Check for automation
            metadata.has_automation = self._has_automation(root)
            
            # Extract export-related info
            export_info = self._extract_export_info(root)
            metadata.export_filenames = export_info.get('filenames', [])
            metadata.annotation = export_info.get('annotation')
            metadata.master_track_name = export_info.get('master_track_name')
            
            # Extract extended metadata for ML features (if enabled)
            if self._extract_extended:
                metadata.extended = self._extract_extended_metadata(root)
            
            # Extract musical key/scale information
            key_info = self._extract_key_info(root)
            metadata.musical_key = key_info.get('key')
            metadata.scale_type = key_info.get('scale')
            metadata.is_in_key = key_info.get('is_in_key')
            
            # Cache result
            self._cache[cache_key] = metadata
            
            return metadata
            
        except Exception as e:
            # Log error but don't crash
            self.logger.error(f"Error parsing {als_path}: {e}", exc_info=True)
            return None
    
    def _extract_version(self, root: ET.Element) -> Optional[str]:
        """Extract Ableton Live version from project."""
        # The Creator attribute is on the root "Ableton" element
        creator = root.get('Creator')
        if creator:
            # Creator format: "Ableton Live 12.3" or "Ableton Live 11.3.10"
            return creator
        
        # Fallback: look for AbletonLiveProject element (older format)
        for elem in root.iter():
            if 'AbletonLiveProject' in elem.tag:
                creator = elem.get('Creator')
                if creator:
                    return creator
        return None
    
    def _extract_tempo(self, root: ET.Element) -> Optional[float]:
        """Extract tempo from project."""
        # Tempo is usually in LiveSet -> MasterTrack -> Tempo
        for tempo_elem in root.iter():
            if 'Tempo' in tempo_elem.tag:
                manual = tempo_elem.find('Manual')
                if manual is not None:
                    value = manual.get('Value')
                    if value:
                        try:
                            return float(value)
                        except ValueError:
                            pass
        return None
    
    def _extract_time_signature(self, root: ET.Element) -> Optional[str]:
        """Extract time signature from project."""
        # Time signature is usually in LiveSet -> MasterTrack -> TimeSignature
        for ts_elem in root.iter():
            if 'TimeSignature' in ts_elem.tag:
                numerator = ts_elem.get('Numerator')
                denominator = ts_elem.get('Denominator')
                if numerator and denominator:
                    return f"{numerator}/{denominator}"
        return None
    
    def _extract_tracks(self, root: ET.Element) -> Dict[str, int]:
        """Extract track information.
        
        Only counts top-level Audio and MIDI tracks.
        Excludes: return tracks, master track, and nested tracks
        (e.g., drum rack pads, group track chains).
        """
        counts = {
            'total': 0,
            'audio': 0,
            'midi': 0,
            'return': 0,
            'master': 0
        }
        
        # Find the main Tracks element (direct child of LiveSet)
        # This is the only place top-level tracks are defined
        liveset = root.find('.//LiveSet')
        if liveset is None:
            # Root might be LiveSet itself
            liveset = root if root.tag == 'LiveSet' else None
        
        if liveset is not None:
            # Find the direct Tracks child (not nested track containers)
            tracks_elem = liveset.find('Tracks')
            if tracks_elem is not None:
                for track in tracks_elem:
                    tag = track.tag
                    
                    # Only count AudioTrack and MidiTrack for the main total
                    if tag == 'AudioTrack':
                        counts['audio'] += 1
                        counts['total'] += 1
                    elif tag == 'MidiTrack':
                        counts['midi'] += 1
                        counts['total'] += 1
                    elif tag == 'ReturnTrack':
                        # Count but don't include in total
                        counts['return'] += 1
                    elif tag == 'MasterTrack':
                        # Count but don't include in total
                        counts['master'] += 1
                    # GroupTrack is counted as a track
                    elif tag == 'GroupTrack':
                        counts['midi'] += 1  # Group tracks are MIDI-like
                        counts['total'] += 1
        
        return counts
    
    def _extract_arrangement_length(self, root: ET.Element) -> Optional[float]:
        """Extract arrangement length in bars by finding the furthest clip end."""
        max_end = 0.0
        
        # Look for MidiClip and AudioClip elements
        for clip_elem in root.iter():
            if clip_elem.tag in ('MidiClip', 'AudioClip'):
                # Find CurrentEnd within the clip
                for sub in clip_elem:
                    if sub.tag == 'CurrentEnd':
                        try:
                            end_val = float(sub.get('Value', 0))
                            if end_val > max_end:
                                max_end = end_val
                        except (ValueError, TypeError):
                            pass
                        break
        
        # Also check for arrangement markers (Locators)
        for locator in root.iter('Locator'):
            for time_elem in locator.iter('Time'):
                try:
                    time_val = float(time_elem.get('Value', 0))
                    if time_val > max_end:
                        max_end = time_val
                except (ValueError, TypeError):
                    pass
        
        # Return length in bars (beats / 4 for 4/4 time)
        # Ableton stores time in beats, not bars
        if max_end > 0:
            return max_end / 4.0
        
        return None
    
    def _extract_plugins_and_devices(self, root: ET.Element) -> tuple[List[str], List[str]]:
        """Extract plugin and device information."""
        plugins = []
        devices = []
        seen_plugins = set()
        seen_devices = set()
        
        # Look for PluginDevice elements (VST/AU plugins)
        for plugin_elem in root.iter():
            if 'PluginDevice' in plugin_elem.tag:
                # Try to get plugin name
                plugin_name = None
                
                # Check for VSTPluginInfo
                vst_info = plugin_elem.find('.//VstPluginInfo')
                if vst_info is not None:
                    plugin_name = vst_info.get('PlugName') or vst_info.get('Name')
                    if plugin_name and plugin_name not in seen_plugins:
                        plugins.append(plugin_name)
                        seen_plugins.add(plugin_name)
                
                # Check for AUPluginInfo (Mac)
                au_info = plugin_elem.find('.//AuPluginInfo')
                if au_info is not None:
                    plugin_name = au_info.get('Name') or au_info.get('PlugName')
                    if plugin_name and plugin_name not in seen_plugins:
                        plugins.append(plugin_name)
                        seen_plugins.add(plugin_name)
        
        # Look for Ableton devices
        device_types = [
            'AudioEffectGroupDevice',
            'MidiEffectGroupDevice',
            'InstrumentGroupDevice',
            'DrumGroupDevice',
            'AudioEffectDevice',
            'MidiEffectDevice',
            'InstrumentDevice',
            'Operator',
            'Simpler',
            'Sampler',
            'Impulse',
            'DrumRack',
            'Compressor',
            'Gate',
            'EQ8',
            'EQThree',
            'AutoFilter',
            'AutoPan',
            'Chorus',
            'Flanger',
            'Phaser',
            'Reverb',
            'Delay',
            'BeatRepeat',
            'Looper',
            'Utility',
            'Limiter',
            'MultibandCompressor',
            'GlueCompressor',
            'Saturator',
            'Erosion',
            'Redux',
            'Overdrive',
            'Cabinet',
            'Amp',
            'DynamicTube',
            'FrequencyShifter',
            'GrainDelay',
            'PingPongDelay',
            'SimpleDelay',
            'Spectrum',
            'Tuner',
            'Vocoder',
            'Arpeggiator',
            'Chord',
            'NoteLength',
            'Pitch',
            'Random',
            'Scale',
            'Velocity',
            'MidiArpeggiator',
            'MidiChord',
            'MidiNoteLength',
            'MidiPitcher',
            'MidiRandom',
            'MidiScale',
            'MidiVelocity',
            'Analog',
            'Collision',
            'Electric',
            'Tension',
            'Wavetable',
            'MidiArp',
            'MidiChord',
            'MidiNoteLength',
            'MidiPitcher',
            'MidiRandom',
            'MidiScale',
            'MidiVelocity'
        ]
        
        for device_type in device_types:
            for device_elem in root.iter():
                if device_type in device_elem.tag:
                    device_name = device_type
                    # Try to get a more specific name
                    name_elem = device_elem.find('.//UserName')
                    if name_elem is not None and name_elem.text:
                        device_name = name_elem.text
                    elif device_elem.get('Name'):
                        device_name = device_elem.get('Name')
                    
                    if device_name and device_name not in seen_devices:
                        devices.append(device_name)
                        seen_devices.add(device_name)
        
        return plugins, devices
    
    def _extract_samples(self, root: ET.Element) -> List[str]:
        """Extract sample file references."""
        samples = []
        seen = set()
        
        # Look for sample references in various places
        for sample_elem in root.iter():
            # AudioClip references
            if 'AudioClip' in sample_elem.tag:
                source = sample_elem.find('.//Source')
                if source is not None:
                    # Check for relative and absolute paths
                    for path_elem in source.iter():
                        if 'RelativePathElement' in path_elem.tag:
                            dir_name = path_elem.get('Dir')
                            if dir_name:
                                samples.append(dir_name)
                        elif 'Path' in path_elem.tag and path_elem.text:
                            path = path_elem.text
                            if path and path not in seen:
                                samples.append(path)
                                seen.add(path)
            
            # SampleRef elements
            if 'SampleRef' in sample_elem.tag:
                file_path = sample_elem.get('Path') or sample_elem.get('File')
                if file_path and file_path not in seen:
                    samples.append(file_path)
                    seen.add(file_path)
        
        return samples
    
    def _has_automation(self, root: ET.Element) -> bool:
        """Check if project has automation."""
        # Look for automation envelopes
        for automation_elem in root.iter():
            if 'AutomationEnvelope' in automation_elem.tag:
                return True
            if 'Envelope' in automation_elem.tag:
                return True
        return False
    
    def _extract_export_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract export-related information from project.
        
        Looks for:
        - ExportLog entries with previous export filenames
        - Annotation/Notes fields
        - Master track name (sometimes used as song title)
        - Audio rendering settings with default filename
        """
        result: Dict[str, Any] = {
            'filenames': [],
            'annotation': None,
            'master_track_name': None
        }
        
        seen_filenames = set()
        
        # Look for export log entries
        for elem in root.iter():
            # ExportLog or ExportHistory elements
            if 'Export' in elem.tag:
                # Look for filename attributes
                for attr in ['FileName', 'Name', 'Path', 'File']:
                    val = elem.get(attr)
                    if val and val not in seen_filenames:
                        # Extract just the filename without path/extension
                        name = Path(val).stem if '/' in val or '\\' in val else val
                        if name and name not in seen_filenames:
                            result['filenames'].append(name)
                            seen_filenames.add(name)
                
                # Check child elements for filenames
                for child in elem:
                    if 'FileName' in child.tag or 'Name' in child.tag:
                        val = child.get('Value') or child.text
                        if val and val not in seen_filenames:
                            name = Path(val).stem if '/' in val or '\\' in val else val
                            if name:
                                result['filenames'].append(name)
                                seen_filenames.add(name)
        
        # Look for AudioRenderSettings (export dialog settings)
        for render_elem in root.iter():
            if 'AudioRenderSettings' in render_elem.tag or 'RenderSettings' in render_elem.tag:
                for child in render_elem:
                    if 'FileName' in child.tag or 'OutputFileName' in child.tag:
                        val = child.get('Value') or child.text
                        if val and val not in seen_filenames:
                            name = Path(val).stem if '/' in val or '\\' in val else val
                            if name:
                                result['filenames'].append(name)
                                seen_filenames.add(name)
        
        # Look for Annotation (project notes)
        for anno_elem in root.iter():
            if 'Annotation' in anno_elem.tag:
                val = anno_elem.get('Value') or anno_elem.text
                if val:
                    result['annotation'] = val
                    break
        
        # Look for Master track name (could be song title)
        for tracks_elem in root.iter():
            if 'MasterTrack' in tracks_elem.tag:
                for name_elem in tracks_elem.iter():
                    if 'Name' in name_elem.tag or 'UserName' in name_elem.tag:
                        # Look for EffectiveName or UserName value
                        val = name_elem.get('Value')
                        if val and val.strip() and val.lower() not in ('master', 'a-master'):
                            result['master_track_name'] = val
                            break
        
        # Also scan for track names that might indicate song title
        # (First track with a non-default name)
        for tracks_elem in root.iter():
            if 'Tracks' in tracks_elem.tag:
                for track in tracks_elem:
                    user_name = None
                    for name_elem in track.iter():
                        if 'UserName' in name_elem.tag:
                            user_name = name_elem.get('Value')
                            break
                    # Skip default names like "1-Audio", "1-MIDI", etc.
                    if user_name and not user_name.startswith(('1-', '2-', '3-', '4-', '5-')):
                        if user_name.lower() not in ('audio', 'midi', 'master'):
                            # This might be a meaningful track name
                            pass  # Could use this for additional hints
        
        return result
    
    def clear_cache(self):
        """Clear the parser cache."""
        self._cache.clear()
    
    # =========================================================================
    # Extended Metadata Extraction Methods (Phase 5 - ML Features)
    # =========================================================================
    
    def _extract_extended_metadata(self, root: ET.Element) -> ExtendedMetadata:
        """Extract extended metadata for ML feature extraction.
        
        Args:
            root: Root XML element of the ALS file.
            
        Returns:
            ExtendedMetadata object with deep analysis data.
        """
        extended = ExtendedMetadata()
        
        # Extract device chains
        extended.device_chains = self._extract_device_chains(root)
        extended.total_device_count = sum(dc.device_count for dc in extended.device_chains)
        all_devices = []
        for dc in extended.device_chains:
            all_devices.extend(dc.devices)
        extended.unique_device_types = len(set(all_devices))
        
        if extended.device_chains:
            extended.avg_devices_per_track = (
                extended.total_device_count / len(extended.device_chains)
            )
        
        # Extract clip information
        extended.clips = self._extract_clips(root)
        extended.audio_clip_count = sum(1 for c in extended.clips if c.clip_type == "audio")
        extended.midi_clip_count = sum(1 for c in extended.clips if c.clip_type == "midi")
        extended.total_clip_count = len(extended.clips)
        
        if extended.clips:
            total_duration = sum(c.duration for c in extended.clips if c.duration > 0)
            extended.avg_clip_duration = total_duration / len(extended.clips)
        
        # Extract routing information
        routing_info = self._extract_routing_info(root)
        extended.has_sends = routing_info['has_sends']
        extended.send_count = routing_info['send_count']
        extended.has_sidechain = routing_info['has_sidechain']
        
        # Extract automation density
        automation_info = self._extract_automation_info(root)
        extended.automation_lane_count = automation_info['lane_count']
        extended.automation_point_count = automation_info['point_count']
        
        # Extract groove pool info
        extended.groove_pool_size = self._extract_groove_pool_size(root)
        
        # Extract scene count
        extended.scene_count = self._extract_scene_count(root)
        
        # Extract key/scale if present (uses same priority logic as main metadata)
        key_info = self._extract_key_info(root)
        extended.musical_key = key_info.get('key')
        extended.scale_type = key_info.get('scale')
        
        # Count plugin parameters (complexity indicator)
        extended.plugin_parameter_count = self._count_plugin_parameters(root)
        
        return extended
    
    def _extract_device_chains(self, root: ET.Element) -> List[DeviceChainInfo]:
        """Extract device chain information from all tracks."""
        chains = []
        
        # Track types and their container names
        track_types = [
            ('AudioTrack', 'audio'),
            ('MidiTrack', 'midi'),
            ('ReturnTrack', 'return'),
            ('MasterTrack', 'master')
        ]
        
        for track_tag, track_type in track_types:
            for track_elem in root.iter():
                if track_tag in track_elem.tag:
                    chain_info = DeviceChainInfo(track_type=track_type)
                    
                    # Extract track name
                    for name_elem in track_elem.iter():
                        if 'UserName' in name_elem.tag or 'EffectiveName' in name_elem.tag:
                            val = name_elem.get('Value')
                            if val:
                                chain_info.track_name = val
                                break
                    
                    # Extract devices in the chain
                    devices = []
                    plugin_count = 0
                    
                    for device_chain in track_elem.iter():
                        if 'DeviceChain' in device_chain.tag:
                            for device in device_chain:
                                device_name = self._get_device_name(device)
                                if device_name:
                                    devices.append(device_name)
                                    if 'Plugin' in device.tag:
                                        plugin_count += 1
                    
                    chain_info.devices = devices
                    chain_info.device_count = len(devices)
                    chain_info.plugin_count = plugin_count
                    chain_info.has_plugins = plugin_count > 0
                    
                    if devices:  # Only add if track has devices
                        chains.append(chain_info)
        
        return chains
    
    def _get_device_name(self, device_elem: ET.Element) -> Optional[str]:
        """Extract device name from a device element."""
        # Try to get user name first
        for name_elem in device_elem.iter():
            if 'UserName' in name_elem.tag:
                val = name_elem.get('Value')
                if val:
                    return val
        
        # Fall back to device type
        tag = device_elem.tag
        if tag:
            # Clean up tag name (remove namespace if present)
            if '}' in tag:
                tag = tag.split('}')[1]
            return tag
        
        return None
    
    def _extract_clips(self, root: ET.Element) -> List[ClipInfo]:
        """Extract clip information from the project."""
        clips = []
        
        # Look for both Audio and MIDI clips
        for clip_tag, clip_type in [('AudioClip', 'audio'), ('MidiClip', 'midi')]:
            for clip_elem in root.iter():
                if clip_elem.tag == clip_tag:
                    clip_info = ClipInfo(clip_type=clip_type)
                    
                    # Extract clip name
                    for name_elem in clip_elem.iter():
                        if 'Name' in name_elem.tag:
                            val = name_elem.get('Value')
                            if val:
                                clip_info.name = val
                                break
                    
                    # Extract timing information
                    for child in clip_elem:
                        if child.tag == 'CurrentStart':
                            try:
                                clip_info.start_time = float(child.get('Value', 0))
                            except (ValueError, TypeError):
                                pass
                        elif child.tag == 'CurrentEnd':
                            try:
                                clip_info.end_time = float(child.get('Value', 0))
                            except (ValueError, TypeError):
                                pass
                        elif child.tag == 'Loop':
                            for loop_child in child:
                                if 'LoopOn' in loop_child.tag:
                                    clip_info.is_looping = loop_child.get('Value') == 'true'
                        elif child.tag == 'ColorIndex':
                            try:
                                clip_info.color_index = int(child.get('Value', -1))
                            except (ValueError, TypeError):
                                pass
                    
                    clip_info.duration = clip_info.end_time - clip_info.start_time
                    clips.append(clip_info)
        
        return clips
    
    def _extract_routing_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract routing information (sends, sidechains)."""
        info = {
            'has_sends': False,
            'send_count': 0,
            'has_sidechain': False
        }
        
        # Check for send tracks
        return_track_count = 0
        for elem in root.iter():
            if 'ReturnTrack' in elem.tag:
                return_track_count += 1
        
        info['has_sends'] = return_track_count > 0
        info['send_count'] = return_track_count
        
        # Check for sidechain routing
        for elem in root.iter():
            if 'Sidechain' in elem.tag or 'SidechainOn' in elem.tag:
                val = elem.get('Value')
                if val == 'true':
                    info['has_sidechain'] = True
                    break
        
        return info
    
    def _extract_automation_info(self, root: ET.Element) -> Dict[str, int]:
        """Extract automation density information."""
        info = {
            'lane_count': 0,
            'point_count': 0
        }
        
        # Count automation envelopes/lanes
        for elem in root.iter():
            if 'AutomationEnvelope' in elem.tag:
                info['lane_count'] += 1
                
                # Count automation points within the envelope
                for point_elem in elem.iter():
                    if 'FloatEvent' in point_elem.tag or 'BoolEvent' in point_elem.tag:
                        info['point_count'] += 1
        
        return info
    
    def _extract_groove_pool_size(self, root: ET.Element) -> int:
        """Extract the number of grooves in the groove pool."""
        count = 0
        for elem in root.iter():
            if 'GroovePool' in elem.tag:
                for groove in elem:
                    if 'Groove' in groove.tag:
                        count += 1
        return count
    
    def _extract_scene_count(self, root: ET.Element) -> int:
        """Extract the number of scenes in the session view."""
        count = 0
        for elem in root.iter():
            if 'Scenes' in elem.tag:
                for scene in elem:
                    if 'Scene' in scene.tag:
                        count += 1
        return count
    
    def _extract_key_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract musical key and scale information with priority logic.
        
        Priority:
        1. Global project scale (LiveSet > ScaleInformation)
        2. If all clips agree on a scale (or are not set), use that
        3. If not set or conflicting, return None
        
        Returns:
            Dict with 'key', 'scale', and 'is_in_key' keys.
        """
        info = {
            'key': None,
            'scale': None,
            'is_in_key': None
        }
        
        # Key mapping (0-11 to note names)
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Scale name mapping (0-24 map to scale types)
        scale_name_map = {
            '0': 'Major',
            '1': 'Minor',
            '2': 'Dorian',
            '3': 'Mixolydian',
            '4': 'Lydian',
            '5': 'Phrygian',
            '6': 'Locrian',
            '7': 'Diminished',
            '8': 'Whole Half',
            '9': 'Whole Tone',
            '10': 'Minor Blues',
            '11': 'Minor Pentatonic',
            '12': 'Major Pentatonic',
            '13': 'Harmonic Minor',
            '14': 'Melodic Minor',
            '15': 'Super Locrian',
            '16': 'Bhairav',
            '17': 'Hungarian Minor',
            '18': 'Minor Gypsy',
            '19': 'Hirojoshi',
            '20': 'In-Sen',
            '21': 'Iwato',
            '22': 'Kumoi',
            '23': 'Pelog',
            '24': 'Spanish',
        }
        
        # Step 1: Check for global project scale (LiveSet > ScaleInformation)
        global_key = None
        global_scale = None
        global_is_in_key = None
        
        liveset = None
        for elem in root.iter():
            if elem.tag == 'LiveSet':
                liveset = elem
                break
        
        if liveset is not None:
            # First, check for InKey setting
            for child in liveset:
                if child.tag == 'InKey':
                    inkey_value = child.get('Value', 'false')
                    global_is_in_key = inkey_value.lower() == 'true'
                    break
            
            # Then check for ScaleInformation
            for child in liveset:
                if child.tag == 'ScaleInformation':
                    # Extract Root and Name
                    root_value = None
                    name_value = None
                    for subchild in child:
                        if subchild.tag == 'Root':
                            root_value = subchild.get('Value')
                        elif subchild.tag == 'Name':
                            name_value = subchild.get('Value')
                    
                    # Extract scale information
                    if root_value is not None and name_value is not None:
                        try:
                            root_idx = int(root_value)
                            name_idx = int(name_value)
                            
                            # If InKey is enabled, even Root=0/Name=0 means "C Major" is set
                            # Otherwise, only consider non-default values as "set"
                            if global_is_in_key is True or (root_idx != 0 or name_idx != 0):
                                if 0 <= root_idx < 12:
                                    global_key = key_names[root_idx]
                                name_str = str(name_idx)
                                if name_str in scale_name_map:
                                    global_scale = scale_name_map[name_str]
                        except (ValueError, TypeError):
                            pass
                    break
        
        # Step 2: Check clip scales
        clip_scales = []
        for clip_elem in root.iter():
            if clip_elem.tag in ['AudioClip', 'MidiClip']:
                clip_key = None
                clip_scale = None
                
                # Look for ScaleInformation within the clip
                for child in clip_elem.iter():
                    if child.tag == 'ScaleInformation':
                        root_value = None
                        name_value = None
                        for subchild in child:
                            if subchild.tag == 'Root':
                                root_value = subchild.get('Value')
                            elif subchild.tag == 'Name':
                                name_value = subchild.get('Value')
                        
                        if root_value is not None and name_value is not None:
                            try:
                                root_idx = int(root_value)
                                name_idx = int(name_value)
                                # Only consider it set if not default (0/0)
                                if root_idx != 0 or name_idx != 0:
                                    if 0 <= root_idx < 12:
                                        clip_key = key_names[root_idx]
                                    name_str = str(name_idx)
                                    if name_str in scale_name_map:
                                        clip_scale = scale_name_map[name_str]
                            except (ValueError, TypeError):
                                pass
                        break
                
                # Only add if clip has a scale set
                if clip_key is not None or clip_scale is not None:
                    clip_scales.append({
                        'key': clip_key,
                        'scale': clip_scale
                    })
        
        # Step 3: Apply priority logic
        # Priority 1: Use global scale if set
        if global_key is not None or global_scale is not None:
            info['key'] = global_key
            info['scale'] = global_scale
            info['is_in_key'] = global_is_in_key
        # Priority 2: If all clips agree (or are not set), use clip scale
        elif clip_scales:
            # Check if all clips have the same scale
            unique_scales = set()
            for clip_scale_info in clip_scales:
                scale_str = f"{clip_scale_info['key']}:{clip_scale_info['scale']}"
                unique_scales.add(scale_str)
            
            # If all clips agree on one scale, use it
            if len(unique_scales) == 1:
                first_scale = clip_scales[0]
                info['key'] = first_scale['key']
                info['scale'] = first_scale['scale']
                info['is_in_key'] = None  # Not applicable for clip-based scale
        
        return info
    
    def _count_plugin_parameters(self, root: ET.Element) -> int:
        """Count the total number of plugin parameters (complexity indicator)."""
        count = 0
        
        for elem in root.iter():
            if 'PluginDevice' in elem.tag:
                # Count parameter containers
                for param in elem.iter():
                    if 'ParameterSlot' in param.tag or 'PluginFloatParameter' in param.tag:
                        count += 1
        
        return count
    
    # =========================================================================
    # Feature Vector Generation (for ML)
    # =========================================================================
    
    def generate_feature_vector(self, metadata: ProjectMetadata) -> List[float]:
        """Generate a feature vector from project metadata for ML.
        
        This creates a numerical representation of the project suitable for
        similarity calculations, clustering, and other ML tasks.
        
        Args:
            metadata: ProjectMetadata object to vectorize.
            
        Returns:
            List of float values representing the project features.
        """
        features = []
        
        # Basic features
        features.append(float(metadata.tempo or 120.0))  # Default tempo
        features.append(float(metadata.track_count))
        features.append(float(metadata.audio_tracks))
        features.append(float(metadata.midi_tracks))
        features.append(float(metadata.return_tracks))
        features.append(float(metadata.arrangement_length or 0.0))
        features.append(float(len(metadata.plugins)))
        features.append(float(len(metadata.devices)))
        features.append(float(len(metadata.sample_references)))
        features.append(1.0 if metadata.has_automation else 0.0)
        
        # Extended features (if available)
        if metadata.extended:
            ext = metadata.extended
            features.append(float(ext.total_device_count))
            features.append(float(ext.unique_device_types))
            features.append(float(ext.avg_devices_per_track))
            features.append(float(ext.audio_clip_count))
            features.append(float(ext.midi_clip_count))
            features.append(float(ext.total_clip_count))
            features.append(float(ext.avg_clip_duration))
            features.append(1.0 if ext.has_sends else 0.0)
            features.append(float(ext.send_count))
            features.append(1.0 if ext.has_sidechain else 0.0)
            features.append(float(ext.automation_lane_count))
            features.append(float(ext.automation_point_count))
            features.append(float(ext.groove_pool_size))
            features.append(float(ext.scene_count))
            features.append(float(ext.plugin_parameter_count))
        else:
            # Pad with zeros if no extended metadata
            features.extend([0.0] * 15)
        
        return features
    
    @staticmethod
    def get_feature_names() -> List[str]:
        """Get the names of features in the feature vector.
        
        Returns:
            List of feature names corresponding to generate_feature_vector output.
        """
        return [
            'tempo',
            'track_count',
            'audio_tracks',
            'midi_tracks',
            'return_tracks',
            'arrangement_length',
            'plugin_count',
            'device_count',
            'sample_count',
            'has_automation',
            'total_device_count',
            'unique_device_types',
            'avg_devices_per_track',
            'audio_clip_count',
            'midi_clip_count',
            'total_clip_count',
            'avg_clip_duration',
            'has_sends',
            'send_count',
            'has_sidechain',
            'automation_lane_count',
            'automation_point_count',
            'groove_pool_size',
            'scene_count',
            'plugin_parameter_count'
        ]