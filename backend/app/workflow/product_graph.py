from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.context_loader import load_context_pack
from app.services.llm import ModelClient


class ProductState(TypedDict, total=False):
    project_id: str
    user_input: str
    product_idea: str
    clarification_questions: list[str]
    assumptions: list[str]
    prd_markdown: str
    ux_flow_markdown: str
    mermaid_flowchart: str
    prototype_html: str
    feature_map: dict[str, str]
    consistency_report: str
    qa_criteria: str
    jira_stories: list[dict[str, Any]]
    jira_stories_markdown: str
    open_questions: list[str]
    version: str
    status: str
    errors: list[str]
    context_pack: str


DEMO_IDEA = (
    "Smart Notification Summary: a phone system feature that groups low-priority "
    "notifications into a summary card in Notification shade, with Settings controls, "
    "privacy safeguards, empty/error states, and QA-ready acceptance criteria."
)


FEATURE_MAP = {
    "FR-01": "notification_summary_card",
    "FR-02": "settings_toggle",
    "FR-03": "empty_state",
    "FR-04": "error_state",
    "FR-05": "success_feedback",
}


AGENT_INSTRUCTION_MARKERS = (
    "agent",
    "generate",
    "create",
    "build",
    "workflow",
    "prd",
    "prototype",
    "jira",
    "story",
    "stories",
    "生成",
    "原型",
    "运行",
)


def product_summary_from_input(user_input: str) -> str:
    candidate = user_input.strip()
    if not candidate:
        return DEMO_IDEA

    lower_candidate = candidate.lower()
    if any(marker in lower_candidate for marker in AGENT_INSTRUCTION_MARKERS):
        return DEMO_IDEA

    return candidate


def clarify_requirements(state: ProductState) -> ProductState:
    user_input = state.get("user_input") or DEMO_IDEA
    return {
        "product_idea": product_summary_from_input(user_input),
        "context_pack": load_context_pack(),
        "assumptions": [
            "Feature ships as an opt-in system experience for Android 15+ devices.",
            "Notification ranking runs on-device where possible; cloud calls are out of scope for the PoC.",
            "System UI owns Notification shade surfaces; Settings owns persistent controls.",
            "Low-priority categorization uses existing notification channels and user behavior signals.",
        ],
        "clarification_questions": [
            "Which regions, device tiers, and Android/OTA versions are in launch scope?",
            "Should summary ranking be fully on-device or can it call a server model?",
            "What notification categories must never be summarized?",
            "Which telemetry events are acceptable under privacy policy?",
            "What is the fallback if ranking data is unavailable?",
        ],
        "open_questions": [
            "Legal/privacy review is needed for notification content processing.",
            "Performance budget needs confirmation from System UI and platform teams.",
        ],
        "status": "clarified",
        "errors": [],
    }


