class TrinityCli < Formula
  include Language::Python::Virtualenv

  desc "CLI for the Trinity Autonomous Agent Orchestration Platform"
  homepage "https://github.com/abilityai/trinity"
  url "https://files.pythonhosted.org/packages/source/t/trinity-cli/trinity_cli-0.1.0.tar.gz"
  sha256 "PLACEHOLDER"  # Update with actual sha256 after first PyPI publish
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Usage", shell_output("#{bin}/trinity --help")
  end
end
