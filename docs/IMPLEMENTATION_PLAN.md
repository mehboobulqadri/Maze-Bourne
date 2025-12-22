# Maze Bourne - Phase-by-Phase Implementation Plan

**Goal**: Transform Maze Bourne into a robust, polished, and enjoyable stealth game following best practices

---

## PHASE 0: CRITICAL HOTFIXES (Est: 2-4 hours)

**Goal**: Fix game-breaking bugs that prevent proper gameplay

### Tasks:

#### 0.1 Fix Menu Button Overlap ✅ CRITICAL
- **File**: `src/core/game.py:430-447`
- **Action**: Adjust button Y positions so no overlap
- **Testing**: Launch game, verify all menu buttons clickable

#### 0.2 Remove Duplicate Method Definitions ✅ CRITICAL
- **Files**: 
  - `src/entities/player.py:171, 384` (take_damage)
  - `src/entities/enemy.py:103, 162` (update)
  - `src/graphics/renderer.py:689, 1384` (_render_debug)
- **Action**: Merge implementations, keep best version
- **Testing**: Play a level, ensure no AttributeErrors

#### 0.3 Fix Missing Sound Reference ✅ CRITICAL
- **File**: `src/entities/player.py:329`
- **Action**: Change "sfx_pickup" to "sfx_ui_select" or create missing file
- **Testing**: Collect key, verify sound plays

#### 0.4 Remove Debug Print Statements ✅
- **File**: `src/entities/player.py:382`
- **Action**: Remove all production `print()` calls
- **Testing**: Play game, no console spam

#### 0.5 Initialize Missing Attributes ✅ CRITICAL
- **File**: `src/levels/maze_generator.py:96`
- **Action**: Add `self.boss_button_positions = []` in __init__
- **Testing**: Load endless level, no AttributeError

#### 0.6 Fix Pathfinding Cache Leak ✅
- **File**: `src/ai/pathfinding.py:30-31`
- **Action**: Add cache size limit and clear on level change
- **Testing**: Play multiple levels, monitor memory usage

**Verification**: Game runs without crashes, all menu buttons work, no obvious bugs

---

## PHASE 1: CODE CLEANUP & STABILITY (Est: 1-2 days)

**Goal**: Clean up code quality issues and add basic error handling

### 1.1 Error Handling Infrastructure

#### 1.1.1 Add Logging System
- Create `src/core/logger.py`
- Replace all `print()` with proper logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- File output for debugging

#### 1.1.2 Wrap Critical Sections
- Try-except around file operations
- Asset loading error handling
- Level generation validation
- Save/load error recovery

### 1.2 Code Organization

#### 1.2.1 Extract Constants
- Move hardcoded values to `constants.py`
- Document constant relationships
- Add validation for dependent constants

#### 1.2.2 Remove Duplicate Code
- Extract vision cone logic to utility
- Create shared collision detection
- Centralize path reconstruction

#### 1.2.3 Add Type Hints
- Add type hints to all public methods
- Use `typing` module properly
- Run mypy for validation

### 1.3 Input System Cleanup

#### 1.3.1 Create Input Manager
- `src/core/input_manager.py`
- Centralize input handling
- Support key rebinding
- Abstract input from game logic

### 1.4 Basic Testing Setup

#### 1.4.1 Create Test Framework
- Set up pytest
- Create `tests/` directory
- Add basic unit tests for critical functions

#### 1.4.2 Integration Tests
- Test level loading
- Test save/load
- Test basic gameplay loop

**Verification**: Code passes linting, basic tests pass, logging works

---

## PHASE 2: COMPLETE CORE FEATURES (Est: 3-4 days)

**Goal**: Finish half-implemented game mechanics

### 2.1 Hiding Spot Mechanics

#### 2.1.1 Player Interaction
- Add `enter_hiding_spot()` method to Player
- Add `exit_hiding_spot()` method to Player
- Handle `is_hidden` state properly
- Disable movement while hidden

#### 2.1.2 Enemy Behavior
- Enemies can't see hidden player
- Add "check hiding spots" behavior to enemies
- Search patterns around hiding spots

#### 2.1.3 Visual Feedback
- Darken screen when hidden
- Show prompt to exit hiding spot
- Animation for enter/exit

### 2.2 Security Camera System

#### 2.2.1 Integration
- Add cameras to GameObjectManager
- Spawn cameras from level data
- Update cameras in game loop

#### 2.2.2 Alarm System
- Trigger alarm when player detected
- Alert nearby enemies
- Visual/audio feedback

