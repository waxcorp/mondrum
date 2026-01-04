# CLAUDE.md - MonDrum AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with the MonDrum codebase.

## Project Overview

**MonDrum** is an advanced audio sampler and sequencer application built in ChucK that integrates with Monome hardware controllers. It combines real-time audio processing, hardware control via OSC protocol, and GTK-based sample editing into a complete music production tool.

### Core Capabilities
- Sample playback and recording using ChucK's LiSa (Live Sample) unit generators
- Tempo-synchronized sequencing engine with BPM control
- Monome 8x8 grid hardware integration via OSC (Open Sound Control)
- GTK-based sample editing using Scalpel sound editor
- Multi-track composition with 128 tracks and 256 sample slots per program
- Real-time zoom and selection recording
- JSON-based selection persistence

## Technology Stack

### Primary Languages
- **ChucK** - Real-time audio synthesis language (main application)
- **Python 2.6+** - Utilities and GTK interfaces

### Key Dependencies
- **ChucK Built-ins**: LiSa, SndBuf, Gain, Dac, OscSend, OscRecv, Event
- **Python Libraries**: scalpel, pygtk, python-osc, wave, threading, json
- **Git Submodules**:
  - `lick` (github.com/heuermh/lick.git) - ChucK utilities
  - `chuck_performance_setup` (github.com/rdpoor/chuck_performance_setup.git)
- **Hardware**: Monome 64 (8x8 grid controller)

## Repository Structure

```
mondrum/
├── src/                           # Main source code
│   ├── mondrum.ck                # Main application (517 lines)
│   └── lib/                      # External libraries
│       ├── lick/                 # ChucK utilities (submodule)
│       └── chuck_performance_setup@ # Symlink to performance utils
│
├── test/                         # Testing infrastructure
│   ├── run.sh                    # Test runner (requires sudo)
│   ├── lib/test-setup.ck         # ProduceMonDrum factory
│   └── tests/                    # Individual test files
│       ├── mondrum.ck
│       ├── mondrum_sample_object.ck
│       ├── mondrum_sequencer.ck
│       ├── mondrum_track.ck
│       └── play_sample_locations.ck
│
├── util/                         # Utility scripts
│   ├── moncut.py                 # Monome sample cutting interface (482 lines)
│   ├── split_wave.py             # Stereo to mono WAV splitter
│   └── mock_osc_gtk.py           # Mock Monome GTK interface
│
├── doc/                          # Documentation
│   └── monome_osc_protocol.txt   # OSC protocol reference
│
└── submodules/                   # Git submodules
    └── chuck_performance_setup/
```

## Architecture and Key Classes

### Class Hierarchy

The codebase follows an object-oriented design with clear inheritance patterns:

```
Instrument (abstract base)
  └── Controller (control loop management)
        ├── KbController (keyboard input)
        └── MonDrumDBObject (persistable objects)
              ├── MonDrumProgram (256 sample slots)
              ├── MonDrumSequenceTrack (track in sequence)
              ├── MonDrumSample (LiSa-based playback)
              └── MonDrumSequence (timing/BPM control)
```

### Core Components in `src/mondrum.ck`

| Class | Purpose | Key Methods/Attributes |
|-------|---------|----------------------|
| `MonDrum` | Main application container | `init()` - OSC setup and initialization |
| `MonDrumProgram` | Sample container (256 slots) | `_samples[256]`, `gain()` |
| `MonDrumSequence` | Sequencing engine | `_tracks[128]`, BPM control, tick events |
| `MonDrumSample` | Playable sample | `play()`, `stop()`, `rate()`, `_lisa_l/r` |
| `MonDrumSequenceController` | Playback control | `playstart()`, `play()`, `stop()`, `playpause()` |
| `Monome` | Hardware interface | `set_level()`, `set_all_buttons()`, OSC send/recv |
| `MonomeButton` | Button state management | `key_event_manager()`, `glow()` |
| `MonDrumProject` | Top-level container | `_seqs[128]`, `_pgms[128]` |
| `MonDrumDB` | Persistence (stub) | `load_mondrum_project()` - mostly unimplemented |

### Python Utilities

