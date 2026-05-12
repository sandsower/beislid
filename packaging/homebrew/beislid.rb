# Draft Homebrew formula for Beislið.
#
# This file is packaging guidance, not the published install path yet.
# Full Homebrew support is tracked in https://github.com/sandsower/beislid/issues/67.

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

    libexec.install "bin"
    libexec.install "skills"
    libexec.install "hooks"
    libexec.install "extensions"
    (libexec/"scripts").install "scripts/install_lib.sh"

    bin.install_symlink libexec/"bin/beislid" => "beislid"
  end

  def caveats
    <<~EOS
      This is a draft formula kept in the Beislið repo for packaging validation.
      Full Homebrew support, including publishing and upgrade policy, is tracked in #67.

      The formula installs Beislið's runtime files under libexec and exposes `beislid` on PATH.
      If you move or manually copy the runtime, set BEISLID_HOME to the runtime root.
    EOS
  end

  test do
    assert_match "Beislið CLI", shell_output("#{bin}/beislid help")
    assert_match "beislid status", shell_output("#{bin}/beislid --status 2>&1", 2)
  end
end
