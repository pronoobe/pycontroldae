# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-12-17

### Added
- **DAE System Support**: Enhanced support for Differential-Algebraic Equation (DAE) systems with automatic simplification via `structural_simplify`
- **New Examples**:
  - `examples/dae_second_order_system.py` - Double mass-spring-damper system with algebraic constraints
  - `examples/simple_dae_test.py` - Simple RLC circuit DAE system
  - `examples/dae_system_with_ports.py` - Complex electromechanical coupling system
  - `examples/second_order_damping.py` - Second-order systems with different damping ratios
- **Documentation**:
  - Added Example 6 in README.md showcasing DAE systems with algebraic constraints
  - Added Chinese version of Example 6 in README_CN.md
  - Created `DAE_SYSTEM_SUMMARY.md` with comprehensive DAE system guide
  - Created `DATAPROBE_FIX_SUMMARY.md` documenting DataProbe improvements

### Fixed
- **DataProbe Enhancement**: Significantly improved `DataProbe` functionality for DAE systems
  - Fixed Julia variable scope issues in `_extract_probe_data` method
  - Added support for extracting both `unknowns` (differential states) and `observed` (algebraic variables)
  - Implemented multi-strategy variable matching (exact match, name conversion, partial match)
  - Added Python-side fallback mechanism for direct state extraction
  - Improved error messages with actionable suggestions
- **Variable Extraction**: Enhanced variable extraction from simplified DAE systems to handle variables eliminated by `structural_simplify`

### Improved
- **Module Port System**: Ports are now automatically created when using `add_state()`, simplifying module definition
- **Error Handling**: Better error messages and warnings when probe variables cannot be found
- **Code Quality**: Refactored probe extraction code for better maintainability and robustness

### Documentation
- Updated README.md with comprehensive DAE system example
- Updated README_CN.md with Chinese translation of DAE example
- Added detailed comments and docstrings in new example files
- Improved code examples with better explanations

## [0.1.0] - 2024-XX-XX

### Added
- Initial release of pycontroldae
- Core functionality for control system modeling and simulation
- Julia backend integration via ModelingToolkit.jl
- Module-based system construction
- Port-based connection API
- Event system (TimeEvent and ContinuousEvent)
- Data export capabilities (NumPy, pandas, CSV)
- Rich control block library (PID, StateSpace, Step, etc.)
- Power system examples (IEEE 9-bus system)

[0.2.0]: https://github.com/pronoobe/pycontroldae/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pronoobe/pycontroldae/releases/tag/v0.1.0