**`util/moncut.py`** (482 lines) - Primary sample editing interface
- `GTKSound`: Scalpel sound editor integration
- `MonomeCutInterface`: Maps Monome grid to sample selection
- `MockMonome`: GTK-based hardware emulator
- Features: Multi-page interface, selection recording, zoom controls, JSON persistence

**`util/split_wave.py`** (56 lines)
- Splits stereo WAV to mono L/R files (ChucK SndBuf requires mono)

**`util/mock_osc_gtk.py`** (59 lines)
- Simple 8x8 GTK button grid for testing without hardware

## Development Workflows

### Running the Application

```bash
# Run main application with test setup
chuck src/mondrum.ck test/lib/test-setup.ck

# Run utility scripts
python util/moncut.py
python util/split_wave.py input.wav [start_frame end_frame]
```

### Running Tests

```bash
# Run all tests
bash test/run.sh

# Run specific test
bash test/run.sh test/tests/mondrum_sequencer.ck
```

**Note**: Tests use `sudo nice -n -19` for real-time priority. Requires root privileges.

### Test Execution Flow
1. Test runner prepends `ProduceMonDrum` factory to test file
2. Creates temporary combined file
3. Executes with ChucK
4. Displays code with line numbers
5. Captures and prints output
6. Cleans up temporary files

## Configuration Reference

### OSC Configuration (from `test/lib/test-setup.ck`)

```chuck
MonDrum Configuration:
  xmit_host: "localhost"
  xmit_prefix: "/monome"
  xmit_port: 14457
  recv_port: 8000
  model: 64 (8x8 grid)

MonDrumDB Configuration:
  xmit_prefix: "/mondrum"
  xmit_host: "localhost"
  xmit_port: 14030
  recv_port: 14130
```

### Monome Grid Layout (from `util/moncut.py`)

```
Rows 0-2: Reserved for future use
Row 3: Page selection buttons (coords 0-7, 3)
Rows 4-7: Playable area (coords 0-7, 4-7)
Control panel: Specific buttons for record, clear, zoom, etc.
  - (7,0)-(7,1): Control functions
  - (6,0)-(6,1): Additional controls
```

## Key Programming Patterns

### ChucK Patterns

**Time-based Programming**
```chuck
dur tick_dur = 60::second / bpm;
tick_dur => now;  // Wait for duration
```

**Concurrent Execution (Shreds)**
```chuck
(spork ~ play_shred(pos)).id() => _shred_id;  // Start concurrent process
Machine.remove(_shred_id);  // Stop process
```

**Audio Patching**
```chuck
_lisa_l => _out_l;   // Connect
_lisa_l =< _out_l;   // Disconnect
```

**Event Broadcasting**
```chuck
_tick_events[i].broadcast();  // Trigger listeners
_key => now;                   // Wait for event
```

### Python Patterns

**OSC Message Protocol**
```python
msg = OSC.OSCMessage('/monome/grid/led/set')
msg += [x, y, level]
self.osc_client.sendto(msg, (host, port))
```

**Threading for UI**
```python
t = threading.Thread(target=self.update_loop)
t.start()
```

## Coding Conventions

### Naming
- **Classes**: PascalCase (`MonDrum`, `MonomeButton`)
- **Methods**: camelCase in ChucK, snake_case in Python
- **Private members**: Underscore prefix (`_private_var`)
- **Public properties**: Getter/setter functions with same name

### Common Patterns
- Two-phase initialization: `init()`, `init_helper()`
- Property pattern: Function overloading for getters/setters
  ```chuck
  fun float gain() { return _gain; }
  fun void gain(float g) { g => _gain; }
  ```
- Factory pattern: `ProduceMonDrum` for configured instances
- Observer pattern: Event-based synchronization

## Critical Considerations for AI Assistants

### 1. Real-Time Audio Constraints
- ChucK runs in real-time; timing is critical
- Changes to timing logic (BPM, tick duration, sample playback) require careful testing
- Use `samp` or `::second` time units appropriately
- Test with actual audio output to verify timing

