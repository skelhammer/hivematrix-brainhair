# BrainHair TODO Items

This document tracks pending TODO items in the BrainHair codebase with their locations, priorities, and implementation notes.

## High Priority

### 1. Implement Datto RMM Integration
**Location:** `app/chat_routes.py:379, 451`

**Description:** The command approval system currently returns simulated output. Actual integration with Datto RMM API is needed for remote command execution on managed devices.

**Implementation Notes:**
- Requires Datto RMM API credentials
- Need to implement OAuth2 authentication flow
- Should handle device lookup by ID
- Must implement PowerShell command execution endpoint
- Add error handling for offline devices
- Consider rate limiting and timeout configurations

**Related Functions:**
- `execute_remote_command()` - Main integration point
- `approve_command()` - Calls execute function

---

## Medium Priority

### 2. Implement Session Idle Tracking and Cleanup
**Location:** `app/claude_session_manager.py:743`

**Description:** The `cleanup_idle_sessions()` method is a placeholder. Without this, Claude Code sessions accumulate in memory indefinitely.

**Implementation Notes:**
- Track last activity timestamp per session
- Implement background thread to periodically check session age
- Gracefully shutdown idle Claude processes
- Clean up database records for completed sessions
- Consider configurable idle timeout (default: 30 minutes)
- Log cleanup events to Helm

**Memory Impact:** Each session keeps a subprocess running. Over time this could cause memory pressure.

---

### 3. Enhance Context with Codex Service Integration
**Location:** `app/chat_routes.py:295, 305`

**Description:** When users provide ticket or client context, the system should call Codex to get detailed information to improve AI responses.

**Implementation Notes:**

#### Ticket Details (line 295):
- Call `GET /api/tickets/{ticket_number}` on Codex service
- Include: status, priority, assigned technician, description, recent updates
- Add error handling for non-existent tickets
- Cache results per session to reduce API calls

#### Client Details (line 305):
- Call `GET /api/clients/{client_name}` on Codex service
- Include: full company name, plan type, contact info, active tickets
- Handle ambiguous client names (multiple matches)
- Cache results per session

**Context Benefits:** Richer context enables AI to provide more relevant responses and suggest appropriate actions.

---

## Low Priority

### 4. Get Actual User Display Name
**Location:** `app/claude_session_manager.py:74`

**Description:** Currently uses username (from JWT sub claim) as display name. Should call Core or user service to get actual full name.

**Implementation Notes:**
- Call Core service to get user profile: `GET /api/users/{user_id}`
- Extract display_name or full_name field
- Fallback to username if service unavailable
- Consider caching user names to reduce API calls
- Update ChatSessionModel.user_name field

**Impact:** Cosmetic improvement for session history and logs.

---

## Implementation Guidelines

When implementing these TODOs:

1. **Add appropriate logging** - Use HelmLogger to log all integration attempts, successes, and failures
2. **Handle errors gracefully** - External service failures should not crash BrainHair
3. **Add configuration** - Use environment variables for API URLs, timeouts, credentials
4. **Write tests** - Add unit tests for new integration code
5. **Update documentation** - Update README.md with new features and configuration options
6. **Consider rate limits** - All external API calls should respect rate limiting
7. **Add metrics** - Consider logging integration success rates to Helm for monitoring

---

## Completed TODOs

- ✅ Add timestamp to command creation (chat_routes.py:335) - Fixed 2025-11-20