def generate_prd(state: ProductState) -> ProductState:
    idea = state["product_idea"]
    assumptions = "\n".join(f"- {item}" for item in state["assumptions"])
    questions = "\n".join(f"- {item}" for item in state["clarification_questions"])
    prd = f"""# PRD vDraft: Smart Notification Summary

## Product Overview
{idea}

Smart Notification Summary reduces notification overload by grouping low-priority notifications into a compact card while keeping urgent notifications immediately visible.

## Background and Problem Definition
Phone users receive high notification volume from commerce, social, content, and utility apps. Current Notification shade experiences force users to scan individual low-priority cards, increasing cognitive load and making urgent alerts harder to notice.

## Goals
- Reduce Notification shade clutter without hiding critical notifications.
- Give users explicit opt-in control from Settings and an inline summary card action.
- Provide clear empty, loading, error, and success states.
- Generate reviewable outputs for PM, UX, engineering, and QA.

## Non-goals
- Rewriting Android notification ranking infrastructure.
- Sending notification content to third-party services.
- Building a real Figma or Jira integration in this PoC.

## Target Users and Scenarios
- Power users with high daily notification volume.
- Users who want promotional and low-priority updates batched.
- QA and support teams validating notification behavior across device states.

## System Entry Points
- **Notification shade:** Summary card appears above low-priority notification groups.
- **Settings:** `Settings > Notifications > Smart Notification Summary` contains opt-in toggle and category controls.
- **Lock screen:** Out of scope for v1.0 unless privacy review approves redacted summary text.

## User Journey
1. User enables Smart Notification Summary in Settings.
2. System shows a loading state while recent notifications are categorized.
3. Notification shade displays a summary card with grouped low-priority notifications.
4. User expands the card, opens source notifications, or marks the summary as useful.
5. User can disable the feature or exclude app categories in Settings.

## Functional Requirements
| ID | Requirement | Prototype focus |
| --- | --- | --- |
| FR-01 | Show a summary card in Notification shade when low-priority notifications exist. | `{FEATURE_MAP["FR-01"]}` |
| FR-02 | Provide Settings opt-in toggle and category controls. | `{FEATURE_MAP["FR-02"]}` |
| FR-03 | Show empty state when no summarizable notifications exist. | `{FEATURE_MAP["FR-03"]}` |
| FR-04 | Show error/offline state when ranking data cannot be prepared. | `{FEATURE_MAP["FR-04"]}` |
| FR-05 | Show success feedback after user confirms or tunes the summary. | `{FEATURE_MAP["FR-05"]}` |

## Privacy and Permission Handling
- Use notification listener/system privileges already available to System UI.
- Do not expose notification content outside system-owned components in v1.0.
- Redact sensitive app categories and private lock-screen content.
- Provide an explicit opt-in toggle with a plain-language explanation.

## Key States and Edge Cases
- Loading: ranking pipeline is preparing summary content.
- Empty: no low-priority notifications or all apps excluded.
- Error/offline: classifier unavailable, stale data, or storage read failure.
- No permission/disabled: user has not opted in or disabled notification access.
- Success: summary action saved, app exclusion changed, or card dismissed.

## Performance, Power, and Memory
- Summary generation should complete within 500 ms for cached notification data.
- Avoid wakeups when Notification shade is closed.
- Keep memory bounded by summarizing metadata and short redacted snippets only.
- Degrade gracefully on low-memory devices.

## Region, Device, Android, and OTA Constraints
- Initial scope: Android 15+ OTA, mid/high-tier devices with System UI summary surface enabled.
- Region policy may disable summary text for markets with stricter notification privacy requirements.
- OEM skin variants must validate Notification shade layout compatibility.

## Owner Boundaries
- System UI: Notification shade card, state rendering, inline actions.
- Settings: opt-in toggle and category controls.
- Platform notification team: ranking and notification metadata contract.
- Data/logging: privacy-safe telemetry events.
- QA: regression matrix across device states, app categories, and OTA paths.

## Acceptance Criteria
- Users can enable or disable the feature from Settings.
- Summary card appears only when eligible low-priority notifications exist.
- Empty, loading, error, disabled, and success states render with stable copy.
- Critical notifications remain outside the summary.
- QA can trace each Jira story to PRD requirement IDs and prototype feature IDs.

## Assumptions
{assumptions}

## Questions to Confirm
{questions}
"""
    return {"prd_markdown": prd, "status": "prd_generated"}


def generate_ux_flow(state: ProductState) -> ProductState:
    flow = """# UX Flow: Smart Notification Summary

## Main Flow
1. User opens Settings and enables Smart Notification Summary.
2. User pulls down Notification shade.
3. System shows a short loading state while summary data is prepared.
4. Summary card appears with grouped low-priority updates.
5. User expands the card, opens an item, marks it useful, or jumps to Settings.

## Alternate Flows
- Empty: no eligible notifications, so the card explains that the summary will appear later.
- Error: ranking is unavailable, so System UI preserves the normal notification list.
- Disabled: Settings toggle is off, so no summary card is shown.

## Focus IDs
- `notification_summary_card`
- `settings_toggle`
- `empty_state`
- `error_state`
- `success_feedback`
"""
    mermaid = """```mermaid
flowchart TD
    A[Settings entry] --> B{Smart Summary enabled?}
    B -- No --> C[Show disabled state]
    B -- Yes --> D[Open Notification shade]
    D --> E[Loading summary]
    E --> F{Eligible notifications?}
    F -- Yes --> G[Summary card]
    F -- No --> H[Empty state]
    G --> I[Expand or open item]
    G --> J[Mark useful]
    G --> K[Manage in Settings]
    E --> L[Error state]
    J --> M[Success feedback]
```"""
    return {"ux_flow_markdown": flow, "mermaid_flowchart": mermaid, "feature_map": FEATURE_MAP, "status": "ux_generated"}