### 2. Hardware Dependencies
Code expects either:
- Physical Monome hardware connected via OSC
- Mock OSC server running (`mock_osc_gtk.py`)
- Proper OSC port configuration (ensure ports don't conflict)

### 3. State Management Complexity
Multiple concurrent state machines:
- **Monome buttons**: 64 buttons, each with level (0-15) and state
- **Sequencer state**: stopped/playing/paused
- **Sample playback**: Active shred IDs for concurrent playback
- **Selection recording**: Page-based selection maps

When modifying state, consider all affected components.

### 4. Audio File Requirements
- ChucK's SndBuf expects **mono** WAV files
- Use `split_wave.py` to convert stereo to mono before loading
- Sample paths are referenced by `MonDrumSample` objects

### 5. Persistence Limitations
- `MonDrumDB` class is largely a stub
- Project save/load is minimal
- Selection data is saved as JSON in `moncut.py`
- No unified persistence layer exists

### 6. Python 2.6 Legacy
- Code targets Python 2.6 (see shebang in `split_wave.py`)
- May need updates for Python 3 compatibility
- Uses older PyGTK (not GTK+ 3)

### 7. Testing Approach
- No automated assertions or test frameworks
- Tests rely on:
  - Console output (`<<< ... >>>`)
  - Machine status queries
  - Time-based execution
  - Manual verification of audio output

### 8. Configuration Spread
OSC parameters, grid dimensions, and control mappings are hardcoded across multiple files:
- `test/lib/test-setup.ck` - OSC ports and hosts
- `util/moncut.py` - Grid layout and button mappings
- `src/mondrum.ck` - Internal defaults

Consider centralizing configuration if making significant changes.

## Common Tasks Guide

### Adding a New Sample
```chuck
MonDrumSample sample;
sample.init(mondrum, "/path/to/mono.wav");
program.set_sample(slot_number, sample);
```

### Creating a Sequence Track
```chuck
MonDrumSequenceTrack track;
track.init(mondrum, program_reference);
sequence.add_track(track_number, track);
```

### Modifying Monome Button Behavior
1. Locate button in `Monome.init()` or `MonomeButton` array
2. Modify `key_event_manager()` callback
3. Update LED feedback with `set_level()`

### Adding New OSC Messages
1. Define message format in sender (ChucK or Python)
2. Add receiver handler in opposite end
3. Update `doc/monome_osc_protocol.txt` if protocol change

### Debugging Tips
- Use `<<< "debug message" >>>` in ChucK for console output
- Check `Machine.status()` for active shred count
- Monitor OSC traffic with OSC debugging tools
- Use `mock_osc_gtk.py` to test without hardware
- Run tests individually to isolate issues

## Git Workflow

### Submodules
```bash
# Initialize submodules
git submodule update --init --recursive

# Update submodules
git submodule update --remote
```

### Branching Convention
- Feature branches: `claude/add-feature-name-XXXXX`
- Always develop on designated branch
- Commit with clear, descriptive messages

## Known Issues and Limitations

1. **Database stub**: `MonDrumDB` is not fully implemented
2. **No config files**: All configuration is hardcoded
3. **Limited documentation**: Main code has minimal comments
4. **Python 2 only**: Not Python 3 compatible
5. **No error handling**: ChucK failures are silent
6. **Memory management**: No explicit cleanup of LiSa buffers
7. **Port conflicts**: Multiple OSC ports must be coordinated

## Future Enhancement Areas

Based on code analysis, these areas would benefit from improvement:
- Configuration file system (YAML/JSON for OSC ports, paths)
- Full implementation of `MonDrumDB` for project persistence
- Python 3 migration
- Comprehensive error handling and logging
- Automated test assertions
- Code documentation and inline comments
- Centralized control mapping configuration
- UI/UX improvements in GTK interfaces

## Resources

- **ChucK Documentation**: https://chuck.cs.princeton.edu/
- **Monome Documentation**: https://monome.org/docs/
- **OSC Protocol**: See `doc/monome_osc_protocol.txt`
- **Scalpel**: GTK sound editor (separate project)

## Quick Reference: File Locations

| Task | File Path |
|------|-----------|
| Main application | `src/mondrum.ck` |
| Test factory | `test/lib/test-setup.ck` |
| Sample editing GUI | `util/moncut.py` |
| Sequencer tests | `test/tests/mondrum_sequencer.ck` |
| OSC protocol docs | `doc/monome_osc_protocol.txt` |
| Test runner | `test/run.sh` |

---

**Document Version**: 1.0
**Last Updated**: 2026-01-04
**Codebase Stats**: ~1,200 LOC, 15+ classes, 7 ChucK files, 3 Python files