#### 2.2.3 Rendering
- Draw camera sprites
- Show vision cone
- Indicate detection state

### 2.3 Lever System

#### 2.3.1 Level Design
- Add levers to campaign levels
- Create lever-door pairs
- Design puzzles around levers

#### 2.3.2 Functionality
- Test lever-door linking
- Add lever-camera linking
- Visual feedback for lever state

### 2.4 Trap Improvements

#### 2.4.1 Visual Indicators
- Show trap state (active/inactive)
- Add particle effects
- Pulsing animation for active traps

#### 2.4.2 Trap Variety
- Timer-based traps
- Pressure plate traps
- Laser traps

### 2.5 Privacy Door System

#### 2.5.1 Fix Logic
- Separate from regular doors in data structures
- Fix collision handling
- Ensure proper vision blocking

#### 2.5.2 UI Feedback
- Show door state
- Interaction prompt
- Auto-close warning

### 2.6 Parry System

#### 2.6.1 Player-Enemy Integration
- Detect parry timing against enemy attacks
- Stun enemy on successful parry
- Reward with invulnerability frames

#### 2.6.2 Visual/Audio Feedback
- Screen flash on successful parry
- Unique sound effect
- Particle effect
- Add UI indicator for parry cooldown

**Verification**: All core mechanics work and feel good

---

## PHASE 3: BOSS BATTLES (Est: 2-3 days)

**Goal**: Complete and polish boss encounter system

### 3.1 Boss Implementation

#### 3.1.1 Boss Arena Generation
- Fix `_generate_boss_arena()` method
- Create proper arena layout
- Place boss buttons correctly
- Add visual flair to arena

#### 3.1.2 Boss AI
- Implement attack patterns
- Add phase transitions
- Pattern recognition
- Defeat condition

#### 3.1.3 Boss Button Mechanics
- Spawn buttons in arena
- Link buttons to boss health/shield
- Visual feedback for activation
- Sequential activation logic

### 3.2 Boss Encounter Flow

#### 3.2.1 Encounter Transition
- Boss warning screen
- Fade to boss arena
- Boss introduction animation
- UI changes for boss fight

#### 3.2.2 Victory/Defeat
- Boss defeat animation
- Victory screen
- Rewards
- Return to endless mode

### 3.3 Boss Types

#### 3.3.1 Create Multiple Boss Variants
- Speed boss (fast, erratic movement)
- Tank boss (slow, high health, AOE)
- Stealth boss (cloaking, ambush)
- Minion summoner boss

**Verification**: Boss fights are challenging and fair

---

## PHASE 4: AI & DIFFICULTY (Est: 3-4 days)

**Goal**: Make AI adaptive and engaging

### 4.1 Enemy AI Improvements

#### 4.1.1 State Machine Refactor
- Extract state logic into separate classes
- Implement proper State pattern
- Add state transition events

#### 4.1.2 Behavior Polish
- Smarter pathfinding decisions
- Group coordination
- Flanking behavior
- Investigation routines

#### 4.1.3 Performance Optimization
- Spatial partitioning for enemy updates
- Update enemies based on distance to player
- Cache visibility calculations

### 4.2 Director System

#### 4.2.1 Activate Adaptive Difficulty
- Track player performance in real-time
- Adjust enemy stats dynamically
- Spawn rate adjustment
- Resource availability scaling

#### 4.2.2 Difficulty Metrics
- Death frequency
- Time in stealth
- Damage taken
- Keys collected vs attempts

### 4.3 Player Behavior Tracker

#### 4.3.1 Implement Tracking
- Record player movement patterns
- Track favorite paths
- Identify player weaknesses
- Build heatmaps

#### 4.3.2 AI Response
- Place enemies on common routes
- Set ambushes at choke points
- Adapt patrol routes

### 4.4 Strategist System

#### 4.4.1 Enemy Coordination
- Implement enemy communication
- Coordinated search patterns
- Pincer movements
- Alert propagation

#### 4.4.2 Strategic Decisions
- When to pursue vs patrol
- Resource allocation
- Trap activation timing

**Verification**: AI feels intelligent and challenging but fair

---

## PHASE 5: PROGRESSION & POLISH (Est: 3-4 days)

**Goal**: Add progression systems and polish gameplay

### 5.1 Save System

#### 5.1.1 Campaign Progress
- Save completed levels
- Save best times
- Save star ratings
- Resume from last level

#### 5.1.2 Endless Mode Progress
- Save high scores
- Save reached floors
- Save unlocks

