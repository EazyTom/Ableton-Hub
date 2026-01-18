"""Comprehensive ALS file structure analysis.

Analyzes .als files to discover all extractable information including:
- Project metadata
- Track structure
- Device/plugin usage
- Sample references
- Backup file relationships
- Export-related data
- Any other useful information

Usage:
    python analyze_als_structure.py <path_to_project_folder_or_als_file>
"""

import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
from typing import Dict, List, Any, Set
from datetime import datetime
import json


class ALSAnalyzer:
    """Comprehensive analyzer for Ableton Live Set files."""
    
    def __init__(self):
        self.all_elements: Dict[str, List[Dict]] = {}
        self.unique_tags: Set[str] = set()
        self.backup_files: List[Path] = []
        self.main_file: Path = None
        
    def analyze_file(self, als_path: Path) -> Dict[str, Any]:
        """Analyze a single .als file and extract all information."""
        result: Dict[str, Any] = {
            'file_path': str(als_path),
            'file_size': als_path.stat().st_size if als_path.exists() else 0,
            'modified_date': datetime.fromtimestamp(als_path.stat().st_mtime).isoformat() if als_path.exists() else None,
            'elements': {},
            'metadata': {},
            'structure': {},
            'extractable_data': {}
        }
        
        try:
            with gzip.open(als_path, 'rb') as f:
                xml_data = f.read()
            
            root = ET.fromstring(xml_data)
            
            # Extract basic metadata
            result['metadata'] = self._extract_metadata(root, als_path)
            
            # Extract all unique element types
            result['structure'] = self._analyze_structure(root)
            
            # Extract specific data categories
            result['extractable_data'] = {
                'tracks': self._extract_tracks(root),
                'devices': self._extract_devices(root),
                'plugins': self._extract_plugins(root),
                'samples': self._extract_samples(root),
                'clips': self._extract_clips(root),
                'automation': self._extract_automation(root),
                'export_info': self._extract_export_info(root),
                'backup_info': self._extract_backup_info(root),
                'project_info': self._extract_project_info(root),
                'timing_info': self._extract_timing_info(root),
                'file_references': self._extract_file_references(root),
                'preferences': self._extract_preferences(root),
            }
            
            # Store all unique tags
            for elem in root.iter():
                self.unique_tags.add(elem.tag)
            
        except Exception as e:
            result['error'] = str(e)
            import traceback
            result['traceback'] = traceback.format_exc()
        
        return result
    
    def _extract_metadata(self, root: ET.Element, path: Path) -> Dict[str, Any]:
        """Extract basic metadata from root element."""
        metadata = {
            'root_tag': root.tag,
            'root_attributes': root.attrib,
            'ableton_version': root.get('Creator', 'Unknown'),
            'major_version': root.get('MajorVersion', 'Unknown'),
            'minor_version': root.get('MinorVersion', 'Unknown'),
        }
        
        # Find LiveSet element
        for elem in root:
            if 'LiveSet' in elem.tag:
                metadata['liveset_attributes'] = elem.attrib
                break
        
        return metadata
    
    def _analyze_structure(self, root: ET.Element) -> Dict[str, Any]:
        """Analyze the XML structure hierarchy."""
        structure = {
            'top_level_elements': [],
            'element_counts': {},
            'max_depth': 0,
            'total_elements': 0
        }
        
        def count_elements(elem, depth=0):
            structure['max_depth'] = max(structure['max_depth'], depth)
            structure['total_elements'] += 1
            
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            structure['element_counts'][tag] = structure['element_counts'].get(tag, 0) + 1
            
            for child in elem:
                count_elements(child, depth + 1)
        
        # Get top-level children
        for child in root:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            structure['top_level_elements'].append(tag)
            count_elements(child, 1)
        
        return structure
    
    def _extract_tracks(self, root: ET.Element) -> Dict[str, Any]:
        """Extract track information."""
        tracks = {
            'audio_tracks': [],
            'midi_tracks': [],
            'return_tracks': [],
            'group_tracks': [],
            'master_track': None,
            'total_count': 0
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if tag == 'AudioTrack':
                track_info = self._extract_track_info(elem, 'audio')
                tracks['audio_tracks'].append(track_info)
                tracks['total_count'] += 1
            elif tag == 'MidiTrack':
                track_info = self._extract_track_info(elem, 'midi')
                tracks['midi_tracks'].append(track_info)
                tracks['total_count'] += 1
            elif tag == 'ReturnTrack':
                track_info = self._extract_track_info(elem, 'return')
                tracks['return_tracks'].append(track_info)
                tracks['total_count'] += 1
            elif tag == 'GroupTrack':
                track_info = self._extract_track_info(elem, 'group')
                tracks['group_tracks'].append(track_info)
                tracks['total_count'] += 1
            elif tag == 'MasterTrack':
                tracks['master_track'] = self._extract_track_info(elem, 'master')
        
        return tracks
    
    def _extract_track_info(self, track_elem: ET.Element, track_type: str) -> Dict[str, Any]:
        """Extract information from a track element."""
        info = {
            'type': track_type,
            'id': track_elem.get('Id', ''),
            'attributes': track_elem.attrib,
            'name': None,
            'devices': [],
            'clips': [],
            'automation': []
        }
        
        # Extract track name
        for name_elem in track_elem.iter():
            if 'Name' in name_elem.tag or 'UserName' in name_elem.tag:
                name_val = name_elem.get('Value') or name_elem.text
                if name_val and name_val.strip():
                    info['name'] = name_val.strip()
                    break
        
        # Count devices
        device_count = 0
        for child in track_elem.iter():
            if 'DeviceChain' in child.tag or 'Devices' in child.tag:
                device_count += len(list(child))
        info['device_count'] = device_count
        
        return info
    
    def _extract_devices(self, root: ET.Element) -> Dict[str, Any]:
        """Extract Ableton device information."""
        devices = {
            'device_types': set(),
            'device_names': [],
            'device_count': 0,
            'by_category': {}
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'Device' in tag and tag != 'DeviceChain':
                devices['device_types'].add(tag)
                devices['device_count'] += 1
                
                # Try to get device name
                for name_elem in elem.iter():
                    if 'UserName' in name_elem.tag:
                        name = name_elem.get('Value')
                        if name:
                            devices['device_names'].append(name)
                            break
        
        devices['device_types'] = sorted(list(devices['device_types']))
        return devices
    
    def _extract_plugins(self, root: ET.Element) -> Dict[str, Any]:
        """Extract VST/AU plugin information."""
        plugins = {
            'vst_plugins': [],
            'au_plugins': [],
            'plugin_paths': [],
            'plugin_count': 0
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'PluginDevice' in tag or 'VstPlugin' in tag or 'AuPlugin' in tag:
                plugins['plugin_count'] += 1
                
                # Extract plugin path
                for path_elem in elem.iter():
                    if 'Path' in path_elem.tag:
                        path_val = path_elem.get('Value')
                        if path_val:
                            plugins['plugin_paths'].append(path_val)
                            if '.vst' in path_val.lower() or '.dll' in path_val.lower():
                                plugins['vst_plugins'].append(path_val)
                            elif '.component' in path_val.lower() or '.au' in path_val.lower():
                                plugins['au_plugins'].append(path_val)
        
        return plugins
    
    def _extract_samples(self, root: ET.Element) -> Dict[str, Any]:
        """Extract sample/audio file references."""
        samples = {
            'sample_paths': [],
            'sample_count': 0,
            'relative_paths': [],
            'absolute_paths': []
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'FileRef' in tag or 'SampleRef' in tag or 'OriginalFileRef' in tag:
                # Look for path information
                for child in elem:
                    if 'Path' in child.tag or 'RelativePath' in child.tag:
                        path_val = child.get('Value') or child.text
                        if path_val:
                            samples['sample_paths'].append(path_val)
                            samples['sample_count'] += 1
                            
                            if path_val.startswith('/') or ':' in path_val:
                                samples['absolute_paths'].append(path_val)
                            else:
                                samples['relative_paths'].append(path_val)
        
        return samples
    
    def _extract_clips(self, root: ET.Element) -> Dict[str, Any]:
        """Extract clip information."""
        clips = {
            'audio_clips': 0,
            'midi_clips': 0,
            'clip_names': [],
            'clip_count': 0
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'AudioClip' in tag:
                clips['audio_clips'] += 1
                clips['clip_count'] += 1
            elif 'MidiClip' in tag:
                clips['midi_clips'] += 1
                clips['clip_count'] += 1
            
            # Extract clip names
            if 'Clip' in tag:
                for name_elem in elem.iter():
                    if 'Name' in name_elem.tag:
                        name = name_elem.get('Value') or name_elem.text
                        if name and name.strip():
                            clips['clip_names'].append(name.strip())
                            break
        
        return clips
    
    def _extract_automation(self, root: ET.Element) -> Dict[str, Any]:
        """Extract automation information."""
        automation = {
            'has_automation': False,
            'automation_lanes': 0,
            'automation_points': 0
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'Automation' in tag:
                automation['has_automation'] = True
            if 'AutomationLane' in tag:
                automation['automation_lanes'] += 1
            if 'AutomationPoint' in tag:
                automation['automation_points'] += 1
        
        return automation
    
    def _extract_export_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract export-related information."""
        export_info = {
            'export_logs': [],
            'render_settings': {},
            'export_directory': None,
            'export_count': 0
        }
        
        for elem in root.iter():
            tag_lower = elem.tag.lower()
            
            if 'exportlog' in tag_lower or 'exporthistory' in tag_lower:
                export_info['export_logs'].append({
                    'tag': elem.tag,
                    'attributes': elem.attrib,
                    'children': {child.tag: (child.get('Value') or child.text) for child in elem}
                })
                export_info['export_count'] += 1
            
            if 'audiorendersettings' in tag_lower or 'rendersettings' in tag_lower:
                for child in elem:
                    key = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    value = child.get('Value') or child.text
                    if value:
                        export_info['render_settings'][key] = value
                        if 'path' in key.lower() or 'dir' in key.lower() or 'folder' in key.lower():
                            export_info['export_directory'] = value
        
        return export_info
    
    def _extract_backup_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract backup-related information."""
        backup_info = {
            'backup_references': [],
            'backup_count': 0
        }
        
        for elem in root.iter():
            tag_lower = elem.tag.lower()
            
            if 'backup' in tag_lower:
                backup_info['backup_references'].append({
                    'tag': elem.tag,
                    'attributes': elem.attrib,
                    'text': elem.text
                })
                backup_info['backup_count'] += 1
        
        return backup_info
    
    def _extract_project_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract project-level information."""
        project_info = {
            'name': None,
            'annotation': None,
            'tempo': None,
            'time_signature': None,
            'arrangement_length': None,
            'scenes': [],
            'scene_count': 0
        }
        
        # Extract tempo
        for elem in root.iter():
            if 'Tempo' in elem.tag:
                manual = elem.find('.//Manual')
                if manual is not None:
                    tempo_val = manual.get('Value')
                    if tempo_val:
                        try:
                            project_info['tempo'] = float(tempo_val)
                        except ValueError:
                            pass
        
        # Extract time signature
        for elem in root.iter():
            if 'TimeSignature' in elem.tag:
                numerator = elem.find('.//Numerator')
                denominator = elem.find('.//Denominator')
                if numerator is not None and denominator is not None:
                    num = numerator.get('Value', '4')
                    den = denominator.get('Value', '4')
                    project_info['time_signature'] = f"{num}/{den}"
        
        # Extract annotation
        for elem in root.iter():
            if 'Annotation' in elem.tag:
                annotation = elem.get('Value') or elem.text
                if annotation:
                    project_info['annotation'] = annotation
        
        # Extract scenes
        for elem in root.iter():
            if 'Scene' in elem.tag:
                project_info['scene_count'] += 1
                scene_name = None
                for name_elem in elem.iter():
                    if 'Name' in name_elem.tag:
                        scene_name = name_elem.get('Value') or name_elem.text
                        break
                if scene_name:
                    project_info['scenes'].append(scene_name)
        
        return project_info
    
    def _extract_timing_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract timing and arrangement information."""
        timing = {
            'arrangement_length': None,
            'loop_start': None,
            'loop_end': None,
            'start_marker': None,
            'end_marker': None
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'ArrangementLength' in tag:
                length = elem.get('Value')
                if length:
                    try:
                        timing['arrangement_length'] = float(length)
                    except ValueError:
                        pass
            
            if 'LoopStart' in tag:
                timing['loop_start'] = elem.get('Value')
            if 'LoopEnd' in tag:
                timing['loop_end'] = elem.get('Value')
            if 'StartMarker' in tag:
                timing['start_marker'] = elem.get('Value')
            if 'EndMarker' in tag:
                timing['end_marker'] = elem.get('Value')
        
        return timing
    
    def _extract_file_references(self, root: ET.Element) -> Dict[str, Any]:
        """Extract all file references."""
        file_refs = {
            'all_paths': [],
            'absolute_paths': [],
            'relative_paths': [],
            'file_types': {}
        }
        
        for elem in root.iter():
            for child in elem:
                if 'Path' in child.tag or 'FileRef' in child.tag or 'RelativePath' in child.tag:
                    path_val = child.get('Value') or child.text
                    if path_val and path_val.strip():
                        file_refs['all_paths'].append(path_val)
                        
                        if path_val.startswith('/') or (len(path_val) > 1 and path_val[1] == ':'):
                            file_refs['absolute_paths'].append(path_val)
                        else:
                            file_refs['relative_paths'].append(path_val)
                        
                        # Categorize by extension
                        ext = Path(path_val).suffix.lower()
                        if ext:
                            file_refs['file_types'][ext] = file_refs['file_types'].get(ext, 0) + 1
        
        return file_refs
    
    def _extract_preferences(self, root: ET.Element) -> Dict[str, Any]:
        """Extract preference/setting information."""
        preferences = {
            'settings': {},
            'preferences': {}
        }
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if 'Settings' in tag or 'Preference' in tag:
                key = tag
                value = elem.get('Value') or elem.text or elem.attrib
                if 'Settings' in tag:
                    preferences['settings'][key] = value
                else:
                    preferences['preferences'][key] = value
        
        return preferences
    
    def find_backup_files(self, project_path: Path) -> List[Path]:
        """Find all backup .als files in the project folder."""
        backups = []
        
        if project_path.is_file():
            project_dir = project_path.parent
        else:
            project_dir = project_path
        
        # Look in Backup folder
        backup_dir = project_dir / 'Backup'
        if backup_dir.exists():
            for backup_file in backup_dir.glob('*.als'):
                backups.append(backup_file)
        
        # Also check for .als files with timestamps in name
        for als_file in project_dir.rglob('*.als'):
            if 'backup' in als_file.name.lower() or '[' in als_file.name:
                if als_file not in backups:
                    backups.append(als_file)
        
        return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)
    
    def analyze_project(self, project_path: Path) -> Dict[str, Any]:
        """Analyze a project folder or single .als file."""
        if project_path.is_file() and project_path.suffix.lower() == '.als':
            self.main_file = project_path
            project_dir = project_path.parent
        else:
            project_dir = project_path
            # Find main .als file (usually same name as folder)
            main_als = project_dir / f"{project_dir.name}.als"
            if main_als.exists():
                self.main_file = main_als
            else:
                # Find any .als file in root
                als_files = list(project_dir.glob('*.als'))
                if als_files:
                    self.main_file = als_files[0]
        
        results = {
            'project_folder': str(project_dir),
            'main_file': str(self.main_file) if self.main_file else None,
            'backup_files': [],
            'main_analysis': None,
            'backup_analyses': [],
            'comparison': {}
        }
        
        # Analyze main file
        if self.main_file and self.main_file.exists():
            results['main_analysis'] = self.analyze_file(self.main_file)
        
        # Find and analyze backups
        self.backup_files = self.find_backup_files(project_path)
        results['backup_files'] = [str(f) for f in self.backup_files]
        
        for backup in self.backup_files:
            backup_analysis = self.analyze_file(backup)
            results['backup_analyses'].append(backup_analysis)
        
        # Compare main vs backups
        if results['main_analysis'] and results['backup_analyses']:
            results['comparison'] = self._compare_files(
                results['main_analysis'],
                results['backup_analyses']
            )
        
        return results
    
    def _compare_files(self, main: Dict, backups: List[Dict]) -> Dict[str, Any]:
        """Compare main file with backups to identify changes."""
        comparison = {
            'version_changes': [],
            'track_changes': [],
            'device_changes': [],
            'plugin_changes': [],
            'timing_changes': []
        }
        
        main_tracks = main.get('extractable_data', {}).get('tracks', {}).get('total_count', 0)
        main_devices = main.get('extractable_data', {}).get('devices', {}).get('device_count', 0)
        main_plugins = main.get('extractable_data', {}).get('plugins', {}).get('plugin_count', 0)
        main_tempo = main.get('extractable_data', {}).get('project_info', {}).get('tempo')
        
        for backup in backups:
            backup_tracks = backup.get('extractable_data', {}).get('tracks', {}).get('total_count', 0)
            backup_devices = backup.get('extractable_data', {}).get('devices', {}).get('device_count', 0)
            backup_plugins = backup.get('extractable_data', {}).get('plugins', {}).get('plugin_count', 0)
            backup_tempo = backup.get('extractable_data', {}).get('project_info', {}).get('tempo')
            
            if backup_tracks != main_tracks:
                comparison['track_changes'].append({
                    'backup': backup['file_path'],
                    'tracks': backup_tracks,
                    'main_tracks': main_tracks
                })
            
            if backup_devices != main_devices:
                comparison['device_changes'].append({
                    'backup': backup['file_path'],
                    'devices': backup_devices,
                    'main_devices': main_devices
                })
            
            if backup_plugins != main_plugins:
                comparison['plugin_changes'].append({
                    'backup': backup['file_path'],
                    'plugins': backup_plugins,
                    'main_plugins': main_plugins
                })
            
            if backup_tempo and main_tempo and abs(backup_tempo - main_tempo) > 0.1:
                comparison['timing_changes'].append({
                    'backup': backup['file_path'],
                    'tempo': backup_tempo,
                    'main_tempo': main_tempo
                })
        
        return comparison


def format_analysis_report(results: Dict[str, Any]) -> str:
    """Format analysis results as a readable report."""
    report = []
    report.append("=" * 100)
    report.append("COMPREHENSIVE ABLETON LIVE SET (.als) FILE ANALYSIS")
    report.append("=" * 100)
    report.append("")
    
    report.append(f"Project Folder: {results.get('project_folder', 'N/A')}")
    report.append(f"Main File: {results.get('main_file', 'N/A')}")
    report.append(f"Backup Files Found: {len(results.get('backup_files', []))}")
    report.append("")
    
    # Main file analysis
    if results.get('main_analysis'):
        main = results['main_analysis']
        report.append("=" * 100)
        report.append("MAIN FILE ANALYSIS")
        report.append("=" * 100)
        report.append(f"File: {main.get('file_path', 'N/A')}")
        report.append(f"Size: {main.get('file_size', 0):,} bytes")
        report.append(f"Modified: {main.get('modified_date', 'N/A')}")
        report.append("")
        
        # Metadata
        metadata = main.get('metadata', {})
        report.append("METADATA:")
        report.append(f"  Ableton Version: {metadata.get('ableton_version', 'N/A')}")
        report.append(f"  Major Version: {metadata.get('major_version', 'N/A')}")
        report.append(f"  Minor Version: {metadata.get('minor_version', 'N/A')}")
        report.append("")
        
        # Structure
        structure = main.get('structure', {})
        report.append("XML STRUCTURE:")
        report.append(f"  Total Elements: {structure.get('total_elements', 0):,}")
        report.append(f"  Max Depth: {structure.get('max_depth', 0)}")
        report.append(f"  Top-Level Elements: {', '.join(structure.get('top_level_elements', [])[:10])}")
        report.append(f"  Unique Element Types: {len(structure.get('element_counts', {}))}")
        report.append("")
        
        # Extractable Data
        data = main.get('extractable_data', {})
        
        # Tracks
        tracks = data.get('tracks', {})
        report.append("TRACKS:")
        report.append(f"  Total: {tracks.get('total_count', 0)}")
        report.append(f"  Audio: {len(tracks.get('audio_tracks', []))}")
        report.append(f"  MIDI: {len(tracks.get('midi_tracks', []))}")
        report.append(f"  Return: {len(tracks.get('return_tracks', []))}")
        report.append(f"  Group: {len(tracks.get('group_tracks', []))}")
        report.append(f"  Master: {'Yes' if tracks.get('master_track') else 'No'}")
        report.append("")
        
        # Devices
        devices = data.get('devices', {})
        report.append("DEVICES:")
        report.append(f"  Total: {devices.get('device_count', 0)}")
        report.append(f"  Types: {', '.join(devices.get('device_types', [])[:20])}")
        if len(devices.get('device_types', [])) > 20:
            report.append(f"  ... and {len(devices.get('device_types', [])) - 20} more types")
        report.append("")
        
        # Plugins
        plugins = data.get('plugins', {})
        report.append("PLUGINS:")
        report.append(f"  Total: {plugins.get('plugin_count', 0)}")
        report.append(f"  VST: {len(plugins.get('vst_plugins', []))}")
        report.append(f"  AU: {len(plugins.get('au_plugins', []))}")
        if plugins.get('plugin_paths'):
            report.append("  Sample Plugin Paths:")
            for path in plugins.get('plugin_paths', [])[:10]:
                report.append(f"    - {path}")
            if len(plugins.get('plugin_paths', [])) > 10:
                report.append(f"    ... and {len(plugins.get('plugin_paths', [])) - 10} more")
        report.append("")
        
        # Samples
        samples = data.get('samples', {})
        report.append("SAMPLES/AUDIO REFERENCES:")
        report.append(f"  Total: {samples.get('sample_count', 0)}")
        report.append(f"  Absolute Paths: {len(samples.get('absolute_paths', []))}")
        report.append(f"  Relative Paths: {len(samples.get('relative_paths', []))}")
        if samples.get('sample_paths'):
            report.append("  Sample Paths (first 10):")
            for path in samples.get('sample_paths', [])[:10]:
                report.append(f"    - {path}")
        report.append("")
        
        # Clips
        clips = data.get('clips', {})
        report.append("CLIPS:")
        report.append(f"  Total: {clips.get('clip_count', 0)}")
        report.append(f"  Audio Clips: {clips.get('audio_clips', 0)}")
        report.append(f"  MIDI Clips: {clips.get('midi_clips', 0)}")
        if clips.get('clip_names'):
            report.append(f"  Named Clips: {len(clips.get('clip_names', []))}")
        report.append("")
        
        # Project Info
        project_info = data.get('project_info', {})
        report.append("PROJECT INFO:")
        report.append(f"  Tempo: {project_info.get('tempo', 'N/A')} BPM")
        report.append(f"  Time Signature: {project_info.get('time_signature', 'N/A')}")
        report.append(f"  Scenes: {project_info.get('scene_count', 0)}")
        if project_info.get('annotation'):
            report.append(f"  Annotation: {project_info.get('annotation')[:100]}...")
        report.append("")
        
        # Timing
        timing = data.get('timing_info', {})
        report.append("TIMING/ARRANGEMENT:")
        report.append(f"  Arrangement Length: {timing.get('arrangement_length', 'N/A')} bars")
        if timing.get('loop_start'):
            report.append(f"  Loop Start: {timing.get('loop_start')}")
        if timing.get('loop_end'):
            report.append(f"  Loop End: {timing.get('loop_end')}")
        report.append("")
        
        # Automation
        automation = data.get('automation', {})
        report.append("AUTOMATION:")
        report.append(f"  Has Automation: {automation.get('has_automation', False)}")
        report.append(f"  Automation Lanes: {automation.get('automation_lanes', 0)}")
        report.append(f"  Automation Points: {automation.get('automation_points', 0)}")
        report.append("")
        
        # File References
        file_refs = data.get('file_references', {})
        report.append("FILE REFERENCES:")
        report.append(f"  Total Paths: {len(file_refs.get('all_paths', []))}")
        report.append(f"  Absolute: {len(file_refs.get('absolute_paths', []))}")
        report.append(f"  Relative: {len(file_refs.get('relative_paths', []))}")
        if file_refs.get('file_types'):
            report.append("  File Types:")
            for ext, count in sorted(file_refs.get('file_types', {}).items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"    {ext}: {count}")
        report.append("")
        
        # Export Info
        export_info = data.get('export_info', {})
        report.append("EXPORT INFORMATION:")
        report.append(f"  Export Logs Found: {export_info.get('export_count', 0)}")
        if export_info.get('export_directory'):
            report.append(f"  Export Directory: {export_info.get('export_directory')}")
        if export_info.get('render_settings'):
            report.append("  Render Settings:")
            for key, value in list(export_info.get('render_settings', {}).items())[:5]:
                report.append(f"    {key}: {value}")
        report.append("")
        
        # Backup Info
        backup_info = data.get('backup_info', {})
        report.append("BACKUP REFERENCES:")
        report.append(f"  Backup References in File: {backup_info.get('backup_count', 0)}")
        report.append("")
    
    # Backup files analysis
    if results.get('backup_analyses'):
        report.append("=" * 100)
        report.append("BACKUP FILES ANALYSIS")
        report.append("=" * 100)
        report.append("")
        
        for i, backup in enumerate(results['backup_analyses'], 1):
            report.append(f"Backup {i}: {backup.get('file_path', 'N/A')}")
            report.append(f"  Size: {backup.get('file_size', 0):,} bytes")
            report.append(f"  Modified: {backup.get('modified_date', 'N/A')}")
            
            backup_data = backup.get('extractable_data', {})
            backup_tracks = backup_data.get('tracks', {}).get('total_count', 0)
            backup_tempo = backup_data.get('project_info', {}).get('tempo')
            
            report.append(f"  Tracks: {backup_tracks}")
            report.append(f"  Tempo: {backup_tempo or 'N/A'} BPM")
            report.append("")
    
    # Comparison
    if results.get('comparison'):
        comparison = results['comparison']
        report.append("=" * 100)
        report.append("MAIN vs BACKUPS COMPARISON")
        report.append("=" * 100)
        report.append("")
        
        if comparison.get('track_changes'):
            report.append("Track Count Changes:")
            for change in comparison['track_changes']:
                report.append(f"  {Path(change['backup']).name}: {change['tracks']} tracks (main has {change['main_tracks']})")
            report.append("")
        
        if comparison.get('device_changes'):
            report.append("Device Count Changes:")
            for change in comparison['device_changes']:
                report.append(f"  {Path(change['backup']).name}: {change.get('devices', 'N/A')} devices (main has {change.get('main_devices', 'N/A')})")
            report.append("")
        
        if comparison.get('plugin_changes'):
            report.append("Plugin Count Changes:")
            for change in comparison['plugin_changes']:
                report.append(f"  {Path(change['backup']).name}: {change['plugins']} plugins (main has {change['main_plugins']})")
            report.append("")
        
        if comparison.get('timing_changes'):
            report.append("Tempo Changes:")
            for change in comparison['timing_changes']:
                report.append(f"  {Path(change['backup']).name}: {change['tempo']} BPM (main: {change['main_tempo']} BPM)")
            report.append("")
    
    # Feature Recommendations
    report.append("=" * 100)
    report.append("POTENTIAL FEATURES TO EXTRACT/BUILD")
    report.append("=" * 100)
    report.append("")
    
    if results.get('main_analysis'):
        main_data = results['main_analysis'].get('extractable_data', {})
        
        report.append("1. BACKUP FILE TRACKING:")
        report.append("   - Link backup files to main project")
        report.append("   - Track changes between versions (tracks, devices, plugins, tempo)")
        report.append("   - Show version history timeline")
        report.append("   - Restore from backup functionality")
        report.append("")
        
        report.append("2. PROJECT EVOLUTION ANALYSIS:")
        report.append("   - Track how projects evolve over time")
        report.append("   - Identify when tracks/devices/plugins were added/removed")
        report.append("   - Tempo changes over time")
        report.append("   - Project complexity metrics over time")
        report.append("")
        
        if main_data.get('file_references', {}).get('absolute_paths'):
            report.append("3. MISSING FILE DETECTION:")
            report.append("   - Check if referenced absolute paths still exist")
            report.append("   - Identify broken sample references")
            report.append("   - Suggest file relocation")
            report.append("")
        
        if main_data.get('samples', {}).get('sample_count', 0) > 0:
            report.append("4. SAMPLE LIBRARY TRACKING:")
            report.append("   - Track which samples are used across projects")
            report.append("   - Identify duplicate sample usage")
            report.append("   - Sample dependency mapping")
            report.append("")
        
        if main_data.get('clips', {}).get('clip_count', 0) > 0:
            report.append("5. CLIP ANALYSIS:")
            report.append("   - Extract clip names and organize by track")
            report.append("   - Clip timeline visualization")
            report.append("   - Find similar clips across projects")
            report.append("")
        
        if main_data.get('automation', {}).get('has_automation'):
            report.append("6. AUTOMATION ANALYSIS:")
            report.append("   - Track automation complexity")
            report.append("   - Identify heavily automated projects")
            report.append("   - Automation pattern detection")
            report.append("")
        
        if main_data.get('plugins', {}).get('plugin_count', 0) > 0:
            report.append("7. PLUGIN USAGE ANALYTICS:")
            report.append("   - Track plugin usage across all projects")
            report.append("   - Identify most/least used plugins")
            report.append("   - Plugin dependency tracking")
            report.append("   - Missing plugin detection")
            report.append("")
        
        if main_data.get('devices', {}).get('device_count', 0) > 0:
            report.append("8. DEVICE CHAIN ANALYSIS:")
            report.append("   - Extract device chains per track")
            report.append("   - Common device chain patterns")
            report.append("   - Device usage statistics")
            report.append("")
        
        if results.get('backup_files'):
            report.append("9. VERSION CONTROL:")
            report.append("   - Automatic backup detection and linking")
            report.append("   - Diff view between versions")
        report.append("   - Rollback to previous version")
        report.append("")
        
        report.append("10. PROJECT HEALTH SCORING:")
        report.append("    - Based on file references, automation, complexity")
        report.append("    - Missing file warnings")
        report.append("    - Project completeness metrics")
        report.append("")
    
    report.append("=" * 100)
    report.append("END OF ANALYSIS")
    report.append("=" * 100)
    
    return "\n".join(report)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_als_structure.py <path_to_project_folder_or_als_file>")
        print("\nExample:")
        print("  python analyze_als_structure.py example-projects/McKenna-Bodhisattva\\ Project/")
        print("  python analyze_als_structure.py example-projects/McKenna-Bodhisattva\\ Project/McKenna-Bodhisattva.als")
        sys.exit(1)
    
    project_path = Path(sys.argv[1])
    
    if not project_path.exists():
        print(f"Error: Path not found: {project_path}")
        sys.exit(1)
    
    print(f"Analyzing: {project_path}")
    print("This may take a moment...\n")
    
    analyzer = ALSAnalyzer()
    results = analyzer.analyze_project(project_path)
    
    # Generate report
    report = format_analysis_report(results)
    
    # Save report
    if project_path.is_file():
        output_file = project_path.parent / f"{project_path.stem}_full_analysis.txt"
    else:
        output_file = project_path / f"{project_path.name}_full_analysis.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    print(f"\n[SAVED] Full analysis saved to: {output_file}")
    
    # Also save raw JSON for programmatic access
    json_file = output_file.with_suffix('.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[SAVED] Raw JSON data saved to: {json_file}")


if __name__ == '__main__':
    main()
