"""Live per-stage progress, rendered into a single GitHub issue comment.

The workflow creates a comment up front and passes its id in via env
(PROGRESS_COMMENT_ID); this module edits that comment as each stage moves
through pending -> running -> done/failed. A no-op when the env isn't set
(e.g. local CLI runs), so the pipeline behaves identically offline.
"""

import os
import requests

_ICON = {
    "pending": "⬜",
    "running": "🔄",
    "done": "✅",
    "failed": "❌",
    "skipped": "➖",
}


class Progress:
    def __init__(self, steps: list[tuple[str, str]]):
        # steps: ordered [(key, label), ...]
        self.steps = [{"key": k, "label": l, "status": "pending"} for k, l in steps]
        self.repo = os.environ.get("GH_REPO", "").strip()
        self.token = os.environ.get("GH_TOKEN", "").strip()
        self.comment_id = os.environ.get("PROGRESS_COMMENT_ID", "").strip()
        self.run_url = os.environ.get("RUN_URL", "").strip()
        self.enabled = bool(self.repo and self.token and self.comment_id)
        self._header = "**Generating your content…**"

    def begin(self) -> None:
        self._push()

    def set(self, key: str, status: str) -> None:
        for s in self.steps:
            if s["key"] == key:
                s["status"] = status
        self._push()

    def done(self, had_errors: bool) -> None:
        self._header = (
            "⚠️ **Finished with errors** — see the failed step below."
            if had_errors else "✅ **All done.**"
        )
        self._push()

    def _body(self) -> str:
        lines = [self._header, ""]
        for s in self.steps:
            note = " _(skipped)_" if s["status"] == "skipped" else ""
            lines.append(f"{_ICON.get(s['status'], '⬜')} {s['label']}{note}")
        if self.run_url:
            lines += ["", f"[Watch live progress]({self.run_url})"]
        return "\n".join(lines)

    def _push(self) -> None:
        if not self.enabled:
            return
        try:
            r = requests.patch(
                f"https://api.github.com/repos/{self.repo}/issues/comments/{self.comment_id}",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                },
                json={"body": self._body()},
                timeout=15,
            )
            if r.status_code >= 300:
                print(f"  (progress update HTTP {r.status_code})")
        except Exception as e:  # never let a status update break the run
            print(f"  (progress update failed: {e})")
