# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Prospectio** is a Node.js platform for searching, presenting work, and acquiring clients online. It includes a frontend Dashboard and a background service, intended to run self-hosted on a Raspberry Pi 4B 8GB.

## Stack

- **Runtime:** Node.js with ES modules (`"type": "module"` in package.json)
- **Package manager:** pnpm (v11.1.1+)

## Commands

```bash
pnpm install       # Install dependencies
```

No build, test, or start scripts are defined yet — add them to `package.json` as the project develops.