#### 5.1.3 Settings Persistence
- Save control bindings
- Save audio settings
- Save display settings

### 5.2 Tutorial System

#### 5.2.1 Interactive Tutorial
- Create tutorial level
- Step-by-step instructions
- Practice areas for each mechanic
- Skip option for experienced players

#### 5.2.2 Contextual Help
- Show control prompts
- Ability cooldown indicators
- First-time hints

### 5.3 Feedback Systems

#### 5.3.1 Visual Feedback
- Detection meter UI
- Stealth indicator
- Enemy awareness visualization
- Screen effects for states

#### 5.3.2 Audio Feedback
- Create/add missing sounds
- Ambient audio
- Musical stings for events
- Proximity audio cues

#### 5.3.3 Haptic Feedback (Optional)
- Controller rumble support
- Different patterns for events

### 5.4 UI/UX Improvements

#### 5.4.1 Menu System
- Keyboard navigation
- Mouse hover effects
- Smooth transitions
- Consistent styling

#### 5.4.2 HUD
- Minimap
- Ability cooldown indicators
- Health/energy bars polish
- Objective tracker

#### 5.4.3 Pause Menu
- Resume
- Restart level
- Settings shortcut
- Quit confirmation

### 5.5 Level Design

#### 5.5.1 Campaign Polish
- Review all 10 levels
- Smooth difficulty curve
- Introduce mechanics gradually
- Add secrets/optional challenges

#### 5.5.2 Endless Mode Balance
- Difficulty scaling formula
- Enemy variety progression
- Boss frequency tuning
- Reward scaling

**Verification**: Game feels polished and complete

---

## PHASE 6: VISUAL EFFECTS (Est: 2-3 days)

**Goal**: Add juice and visual appeal

### 6.1 Particle System Enhancement

#### 6.1.1 More Particle Types
- Dust clouds for movement
- Sparks for interactions
- Bullet time effects for dash
- Death particles for enemies

#### 6.1.2 Particle Pooling
- Implement object pooling
- Limit particle count
- Performance optimization

### 6.2 Screen Effects

#### 6.2.1 Transitions
- Fade in/out between states
- Wipe transitions between levels
- Smooth scene changes

#### 6.2.2 Post-Processing
- Stealth mode visual filter
- Damage vignette
- Alert flash effects
- Color grading per state

### 6.3 Animation Polish

#### 6.3.1 Player Animations
- Smooth movement interpolation
- Dash trail effect
- Stealth crouch visual
- Parry animation

#### 6.3.2 Enemy Animations
- Patrol cycle
- Alert animation
- Death animation
- Stun effect

#### 6.3.3 Object Animations
- Door opening/closing
- Lever pull
- Key spin
- Trap activation

### 6.4 Lighting Effects (Optional)

#### 6.4.1 Dynamic Lighting
- Player flashlight
- Enemy spotlights
- Environmental lighting
- Shadows

**Verification**: Game looks appealing and professional

---

## PHASE 7: AUDIO SYSTEM (Est: 2-3 days)

**Goal**: Complete audio experience

### 7.1 Sound Effects

#### 7.1.1 Create/Source Missing Sounds
- Pickup sounds
- Parry impact
- Camera alarm
- Lever switch
- Door sounds
- Boss sounds

#### 7.1.2 Spatial Audio
- 3D audio positioning
- Volume based on distance
- Panning based on direction

### 7.2 Music System

#### 7.2.1 Music Tracks
- Menu theme
- Gameplay ambience
- Alert music
- Boss battle theme
- Victory jingle

#### 7.2.2 Dynamic Music
- Smooth transitions between tracks
- Intensity layers for stealth/alert
- Silence for tension

### 7.3 Procedural Audio (Optional)

#### 7.3.1 Implement Music Generator
- Generative ambient tracks
- Reactive to gameplay
- Endless variation

**Verification**: Audio enhances gameplay experience

---

## PHASE 8: RL INTEGRATION (Est: 2-3 days)

**Goal**: Make RL training actually useful

### 8.1 Training Pipeline

#### 8.1.1 Connect Training to Game
- Button to watch trained agent
- Real-time training mode
- Model selection UI

#### 8.1.2 Model Management
- Save/load trained models
- Model performance metrics
- A/B testing different agents

### 8.2 RL Enemy Mode

#### 8.2.1 RL-Controlled Enemies
- Use trained model for enemy decisions
- Adaptive enemy type
- Difficulty scaling with RL

