# Homebrew Tap Setup

To distribute `trinity` via Homebrew, create a tap repository:

## 1. Create the tap repo

Create `abilityai/homebrew-tap` on GitHub, then copy `trinity-cli.rb` into it:

```
homebrew-tap/
└── Formula/
    └── trinity-cli.rb
```

## 2. Update the formula

After each PyPI release, update the `url` version and `sha256`:

```bash
# Get the sha256 of the new release
curl -sL https://files.pythonhosted.org/packages/source/t/trinity-cli/trinity_cli-VERSION.tar.gz | shasum -a 256
```

## 3. Users install with

```bash
brew tap abilityai/tap
brew install trinity-cli
```

Or as a one-liner:

```bash
brew install abilityai/tap/trinity-cli
```
