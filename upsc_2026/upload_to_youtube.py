"""Upload the v2 UPSC Prelims 2026 GS Paper 1 explainer to YouTube.

Reuses the existing auth + uploader modules under uploader/.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
# OAuth flow + token paths are relative to CWD in uploader.auth
os.chdir(REPO_ROOT)

from uploader.auth import get_youtube_service, get_channel_info  # noqa: E402
from uploader.youtube import upload_video  # noqa: E402

VIDEO_PATH = r"D:\temp\upsc_2026_video_v2\UPSC_Prelims_2026_GS1_AnswerKey_v2_with_intro.mp4"

TITLE = "UPSC Prelims 2026 GS Paper 1 – Complete Answer Key with Explanation (24 May 2026)"

DESCRIPTION = """UPSC Civil Services Preliminary Examination 2026 — General Studies Paper 1, conducted on 24 May 2026 (Set D). This video walks through all 100 questions of GS Paper 1 with the verbatim question text, all four options, the correct answer, and a quick explanation for each.

Use this video to:
• Tally your attempt and estimate your score
• Understand the reasoning behind tricky answers
• Revise key concepts across History, Polity, Economy, Geography, Environment, Sci-Tech and Current Affairs
• Spot disputed questions where the official key may differ

Important note: The official UPSC answer key will be released after the objection window. Some answers in this video may change once the official key is out — always refer to the latest official UPSC release for your final tally.

Topics covered include:
• Ancient, Medieval and Modern History
• Indian Polity & Governance (Constitution, Parliament, Committees)
• Indian Economy (UPI, ONDC, MPI, NBFCs, Bonds, RBI)
• Geography (Peninsular Block, Climate, Strait of Hormuz)
• Environment & Ecology (Mangroves, REDD+, Madhav NP, Lake Turkana)
• Science & Technology (Quantum Mission, Green Hydrogen, GenomeIndia, Stealth, LLMs)
• Current Affairs (AI Impact Summit 2026, BAFTA, Nobel Prizes, BIMSTEC)
• International Relations (ASEAN, EU, UN Peacekeeping, INTERPOL Notices)

If this video helps your preparation, please LIKE, SHARE and SUBSCRIBE for more UPSC content.
Comments and discussion are welcome — share your attempt score and any questions where you think the answer should be different.

#UPSC #UPSC2026 #Prelims2026 #UPSCPrelims #GSPaper1 #AnswerKey #CivilServices #IAS #UPSCCSE #CurrentAffairs"""

TAGS = [
    "UPSC", "UPSC 2026", "UPSC Prelims 2026", "UPSC Prelims",
    "GS Paper 1", "UPSC Answer Key", "UPSC Prelims Answer Key 2026",
    "Civil Services", "IAS", "UPSC CSE", "UPSC CSE 2026",
    "Current Affairs", "UPSC Solutions", "Prelims 2026 Solutions",
    "24 May 2026", "UPSC GS-1",
]


def main() -> None:
    if not os.path.isfile(VIDEO_PATH):
        print(f"ERROR: Video not found at {VIDEO_PATH}")
        sys.exit(1)

    file_size_mb = os.path.getsize(VIDEO_PATH) / (1024 * 1024)
    print(f"Video: {VIDEO_PATH}")
    print(f"Size:  {file_size_mb:.1f} MB")
    print(f"Title: {TITLE}")
    print(f"Privacy: public  |  Comments: enabled  |  Embeddable: yes")
    print()

    service = get_youtube_service()
    info = get_channel_info(service)
    if info:
        print(f"Channel: {info.get('title')}  ({info.get('subscribers')} subs, "
              f"{info.get('videos')} videos)")
    print()

    result = upload_video(
        service,
        video_path=VIDEO_PATH,
        title=TITLE,
        description=DESCRIPTION,
        tags=TAGS,
        category_id="27",   # Education
        privacy_status="public",
    )

    print()
    if result.success:
        print("=== UPLOAD SUCCESS ===")
        print(f"Video ID:  {result.video_id}")
        print(f"Video URL: {result.video_url}")
        print()
        print("Defaults set by uploader.youtube.upload_video():")
        print("  - publicStatsViewable: True (like/view counts visible)")
        print("  - embeddable: True")
        print("  - selfDeclaredMadeForKids: False")
        print()
        print("Note: Comments are enabled by default for new YouTube uploads.")
        print("If your channel has comments disabled at the channel level, "
              "enable them in YouTube Studio > Settings > Community.")
    else:
        print("=== UPLOAD FAILED ===")
        print(f"Error: {result.error}")
        sys.exit(2)


if __name__ == "__main__":
    main()
