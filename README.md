# Aether

*A portable semantic programming language with multi-backend transpilation.*

```
Aether → Python
       → C++
       → JavaScript
       → Rust
       → ...
```

Aether is an experimental programming language focused on:

- semantic portability,
- extensible compiler infrastructure,
- multi-target transpilation,
- structured syntax,
- and AI-assisted code generation workflows.

Unlike traditional transpilers that only transform syntax, Aether is designed around a stable parser and AST architecture that can evolve into a backend-independent semantic layer.

---

## Philosophy

Aether is not intended to replace existing ecosystems.

Instead, it acts as:
```
One language
→ many targets
→ shared semantics
→ portable logic
```

The goal is to write high-level program logic once and transpile it into multiple implementation languages with minimal adaptation.

---

## Example

### Aether

```
function fibonacci(n: int) -> int {
    if n <= 1 {
        return n;
    }

    return fibonacci(n - 1)
         + fibonacci(n - 2);
}

values = [];

for value in range(10) {
    values.append(
        fibonacci(value)
    );
}

print(values);
```

---

### Python Output

```python
def fibonacci(n: int) -> int:
    if n <= 1:
        return n

    return fibonacci(n - 1) + fibonacci(n - 2)

values = []

for value in range(10):
    values.append(fibonacci(value))

print(values)
```

---

## Features

- Recursive descent parser
- AST-driven compilation
- Python transpilation backend
- Extensible lexer/parser architecture
- Function declarations
- Expressions and operator precedence
- Member access and chained calls
- Typed declarations
- Blocks and structured control flow
- Backend-oriented compiler design

---

## Architecture

```
Source
↓
Lexer
↓
Parser
↓
AST
↓
Transpiler Backend
↓
Target Language
```

Future plans include:

```
AST
↓
Semantic IR
↓
Optimization Passes
↓
Backend Lowering
↓
Target Emission
```

---

## Why Aether Exists

Most transpiled languages focus primarily on syntax improvements.

Aether instead focuses on:

- semantic portability,
- compiler infrastructure,
- transformability,
- and backend abstraction.

The long-term goal is to support:

- multiple target languages,
- backend-independent tooling,
- AI-oriented program generation,
- static analysis,
- optimization passes,
- and potentially self-hosting compilation.

---

## Goals

- Portable semantics
- Stable AST infrastructure
- Extensible transpilation
- Backend abstraction
- Tooling-friendly architecture
- AI-compatible intermediate representation

---

## Non-Goals

Currently, Aether is **not** focused on:

- raw runtime performance,
- replacing existing ecosystems,
- production-ready compilation,
- low-level systems programming.

---

## Example Usage

### Build

```
python lang.py build example.txt
```

---

### Run

```
python lang.py run example.ae
```

---

## Project Status

Aether is currently experimental and under active architectural development.

The compiler pipeline already includes:

- lexing,
- parsing,
- AST generation,
- and Python transpilation.

Future work includes:

- semantic analysis,
- intermediate representations,
- multi-backend support,
- optimization passes,
- and source mapping.

---

## Vision

Aether explores the idea that:

> program logic should outlive implementation languages

Instead of writing separate implementations for different runtimes, Aether aims to provide a portable semantic layer that can adapt to multiple targets.

---

## License

MIT License