#### 8.2.2 Competitive Mode (Optional)
- Player vs RL agent races
- Leaderboard against AI

**Verification**: RL adds value to gameplay

---

## PHASE 9: PERFORMANCE OPTIMIZATION (Est: 2-3 days)

**Goal**: Ensure smooth 144 FPS gameplay

### 9.1 Rendering Optimization

#### 9.1.1 Culling
- Frustum culling
- Occlusion culling
- LOD for distant objects

#### 9.1.2 Batching
- Batch draw calls
- Sprite atlases
- Dirty rectangle rendering

### 9.2 AI Optimization

#### 9.2.1 Spatial Partitioning
- Quadtree for entities
- Only update nearby enemies
- Smart FOV updates

#### 9.2.2 Pathfinding Optimization
- Jump Point Search
- Hierarchical pathfinding
- Path smoothing
- Asynchronous pathfinding

### 9.3 Memory Management

#### 9.3.1 Object Pooling
- Pool particles
- Pool projectiles (if added)
- Pool enemies (respawn)

#### 9.3.2 Asset Management
- Unload unused assets
- Lazy loading
- Asset preloading for level

### 9.4 Profiling

#### 9.4.1 Performance Metrics
- Frame time breakdown
- Memory usage tracking
- Bottleneck identification
- FPS stability analysis

**Verification**: Consistent 144 FPS, low memory usage

---

## PHASE 10: ACCESSIBILITY & POLISH (Est: 2-3 days)

**Goal**: Make game accessible and polished

### 10.1 Accessibility Features

#### 10.1.1 Visual Accessibility
- Colorblind modes
- High contrast mode
- Adjustable UI scale
- Font size options

#### 10.1.2 Audio Accessibility
- Visual indicators for sounds
- Subtitle system (if dialogue added)
- Audio cues for visual events

#### 10.1.3 Control Accessibility
- Remappable controls
- Alternative control schemes
- One-handed mode support
- Difficulty presets

### 10.2 Settings Menu

#### 10.2.1 Comprehensive Settings
- Graphics quality options
- Audio mixing (master, SFX, music separately)
- Gameplay tweaks
- Accessibility options
- Stats and achievements page

### 10.3 Credits & About

#### 10.3.1 Proper Credits Screen
- Developer credits
- Asset attribution
- Library credits
- Thank you notes

### 10.4 Final Polish Pass

#### 10.4.1 Bug Bash
- Play through entire game
- Fix all found bugs
- Test edge cases

#### 10.4.2 Balance Pass
- Tune all difficulty values
- Test pacing
- Collect playtest feedback

#### 10.4.3 Localization Prep (Optional)
- Extract all strings
- Prepare for translation
- UI layout for longer text

**Verification**: Game is accessible and polished

---

## PHASE 11: ARCHITECTURE REFACTOR (Est: 4-5 days)

**Goal**: Improve code architecture for maintainability

### 11.1 Game Class Refactor

#### 11.1.1 Split Into Managers
- Extract `StateManager`
- Extract `SceneManager`
- Extract `UIManager`
- Keep Game as coordinator only

### 11.2 Event System

#### 11.2.1 Implement Event Bus
- Create `src/core/events.py`
- Pub-sub pattern
- Event types enum
- Decouple systems

### 11.3 Entity Component System (Optional)

#### 11.3.1 ECS Architecture
- Component classes
- System classes
- Entity manager
- Gradual migration

### 11.4 Dependency Injection

#### 11.4.1 Service Locator
- Create service registry
- Inject dependencies
- Improve testability

**Verification**: Code is maintainable and testable

---

## PHASE 12: ADVANCED FEATURES (Est: 3-5 days)

**Goal**: Add advanced optional features

### 12.1 Endless Mode Enhancements

#### 12.1.1 Meta Progression
- Permanent upgrades
- Unlockable abilities
- Character customization

#### 12.1.2 Modifiers
- Daily challenges
- Mutators
- Special conditions

### 12.2 Multiplayer (Optional, Ambitious)

#### 12.2.1 Local Co-op
- Split-screen
- Shared screen
- Cooperative gameplay

#### 12.2.2 Online Leaderboards
- High score submission
- Time trial rankings
- Daily/weekly challenges

### 12.3 Level Editor Enhancements

#### 12.3.1 Full Editor
- Improve editor UI
- Terrain painting
- Object placement
- Enemy scripting
- Save/load custom levels
- Share levels (export/import)

#### 12.3.2 Community Features
- Level sharing
- Voting system
- Featured levels

