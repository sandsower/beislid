# Homebrew formula for Beislið.
#
# This file is the source of truth for Homebrew packaging.

class Beislid < Formula
  desc "Opinionated workflow skills and CLI for coding agents"
  homepage "https://github.com/sandsower/beislid"
  license "MIT"
  head "https://github.com/sandsower/beislid.git", branch: "main"

  def install
    libexec.install "install.sh"
    libexec.install "package.json"
    libexec.install ".claude-plugin"
    libexec.install "README.md"
    libexec.install "LICENSE"
    libexec.install "NOTICE.md"
    libexec.install ".beislid"

    libexec.install "bin"
    libexec.install "skills"
    libexec.install "hooks"
    libexec.install "extensions"
    (libexec/"scripts").install "scripts/install_lib.sh"
    (libexec/"scripts").install "scripts/run_ledger.py"
    (libexec/"scripts").install "scripts/action_policy.py"
    (libexec/"scripts").install "scripts/validate_export.py"
    (libexec/"scripts").install "scripts/visual_feedback.py"

    bin.install_symlink libexec/"bin/beislid" => "beislid"
  end

  def caveats
    <<~EOS
      Homebrew installs Beislið's runtime files under libexec and exposes `beislid` on PATH.
      Use `brew upgrade beislid` for Homebrew-managed updates. `beislid update` is for source-checkout installs.

      If you move or manually copy the runtime, set BEISLID_HOME to the runtime root.
    EOS
  end

  test do
    assert_match "Beislið CLI", shell_output("#{bin}/beislid help")
    assert_match "beislid status", shell_output("#{bin}/beislid status")
    assert_match "Version stamp", (libexec/".beislid/workflow-md-format.md").read
  end
end