def generate_prototype(state: ProductState) -> ProductState:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Smart Notification Summary Prototype</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background: #f4f6f8; color: #17202a; }
    .phone { width: min(390px, 96vw); min-height: 720px; border: 10px solid #111827; border-radius: 34px; background: #eef2f7; overflow: hidden; box-shadow: 0 18px 55px rgba(17,24,39,.22); }
    .focus-ring { outline: 3px solid #0f766e; outline-offset: 4px; }
    button { transition: transform .12s ease, background .12s ease; }
    button:active { transform: scale(.98); }
  </style>
</head>
<body>
  <main class="min-h-screen flex items-center justify-center p-4">
    <section class="phone">
      <div class="bg-slate-950 text-white px-5 pt-4 pb-3">
        <div class="flex justify-between text-xs opacity-80"><span>9:41</span><span>5G 82%</span></div>
        <div class="mt-5 flex gap-2">
          <button onclick="showView('shade')" class="px-3 py-2 rounded bg-white/15 text-sm">Shade</button>
          <button onclick="showView('settings')" class="px-3 py-2 rounded bg-white/15 text-sm">Settings</button>
          <button onclick="cycleState()" class="ml-auto px-3 py-2 rounded bg-teal-500 text-sm">Cycle state</button>
        </div>
      </div>

      <div id="shade" class="p-4 space-y-3">
        <div class="text-sm font-semibold text-slate-600">Notification shade</div>
        <div id="loading" data-feature="loading_state" class="rounded-md bg-white p-4 shadow-sm">
          <div class="h-3 w-32 bg-slate-200 rounded animate-pulse"></div>
          <div class="mt-3 h-3 w-56 bg-slate-200 rounded animate-pulse"></div>
        </div>
        <div id="summary" data-feature="notification_summary_card" class="hidden rounded-md bg-white p-4 shadow-sm">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-base font-semibold">Smart summary</div>
              <p class="text-sm text-slate-600 mt-1">7 low-priority updates grouped from Shopping, News, and Social.</p>
            </div>
            <span class="text-xs bg-teal-100 text-teal-800 px-2 py-1 rounded">Opt-in</span>
          </div>
          <div id="expanded" class="hidden mt-3 text-sm text-slate-700 space-y-2">
            <p>Shopping: 3 delivery and promo updates</p>
            <p>News: 2 digest items</p>
            <p>Social: 2 non-urgent reactions</p>
          </div>
          <div class="mt-4 flex gap-2">
            <button onclick="toggleExpanded()" class="px-3 py-2 rounded bg-slate-900 text-white text-sm">Expand</button>
            <button onclick="showSuccess()" class="px-3 py-2 rounded bg-teal-600 text-white text-sm">Useful</button>
            <button onclick="showView('settings')" class="px-3 py-2 rounded bg-slate-100 text-sm">Manage</button>
          </div>
        </div>
        <div id="empty" data-feature="empty_state" class="hidden rounded-md bg-white p-4 shadow-sm">
          <div class="font-semibold">No summary right now</div>
          <p class="text-sm text-slate-600 mt-1">Critical notifications stay visible. Low-priority updates will appear here when available.</p>
        </div>
        <div id="error" data-feature="error_state" class="hidden rounded-md bg-red-50 p-4 border border-red-200">
          <div class="font-semibold text-red-900">Summary unavailable</div>
          <p class="text-sm text-red-700 mt-1">Your regular notifications are still shown. Try again later or review Settings.</p>
        </div>
        <div id="success" data-feature="success_feedback" class="hidden rounded-md bg-emerald-50 p-4 border border-emerald-200">
          <div class="font-semibold text-emerald-900">Preference saved</div>
          <p class="text-sm text-emerald-700 mt-1">The system will tune future summaries from this feedback.</p>
        </div>
        <div class="rounded-md bg-white p-4 shadow-sm">
          <div class="font-medium">Calendar</div>
          <p class="text-sm text-slate-600">Design review starts in 15 minutes.</p>
        </div>
      </div>

      <div id="settings" class="hidden p-4 space-y-3">
        <div class="text-sm font-semibold text-slate-600">Settings > Notifications</div>
        <div data-feature="settings_toggle" class="rounded-md bg-white p-4 shadow-sm">
          <div class="flex items-center justify-between">
            <div>
              <div class="font-semibold">Smart Notification Summary</div>
              <p class="text-sm text-slate-600 mt-1">Group low-priority notifications into one summary card.</p>
            </div>
            <label class="inline-flex items-center cursor-pointer">
              <input id="toggle" type="checkbox" checked class="sr-only peer" onchange="syncToggle()" />
              <span class="w-11 h-6 bg-slate-300 rounded-full peer-checked:bg-teal-600 relative after:content-[''] after:absolute after:h-5 after:w-5 after:bg-white after:rounded-full after:left-0.5 after:top-0.5 peer-checked:after:translate-x-5 after:transition"></span>
            </label>
          </div>
        </div>
        <div class="rounded-md bg-white p-4 shadow-sm space-y-2">
          <div class="font-medium">Included categories</div>
          <label class="flex justify-between text-sm"><span>Shopping updates</span><input type="checkbox" checked></label>
          <label class="flex justify-between text-sm"><span>News digests</span><input type="checkbox" checked></label>
          <label class="flex justify-between text-sm"><span>Social reactions</span><input type="checkbox" checked></label>
        </div>
      </div>
    </section>
  </main>
  <script>
    const states = ['loading', 'summary', 'empty', 'error'];
    let stateIndex = 1;
    function hideStates(){ states.concat(['success']).forEach(id => document.getElementById(id).classList.add('hidden')); }
    function renderState(id){ hideStates(); document.getElementById(id).classList.remove('hidden'); location.hash = id; }
    function cycleState(){ stateIndex = (stateIndex + 1) % states.length; renderState(states[stateIndex]); }
    function showSuccess(){ hideStates(); document.getElementById('success').classList.remove('hidden'); location.hash = 'success_feedback'; }
    function toggleExpanded(){ document.getElementById('expanded').classList.toggle('hidden'); }
    function showView(id){ document.getElementById('shade').classList.toggle('hidden', id !== 'shade'); document.getElementById('settings').classList.toggle('hidden', id !== 'settings'); }
    function syncToggle(){ renderState(document.getElementById('toggle').checked ? 'summary' : 'empty'); }
    function applyFocus(){
      const focus = new URLSearchParams(location.search).get('focus') || location.hash.replace('#','');
      if (!focus) { renderState('summary'); return; }
      const target = document.querySelector(`[data-feature="${focus}"]`) || document.getElementById(focus);
      if (focus === 'settings_toggle') showView('settings'); else showView('shade');
      if (focus === 'empty_state') renderState('empty');
      else if (focus === 'error_state') renderState('error');
      else if (focus === 'success_feedback') showSuccess();
      else if (focus !== 'settings_toggle') renderState('summary');
      if (target) target.classList.add('focus-ring');
    }
    applyFocus();
  </script>
</body>
</html>"""
    return {"prototype_html": html, "status": "prototype_generated"}


def check_consistency(state: ProductState) -> ProductState:
    report = """# Consistency Review

## Summary
PRD, UX flow, and prototype are aligned for the main Smart Notification Summary scenario. Each PRD requirement FR-01 through FR-05 has a matching prototype focus ID and UX flow state.

## PRD Requirements Missing in Prototype
- Lock screen privacy behavior is intentionally out of prototype scope and should remain a v1.1 discussion item.
- Region/device/OTA constraints are documented in PRD but not visually represented in the prototype.

## Prototype Elements Missing in PRD
- The prototype includes a `Useful` feedback action. PRD covers success feedback but should add analytics and tuning behavior details.

## Missing Boundary Scenarios
- No permission state needs a dedicated visual if notification access can be revoked independently.
- Low-memory degradation needs QA coverage beyond this visual prototype.

## Acceptance Criteria Gaps
- Add a measurable latency budget test for summary generation.
- Add regression checks for critical notifications remaining outside the summary.

## Recommended Fixes
1. Add no-permission state in the next prototype iteration.
2. Confirm telemetry events with privacy review.
3. Validate Settings owner boundary for category-level exclusions.
"""
    return {"consistency_report": report, "status": "reviewed"}


def generate_qa(state: ProductState) -> ProductState:
    qa = """# QA Acceptance Criteria

## Normal Path
- Enable Smart Notification Summary in Settings and verify the Notification shade summary card appears when eligible low-priority notifications exist.
- Expand the summary card and confirm grouped categories remain traceable to source notifications.
- Tap `Useful` and verify success feedback appears without removing critical notifications.

## Boundary Scenarios
- No eligible notifications: empty state appears and normal notifications are unaffected.
- All categories excluded: summary card does not appear.
- Device upgraded by OTA: previous opt-in state and category selections are preserved.

## Failure States
- Ranking unavailable: error state appears and standard notification list remains visible.
- Storage read failure: feature fails closed and logs a privacy-safe diagnostic event.
- Offline: on-device cached behavior continues; no network dependency blocks Notification shade.

## Permission and Privacy
- Disabled toggle prevents summary generation.
- Sensitive notification categories are redacted or excluded.
- Lock screen does not show summary text unless privacy setting allows it.

## Regression Risks
- Notification shade jank or delayed expansion.
- Critical notifications incorrectly grouped into summary.
- Excess battery usage from background ranking.
- Settings toggle desynchronized from System UI state.
"""
    return {"qa_criteria": qa, "status": "qa_generated"}


def generate_jira(state: ProductState) -> ProductState:
    stories = [
        {
            "type": "Epic",
            "title": "Deliver Smart Notification Summary v1.0",
            "user_story": "As a phone user, I want low-priority notifications summarized so I can focus on important alerts.",
            "description": "Build the opt-in system experience across Notification shade and Settings.",
            "acceptance_criteria": ["PRD FR-01 through FR-05 are implemented", "QA normal, empty, error, and privacy scenarios pass"],
            "dependencies": ["System UI surface", "Settings toggle", "Notification ranking contract"],
            "prd_sections": ["Functional Requirements", "Privacy and Permission Handling"],
            "prototype_feature_id": "notification_summary_card",
        },
        {
            "type": "Story",
            "title": "Render summary card in Notification shade",
            "user_story": "As a user, I can see grouped low-priority notifications in one card.",
            "description": "Create default, loading, empty, error, and success rendering states.",
            "acceptance_criteria": ["Card appears only with eligible notifications", "Critical notifications remain separate"],
            "dependencies": ["Notification metadata", "System UI layout"],
            "prd_sections": ["FR-01", "Key States and Edge Cases"],
            "prototype_feature_id": "notification_summary_card",
        },
        {
            "type": "Story",
            "title": "Add Settings opt-in and category controls",
            "user_story": "As a user, I can control whether summaries are enabled and which categories are included.",
            "description": "Expose toggle and category controls under Settings > Notifications.",
            "acceptance_criteria": ["Toggle persists across restart", "Disabled state prevents summary display"],
            "dependencies": ["Settings storage", "System UI state sync"],
            "prd_sections": ["FR-02", "Owner Boundaries"],
            "prototype_feature_id": "settings_toggle",
        },
    ]
    md = "\n\n".join(
        f"## {item['type']}: {item['title']}\n"
        f"**User story:** {item['user_story']}\n\n"
        f"**Description:** {item['description']}\n\n"
        f"**Acceptance criteria:**\n" + "\n".join(f"- {criterion}" for criterion in item["acceptance_criteria"]) + "\n\n"
        f"**Dependencies:** {', '.join(item['dependencies'])}\n\n"
        f"**PRD trace:** {', '.join(item['prd_sections'])}\n\n"
        f"**Prototype feature ID:** `{item['prototype_feature_id']}`"
        for item in stories
    )
    return {"jira_stories": stories, "jira_stories_markdown": md, "status": "completed"}


def build_graph():
    graph = StateGraph(ProductState)
    graph.add_node("clarify", clarify_requirements)
    graph.add_node("prd", generate_prd)
    graph.add_node("ux", generate_ux_flow)
    graph.add_node("prototype", generate_prototype)
    graph.add_node("review", check_consistency)
    graph.add_node("qa", generate_qa)
    graph.add_node("jira", generate_jira)
    graph.add_edge(START, "clarify")
    graph.add_edge("clarify", "prd")
    graph.add_edge("prd", "ux")
    graph.add_edge("ux", "prototype")
    graph.add_edge("prototype", "review")
    graph.add_edge("review", "qa")
    graph.add_edge("qa", "jira")
    graph.add_edge("jira", END)
    return graph.compile()


def run_product_workflow(project_id: str, user_input: str) -> ProductState:
    _ = ModelClient()
    graph = build_graph()
    initial: ProductState = {"project_id": project_id, "user_input": user_input, "status": "started", "errors": []}
    return graph.invoke(initial)