### 12.4 Replay System

#### 12.4.1 Record Gameplay
- Record inputs
- Replay playback
- Ghost races

### 12.5 Speedrun Features

#### 12.5.1 Speedrun Mode
- In-game timer
- Segment timing
- Best segments tracking
- Comparison ghost

**Verification**: Advanced features work and add depth

---

## PHASE 13: DOCUMENTATION & RELEASE (Est: 2-3 days)

**Goal**: Prepare for release

### 13.1 Documentation

#### 13.1.1 Code Documentation
- Complete all docstrings
- Architecture documentation
- API documentation
- Generate docs with Sphinx

#### 13.1.2 User Documentation
- Complete README
- Gameplay guide
- FAQ
- Troubleshooting guide

#### 13.1.3 Developer Documentation
- Setup guide
- Contributing guidelines
- Code style guide
- Building instructions

### 13.2 Distribution

#### 13.2.1 Packaging
- Create executable builds
- Windows installer
- Cross-platform builds
- Version management

#### 13.2.2 Release Checklist
- Version number
- Changelog
- Release notes
- Marketing materials

### 13.3 Community

#### 13.3.1 GitHub Presence
- Clean up repository
- Add LICENSE
- Create issue templates
- Set up discussions

#### 13.3.2 Itch.io Page (or Steam)
- Game page
- Screenshots
- Trailer video
- Description

**Verification**: Ready for public release

---

## TESTING CHECKLIST (After Each Phase)

### Smoke Tests
- [ ] Game launches without errors
- [ ] Main menu functional
- [ ] Can start and complete a level
- [ ] No crashes during normal play

### Regression Tests
- [ ] Previous features still work
- [ ] No performance degradation
- [ ] Settings persist
- [ ] Saves load correctly

### Integration Tests
- [ ] New features integrate with existing systems
- [ ] No conflicts between systems
- [ ] Consistent behavior across game

---

## ESTIMATED TIMELINE

**Phase 0**: 0.5 days  
**Phase 1**: 2 days  
**Phase 2**: 4 days  
**Phase 3**: 3 days  
**Phase 4**: 4 days  
**Phase 5**: 4 days  
**Phase 6**: 3 days  
**Phase 7**: 3 days  
**Phase 8**: 3 days  
**Phase 9**: 3 days  
**Phase 10**: 3 days  
**Phase 11**: 5 days  
**Phase 12**: 5 days (optional)  
**Phase 13**: 3 days  

**Total**: 45 days (9 weeks) of focused development
**With Optional Features**: 50 days (10 weeks)

---

## SUCCESS METRICS

### Technical Metrics
- [ ] Zero critical bugs
- [ ] 144 FPS maintained
- [ ] Memory usage < 500MB
- [ ] Load times < 3 seconds
- [ ] No crashes in 1 hour playtime

### Gameplay Metrics
- [ ] Tutorial completion rate > 80%
- [ ] Average session length > 30 minutes
- [ ] Level completion rate > 60%
- [ ] Player retention (return in 7 days) > 40%

### Quality Metrics
- [ ] Code coverage > 70%
- [ ] All linting passes
- [ ] Documentation complete
- [ ] No TODO/FIXME in production code

---

## RISK MITIGATION

### Identified Risks
1. **Scope Creep**: Stick to plan, defer non-critical features
2. **Time Overrun**: Build in 20% buffer, prioritize ruthlessly
3. **Technical Debt**: Refactor early, don't defer cleanup
4. **Performance Issues**: Profile early and often
5. **Design Changes**: Lock design document, changes go through review

### Mitigation Strategies
- Daily progress tracking
- Weekly playtesting
- Bi-weekly code review
- Automated testing
- Feature freeze before polish phase

---

## MAINTENANCE PLAN (Post-Launch)

### Week 1-2: Critical Bugs
- Monitor crash reports
- Fix game-breaking bugs
- Hotfix releases

### Month 1: Community Feedback
- Address common complaints
- Balance adjustments
- QOL improvements

### Month 2-3: Content Updates
- New levels
- New enemies
- New mechanics

### Month 4+: Long-term Support
- Seasonal events
- Community features
- Continued balance

---

## NOTES

- Each phase should end with working, tested, integrated code
- Don't move to next phase with known critical bugs
- Playtest after every major change
- Keep a changelog
- Commit frequently with clear messages
- Tag releases properly
- Maintain backward compatibility for saves

**Remember**: Quality over quantity. A polished, small game beats a buggy large one.
