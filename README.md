# Vibe Language

**The language humans enjoy and AI understands.**

Vibe is a compiled, statically-typed programming language designed for human-AI collaboration in software engineering. It combines Rust's safety guarantees, Go's simplicity, and Nim's expressiveness with native AI-readable metadata.

## Features

- **Safety by Default** - Bounds checking, overflow protection, safe strings
- **Simplicity First** - Small language surface, easy to learn
- **Expressive** - Minimal boilerplate, powerful abstractions
- **AI-Native** - Metadata, semantic indexing, agent collaboration built-in
- **Performant** - Compiles to native code, no runtime overhead

## Quick Start

```bash
# Clone the repository
git clone https://github.com/vibe-lang/vibe.git
cd vibe

# Run setup
./setup.sh

# Create a new project
vpm init my-project
cd my-project

# Run your project
vibec run src/main.vibe
```

## Example

```vibe
module MyApp

intent:
    Main application entry point

import std.io

proc main() -> int {
    let name = "Vibe Developer"
    std.io.println("Hello, ${name}!")
    return 0
}
```

## Compiler Commands

```bash
# Build to executable
vibec build src/main.vibe

# Run program
vibec run src/main.vibe

# Emit C code
vibec emit-c src/main.vibe

# Analyze code
vibec analyze src/main.vibe

# Run tests
vibec test src/
```

## Package Manager

```bash
# Initialize project
vpm init

# Install package
vpm install sqlite

# Search packages
vpm search "http server"

# List installed
vpm list

# Publish package
vpm publish
```

## AI Metadata

Vibe includes native AI-readable metadata:

```vibe
module WebServer

intent:
    HTTP web server implementation
    Handle REST API requests

owner: backend_team
risk: high

dependencies:
    - http
    - json
    - database

testing:
    unit: 92.5
    integration: 85.0
    threshold: 90
```

## Documentation

- [Language Specification](docs/SPEC.md)
- [Examples](examples/)
- [API Reference](docs/API.md) (coming soon)

## Building from Source

```bash
git clone https://github.com/vibe-lang/vibe.git
cd vibe
python3 src/compiler/vibec.py build src/main.vibe
```

## License

MIT License

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Community

- [Discord](https://discord.gg/vibe-lang)
- [GitHub Discussions](https://github.com/vibe-lang/vibe/discussions)
- [Twitter](https://twitter.com/vibe_lang)

---

**Vibe: The language humans enjoy and AI understands.**
