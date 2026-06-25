**When to Read This:** Touching client-side join/leave logic, understanding how the browser orchestrates config, start, and stop, or debugging RTC/RTM lifecycle issues in the web client.

# Session Lifecycle

> Browser-side orchestration of the Agora RTC/RTM session. Covers config fetch, agent start, RTC join, RTM transcript, and teardown. The backend owns token issuance and session tracking; the web client owns the RTC/RTM channel lifecycle.

## Phase 1: Config fetch

`LandingPage.tsx` calls `getConfig({ channel?, uid? })` which hits `GET /api/get_config`. The backend:

- Generates a concrete non-zero UID if the request omits one or passes ≤ 0.
- Mints a Token007 RTC+RTM token (3600s expiry) for the user UID.
- Returns `{ app_id, token, uid, channel_name, agent_uid }`.

The web client stores `app_id`, `token`, `uid`, and `channel_name` for the RTC join step.

## Phase 2: RTC join and agent start

`LandingPage.tsx` calls these in sequence:

1. Join the Agora RTC channel using the token and UID from `get_config`.
2. `POST /api/startAgent` with `{ channelName, rtcUid (agent_uid), userUid (uid) }`. The backend builds the `CustomLLM` vendor and starts the async agent session.
3. The backend returns `{ agent_id, channel_name, status: "started" }`.
4. The web client stores `agent_id` for later teardown.

## Phase 3: Conversation

`ConversationComponent.tsx` handles the live session:

- Publishes the local microphone track to the RTC channel.
- Listens for remote audio (agent) and plays it back.
- Subscribes to RTM for transcript events and metrics.

Transcript normalization (`normalizeTranscript` in `src/lib/conversation.ts`) maps `uid === '0'` to the local UID so speaker labels are correct.

`mapAgentVisualizerState` maps Agora `AgentState` values (`listening`, `thinking`, `speaking`, `idle`, `silent`) to `AgentVisualizerState` values used by the UI kit.

## Phase 4: Teardown

When the user ends the call:

1. `POST /api/stopAgent { agentId }` — backend stops the session.
2. Web client leaves the RTC channel and unpublishes the mic track.
3. RTM connection is closed.
4. UI returns to the landing page.

The backend's `Agent.stop()` first tries `session.stop()` from the in-memory `_sessions` map; if the session is not found, it falls back to `client.stop_agent(agent_id)` (stateless cloud path).

## Transcript speaker mapping

`normalizeTranscript(transcript, localUid)` in `src/lib/conversation.ts`:

- `uid === '0'` → replaced with `localUid` (the user's UID from `get_config`).
- Applies `normalizeTranscriptSpacing` to add spaces after punctuation and collapse multiple spaces.

`getMessageList` and `getCurrentInProgressMessage` filter and convert `TranscriptHelperItem` entries into `IMessageListItem` shapes for the UI kit.

## Token and UID constraints

- Token issuance (`generate_convo_ai_token`) requires a concrete non-zero UID. The backend rejects zero/negative UIDs and generates one.
- `agent_uid` is randomly generated (8-digit integer) on each `get_config` call.
- `channel_name` is generated as `rag-<timestamp>-<random>` if not specified.

## Related

- [02_architecture](../02_architecture.md) — full request flow including the Agora cloud side.
- [06_interfaces](../06_interfaces.md) — `get_config`, `startAgent`, `stopAgent` route contracts.
