# Vibe Language Specification v0.1.0

## Overview

Vibe is a compiled, statically-typed programming language designed for human-AI collaboration in software engineering. It combines Rust's safety guarantees, Go's simplicity, and Nim's expressiveness with native AI-readable metadata.

## Design Principles

1. **Safety by Default** - Bounds checking, overflow protection, safe strings
2. **Simplicity First** - Small language surface, easy to learn
3. **Expressive** - Minimal boilerplate, powerful abstractions
4. **AI-Native** - Metadata, semantic indexing, agent collaboration built-in
5. **Performant** - Compiles to native code, no runtime overhead

## Core Philosophy

**Rust gives you:**
- Memory safety
- No null pointer crashes
- Strong type system
- Safe concurrency

**Go gives you:**
- Fast compilation
- Simple syntax
- Easy deployment
- Small language surface

**Nim gives you:**
- Expressive syntax
- Compile-time metaprogramming
- Native binaries
- Performance close to C

**Vibe adds:**
- AI-readable metadata
- Built-in architecture maps
- Semantic code indexing
- Native agent collaboration
- Compiler-assisted code generation
- Self-documenting modules

## What Vibe Should NOT Have

**Avoid:**
- Lifetimes (Rust complexity)
- Macros as complicated as Rust's
- Template hell like C++
- Python-style runtime typing
- Java-style verbosity
- JavaScript quirks

## Syntax Overview

```vibe
# Single-line comment
## Multi-line comment

module MyApplication

intent:
    Main application entry point
    Coordinates all subsystems

owner: engineering_team
risk: medium

import std.io
import std.collections

proc main() -> int {
    let name = "Vibe Developer"
    std.io.println("Hello, ${name}!")
    return 0
}

func add(a: int, b: int) -> int {
    return a + b
}

struct User {
    name: string
    age: int
    email: string
}

enum Color {
    Red
    Green
    Blue
}

func calculate(x: float) -> float {
    if x > 0.0 {
        return x * 2.0
    } else {
        return 0.0
    }
}

spawn process()
await result
```

## Type System

### Primitive Types
- `int` - 64-bit signed integer
- `float` - 64-bit IEEE 754 double
- `bool` - true/false
- `string` - UTF-8 encoded, immutable
- `char` - Unicode code point
- `byte` - 8-bit unsigned
- `void` - No return value

### Compound Types
- Arrays: `[int]`
- Tuples: `(int, string)`
- Maps: `{string: int}`
- Optional: `?int` (None or int)
- Result: `!int` (Error or int)

### User-Defined Types
- `struct` - Product types with named fields
- `enum` - Sum types (tagged unions)
- `trait` - Interface definitions
- `type` - Type aliases

## Ownership Model

Vibe uses automatic reference counting (ARC) with optional ownership annotations:

```vibe
# Default: ARC managed
let data = Data()

# Explicit ownership (for performance-critical code)
let owned data = Data()

# Borrowed reference
func process(data: &Data) {
    # Read-only access
    return data.value
}

# Mutable borrow
func modify(data: &mut Data) {
    data.value = 42
}
```

## Concurrency

```vibe
# Spawn a task
spawn background_task()

# Async/await
let result = await compute_async()

# Channels
let channel = Channel[int]()
spawn producer(channel)
let value = await channel.receive()
```

## Error Handling

```vibe
# Result type
func parse(input: string) -> !int {
    if input.is_valid() {
        return input.to_int()
    } else {
        return Error("Invalid input")
    }
}

# Pattern matching
match result {
    Ok(value) => process(value),
    Error(e) => handle_error(e)
}

# Or operator
let value = parse(input) or 0
```

## AI Metadata

Every module can include structured metadata:

```vibe
module PaymentProcessor

intent:
    Handle payment processing
    Integrate with Stripe API
    Manage billing cycles

owner: payments_team
risk: critical

dependencies:
    - stripe_api
    - user_database
    - notification_service

api_surface:
    - process_payment(amount, currency)
    - refund(transaction_id)
    - get_balance(account_id)

testing:
    unit: 95%
    integration: 80%
    coverage_threshold: 90
```

## Compiler Commands

```bash
# Build
vibec build src/main.vibe

# Run
vibec run src/main.vibe

# Test
vibec test src/

# Release build
vibec release src/main.vibe

# Generate docs
vibec docs src/

# AI analysis
vibec analyze src/
```

## Package Manager

```bash
# Initialize
vpm init

# Install
vpm install sqlite
vpm install web

# Update
vpm update

# Search
vpm search "http server"

# Publish
vpm publish
```

## Memory Safety Features

1. **Bounds checking** - Arrays checked at compile and runtime
2. **Overflow protection** - Arithmetic overflow is a compile error
3. **Safe strings** - UTF-8 validated, no null bytes
4. **Safe arrays** - No dangling pointers
5. **Safe concurrency** - No data races
6. **Optional unsafe** - Explicit blocks for low-level code

## Goal

"The first language designed for autonomous software engineering."

**Vibe: The language humans enjoy and AI understands.**
