# Changelog

All notable changes to this project will be documented in this file.

The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [Unreleased]

### Added 



### Fixed





## [0.0.3] - 2023-01-08

### Improved

- Auto resuming if previous correlation calculations was abruptly interrupted.
- Mixing large and small files - speeds up fingerprint scanning.
- You can now create fingerprint from audio up to 1.5 hours.

### Performance

Set '526 misc files', host 'i3-2120, 8Gb, HDD, Win10', vs 0.0.2.
- Create fingerprints: 151...206 s (0.95...1.29x better).
- Calculate correlations: 13.0558124 s (1.118x better).



## [0.0.2] - 2023-01-03

### Changed

- Now data is dumped into JSON Lines format.

### Improved

- Batches filling up free memory. Now correlations take less computation time.
  If by the beginning of a new calculation cycle there is free memory, then
  part of it is requisitioned. Some memory will always be free, even if app
  have to analyze pairs by 1, killing performance.

### Performance

Set '526 misc files', host 'i3-2120, 8Gb, HDD, Win10', vs 0.0.1.
- Create fingerprints: 195.661795 s (no changes).
- Calculate correlations: 14.601380 s (27.368x better).



## [0.0.1] - 2023-01-31

### Under development

- track downloading;
- track tagging;
- search for duplicates by audio fingerprints among local files.

### Performance

Set '526 misc files', host 'i3-2120, 8Gb, HDD, Win10'.
- Create fingerprints: 195.343067 s.
- Calculate correlations: 335.577205 s.



[unreleased]: https://github.com/okeangel/cometa/compare/v0.0.3...HEAD
[0.0.3]: https://github.com/okeangel/cometa/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/okeangel/cometa/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/okeangel/cometa/releases/tag/v0.0.1