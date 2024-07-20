# Contributing to Ceylon Multi-Agent System (MAS)

Thank you for your interest in contributing to the Ceylon AI Multi-Agent System (MAS) project! We welcome contributions from the community to help make this project better. Below are some guidelines to help you get started.

## Table of Contents

1. [How to Contribute](#how-to-contribute)
2. [Code of Conduct](#code-of-conduct)
3. [Development Setup](#development-setup)
4. [Submitting Changes](#submitting-changes)
5. [Style Guides](#style-guides)
6. [Developer Guidelines](#developer-guidelines)
   - [Rust Development](#rust-development)
   - [Python Development](#python-development)

## How to Contribute

1. **Fork the repository**: Click the 'Fork' button at the top right corner of the repository page.
2. **Clone your fork**: 
   ```bash
   git clone https://github.com/ceylonai/ceylon
   cd ceylon
   ```
3. **Create a branch**:
   ```bash
   git checkout -b your-feature-branch
   ```
4. **Make your changes**: Develop your feature or fix.
5. **Commit your changes**:
   ```bash
   git commit -m "Description of your changes"
   ```
6. **Push to your fork**:
   ```bash
   git push origin your-feature-branch
   ```
7. **Create a pull request**: Go to the repository page on GitHub and click 'New pull request'.

## Code of Conduct

Please note that this project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Development Setup

### Prerequisites

- [Rust](https://www.rust-lang.org/tools/install)
- [Python](https://www.python.org/downloads/)

### Steps

1. Install dependencies for Rust and Python projects.
2. Follow the [Rust Development](#rust-development) and [Python Development](#python-development) guidelines below for detailed setup instructions.

## Submitting Changes

- Ensure that your code adheres to the project's style guides.
- Write clear and descriptive commit messages.
- Include tests for new features or bug fixes.
- Ensure that all tests pass before submitting a pull request.

## Style Guides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature").
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...").
- Limit the first line to 72 characters or less.

### Rust Style Guide

- Follow the [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/).
- Ensure your code is formatted using `rustfmt`.
- Use `clippy` to check for common mistakes and improve code quality.

### Python Style Guide

- Follow [PEP 8](https://pep8.org/).
- Ensure your code is formatted using `black`.
- Use `flake8` to check for common mistakes and improve code quality.

## Developer Guidelines

### Rust Development

1. **Setup**
    - Install Rust:
      ```bash
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
      ```
    - Add required components:
      ```bash
      rustup component add clippy rustfmt
      ```

2. **Building the Project**
   ```bash
   cargo build
   ```

3. **Running Tests**
   ```bash
   cargo test
   ```

4. **Linting and Formatting**
    - Format your code:
      ```bash
      cargo fmt
      ```
    - Run clippy for lint checks:
      ```bash
      cargo clippy
      ```

### Python Development

1. **Setup**
    - Install Python dependencies:
      ```bash
      pip install -r requirements.txt
      ```

2. **Running the Project**
   ```bash
   python main.py
   ```

3. **Running Tests**
   ```bash
   pytest
   ```

4. **Linting and Formatting**
    - Format your code:
      ```bash
      black .
      ```
    - Run flake8 for lint checks:
      ```bash
      flake8
      ```

Thank you for contributing to the Ceylon: Multi-Agent System (MAS) project!